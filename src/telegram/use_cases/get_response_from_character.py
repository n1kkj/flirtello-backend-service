from __future__ import annotations

import hashlib
import logging
from typing import Optional
from uuid import UUID

import sentry_sdk
from fastapi import HTTPException
from sqlmodel import Session, select

from src.db.lib.billing.common.enums import CurrenciesTypes, PaidActions, SourceNames
from src.db.lib.billing.common.exceptions import (
    NotEnoughCurrencyError,
    TariffPlanExpired,
)
from src.db.lib.chat_models import Channel, MessageType
from src.db.lib.chat_types import MessageType as ChatTypesMessageType
from src.db.lib.content_models import ImageInfo, LLMStats, UserImageView
from src.db.lib.llm_services.api import LLMServiceAPI
from src.lib.billing import map_bff_image_type_to_paid_action_name
from src.lib.config import config
from src.routers.chat import MessageResponse
from src.telegram.api import delete_message, send_tg_message
from src.telegram.async_adapters import (
    async_check_user_have_enough_currency,
    async_get_paid_action_dataset,
    async_get_user_current_tariff_plan,
    async_process_paid_action,
    async_send_message,
    async_send_message_and_get_response,
)
from src.telegram.context import RequestContext
from src.telegram.DTO.chat import (
    SendChatMessageInputDTO,
    SendChatMessageOutputDTO,
    SendChatMessageOutputSubDTO,
)
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.template_messages import TemplateMessages
from src.translator import TranslationRequest

logger = logging.getLogger(__name__)


async def _send_preloader(
    chat_id: str, token: str, context: RequestContext
) -> Optional[dict]:
    """Sends a preloader message without delay and without notification sound."""
    try:
        lang_code = context.user_language or "en"
        _ = get_gettext_for_language(lang_code)
        preloader_text = _("Typing...")
        response = await send_tg_message(
            chat_id, preloader_text, token, disable_notification=True
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Failed to send preloader: {e}")
        return None


async def get_response_from_character(
    char_id: int,
    user_id: UUID,
    data: SendChatMessageInputDTO,
    session: Session,
    context: RequestContext | None = None,
) -> SendChatMessageOutputDTO:
    original_user_message = data.message
    translated_user_message = original_user_message

    # Send "Typing..." preloader immediately at the start
    typing_message_data = None
    typing_message_id = None
    if context and context.telegram_chat_id and context.bot_token:
        typing_message_data = await _send_preloader(
            context.telegram_chat_id, context.bot_token, context
        )
        if typing_message_data:
            typing_message_id = typing_message_data.get("result", {}).get("message_id")

    # --- 1. Translate incoming message (if needed) ---
    if (
        context
        and context.translator
        and context.user_language
        and context.user_language != "en"
        and original_user_message
    ):
        try:
            with context.record_timing("translate_user_message"):
                key = hashlib.sha256(original_user_message.encode()).hexdigest()
                req = TranslationRequest(
                    source_text=original_user_message,
                    source_lang=context.user_language,
                    target_lang="en",  # Target is character's language
                    context="A male user's chat message to a female character.",
                    context_key=f"user_message:{key}",
                )
                res = await context.translator.translate(req)
                translated_user_message = res.translated_text
            logger.info(
                f"[{context.request_id}] Translated user message from {context.user_language} to en"
            )
        except Exception as e:
            logger.error(
                f"[{context.request_id}] Failed to translate user message for user {user_id}: {e}"
            )
            sentry_sdk.capture_exception(e)
            # Proceed with original message if translation fails

    # Using centralized async adapters from telegram.async_adapters module

    try:
        # Billing
        paid_action_dataset = await async_get_paid_action_dataset(
            PaidActions.MESSAGE.value
        )
        await async_check_user_have_enough_currency(
            user_id, paid_action_dataset.price, CurrenciesTypes.TOKEN.value
        )
        tariff_plan = await async_get_user_current_tariff_plan(user_id)
        tariff_plan_id = str(tariff_plan.id)
        if data.config_id and data.config_id != "null":
            channel = await session.execute(
                select(Channel).where(
                    Channel.char_id == char_id,
                    Channel.user_id == user_id,
                    Channel.config_id == data.config_id,
                )
            )
            channel = channel.scalars().first()
            if not channel:
                raise HTTPException(status_code=404, detail="Channel not found")

            # --- Save TRANSLATED user message (English only in DB) ---
            await async_send_message(
                char_id=char_id,
                user_id=user_id,
                sender="user",
                text=translated_user_message,  # ✅ Save English version in DB
                llm_stats=LLMStats.dummy(),
                config_id=data.config_id,
            )

            roleplay_api_response: Optional[MessageResponse]
            with context.record_timing("llm_api_get_response"):
                # EXTERNAL IMAGE CALL: Roleplay Service (can return image)
                roleplay_api_response = await LLMServiceAPI(
                    api_url=config.roleplay_api_url,
                    api_key=config.api_key,
                ).post(
                    params={
                        "user_id": str(user_id),
                        "text": translated_user_message,  # Use translated message
                        "character_id": char_id,
                        "config_id": str(data.config_id),
                    },
                    validation_schema=MessageResponse,
                    endpoint_url="/chat/messages",
                )
            messages = []
            if not roleplay_api_response:
                logger.info(
                    "No response from roleplay API in get_response_from_character"
                )
                sentry_sdk.capture_message(
                    "No response from roleplay API in get_response_from_character",
                    level="error",
                )
                # Delete "Typing..." message if it was sent
                if (
                    typing_message_id
                    and context
                    and context.telegram_chat_id
                    and context.bot_token
                ):
                    try:
                        await delete_message(
                            context.telegram_chat_id,
                            typing_message_id,
                            context.bot_token,
                        )
                    except Exception as e:
                        logger.error(f"Failed to delete typing message: {e}")
                return SendChatMessageOutputDTO.from_single_text_message(
                    message="I can't talk right now darling"
                )
            logger.info(f"Roleplay api response: {roleplay_api_response.messages}")
            messages = []
            with context.record_timing("translate_character_turn_with_config"):
                for message in roleplay_api_response.messages:
                    # Access attachments while object is still attached to session
                    attachments = message.attachments
                    original_char_response = message.text or ""

                    # Save character response (already in English from LLM)
                    current_message = await async_send_message(
                        char_id=char_id,
                        user_id=user_id,
                        sender="character",
                        text=original_char_response,  # ✅ English response from LLM
                        llm_stats=LLMStats.dummy(),
                        attachments=attachments,
                        message_type=message.message_type,
                        stage_name=message.stage_name,
                        config_id=data.config_id,
                    )

                    translated_char_response = original_char_response
                    # --- 2. Translate outgoing message (if needed) ---
                    logger.info(
                        f"[{context.request_id}] Translation check: context={context is not None}, "
                        f"translator={context.translator is not None if context else 'N/A'}, "
                        f"user_language={context.user_language if context else 'N/A'}, "
                        f"is_voice={context.is_voice_message if context else 'N/A'}"
                    )
                    if (
                        context
                        and context.translator
                        and context.user_language
                        and context.user_language != "en"
                        and original_char_response
                    ):
                        try:
                            logger.info(
                                f"[{context.request_id}] Starting translation en → {context.user_language}"
                            )
                            message_hash = hashlib.sha256(
                                original_char_response.encode()
                            ).hexdigest()
                            req = TranslationRequest(
                                source_text=original_char_response,
                                source_lang="en",
                                target_lang=context.user_language,
                                context="A female character's chat message to a male user.",
                                context_key=f"char_response:{message_hash}",
                            )
                            res = await context.translator.translate(req)
                            translated_char_response = res.translated_text
                            logger.info(
                                f"[{context.request_id}] ✅ Translated: '{original_char_response[:50]}...' → '{translated_char_response[:50]}...'"
                            )
                        except Exception as e:
                            logger.error(
                                f"[{context.request_id}] ❌ Failed to translate char response for user {user_id}: {e}"
                            )
                            sentry_sdk.capture_exception(e)
                    else:
                        logger.info(
                            f"[{context.request_id}] Skipping translation (will send in English)"
                        )

                    if (
                        message.message_type == MessageType.DEFAULT_TEXT.value
                        or message.message_type == MessageType.SCENARIO_TEXT.value
                    ):
                        paid_action_dataset = await async_get_paid_action_dataset(
                            PaidActions.MESSAGE.value
                        )
                        additional_data = {
                            "char_id": char_id,
                            "message_id": current_message.id,
                            "tariff_plan_id": tariff_plan_id,
                            "config_id": str(data.config_id),
                        }
                        logger.info(
                            f"🔵 [BILLING DEBUG] CALLING MESSAGE BILLING: user_id={user_id}, char_id={char_id}, message_id={current_message.id}, price={paid_action_dataset.price}"
                        )
                        await async_process_paid_action(
                            user_id,
                            paid_action_dataset,
                            SourceNames.TELEGRAM,
                            additional_data,
                        )
                        logger.info(
                            f"✅ [BILLING DEBUG] MESSAGE BILLING CALL COMPLETED: user_id={user_id}, char_id={char_id}"
                        )
                        if message.char_id:
                            messages.append(
                                SendChatMessageOutputSubDTO(
                                    message=translated_char_response,  # Use translated response
                                    message_type=message.message_type,
                                )
                            )
                    elif message.message_type == MessageType.DEFAULT_IMAGE.value:
                        # Проверка баланса перед добавлением изображения
                        # Получаем image_id из attachments
                        image_id = None
                        if message.attachments and len(message.attachments) > 0:
                            attachment_id = message.attachments[0].get("id")
                            # Конвертируем в UUID, если это строка
                            if attachment_id:
                                image_id = (
                                    UUID(attachment_id)
                                    if isinstance(attachment_id, str)
                                    else attachment_id
                                )

                        if image_id:
                            # Получаем ImageInfo для определения rating
                            image_info = await session.get(ImageInfo, image_id)
                            if image_info and image_info.rating:
                                # Определяем paid_action на основе rating
                                paid_action_name = (
                                    map_bff_image_type_to_paid_action_name(
                                        image_info.rating
                                    )
                                )
                                paid_action_dataset = (
                                    await async_get_paid_action_dataset(
                                        paid_action_name
                                    )
                                )

                                # Проверяем баланс перед добавлением изображения
                                try:
                                    await async_check_user_have_enough_currency(
                                        user_id,
                                        paid_action_dataset.price,
                                        CurrenciesTypes.TOKEN.value,
                                    )
                                    # Баланс достаточен - добавляем изображение
                                    messages.append(
                                        SendChatMessageOutputSubDTO.from_attachment(
                                            message
                                        )
                                    )

                                    # Списываем токены за изображение
                                    additional_data = {
                                        "char_id": char_id,
                                        "image_id": str(image_id),
                                        "tariff_plan_id": tariff_plan_id,
                                        "config_id": str(data.config_id),
                                    }
                                    logger.info(
                                        f"🔵 [BILLING DEBUG] CALLING IMAGE BILLING (from text): user_id={user_id}, char_id={char_id}, image_id={image_id}, rating={image_info.rating}, price={paid_action_dataset.price}"
                                    )
                                    await async_process_paid_action(
                                        user_id,
                                        paid_action_dataset,
                                        SourceNames.TELEGRAM,
                                        additional_data,
                                    )
                                    logger.info(
                                        f"✅ [BILLING DEBUG] IMAGE BILLING CALL COMPLETED (from text): user_id={user_id}, char_id={char_id}"
                                    )

                                    # Помечаем изображение как просмотренное ТОЛЬКО после успешной отправки
                                    user_view = UserImageView(
                                        user_id=user_id, image_id=image_id
                                    )
                                    session.add(user_view)
                                    logger.info(
                                        f"✅ [IMAGE VIEW] Marked image {image_id} as viewed for user {user_id}"
                                    )
                                except NotEnoughCurrencyError:
                                    # Недостаточно токенов - всегда добавляем NO_TOKENS сообщение с клавиатурой
                                    logger.info(
                                        f"❌ [BILLING DEBUG] Insufficient balance for image (from text): user_id={user_id}, char_id={char_id}, image_id={image_id}, rating={image_info.rating}"
                                    )
                                    messages.append(
                                        SendChatMessageOutputSubDTO(
                                            message=TemplateMessages.NO_TOKENS.value,
                                            insufficient_balance=True,
                                        )
                                    )
                                    # Изображение НЕ помечается как просмотренное, так как оно не было отправлено пользователю
                            else:
                                # Не удалось получить rating - добавляем изображение без проверки (fallback)
                                logger.warning(
                                    f"⚠️ [BILLING DEBUG] Could not get rating for image_id={image_id}, adding without balance check"
                                )
                                messages.append(
                                    SendChatMessageOutputSubDTO.from_attachment(message)
                                )
                        else:
                            # Нет image_id в attachments - добавляем как есть (fallback)
                            logger.warning(
                                "⚠️ [BILLING DEBUG] No image_id in attachments for DEFAULT_IMAGE message, adding without balance check"
                            )
                            messages.append(
                                SendChatMessageOutputSubDTO.from_attachment(message)
                            )

            await session.commit()
            logger.info(f"Messages: {messages}")

            # Delete "Typing..." message if it was sent
            if (
                typing_message_id
                and context
                and context.telegram_chat_id
                and context.bot_token
            ):
                try:
                    await delete_message(
                        context.telegram_chat_id, typing_message_id, context.bot_token
                    )
                except Exception as e:
                    logger.error(f"Failed to delete typing message: {e}")

            return SendChatMessageOutputDTO(messages=messages)

        # This is the non-config_id flow.
        # Here, `send_message_and_get_response` handles both saving user message and getting char response.
        # We need to adapt it. A better way would be to refactor it to accept a pre-translated message.
        # For now, let's assume `send_message_and_get_response` will be refactored or we'll replace its logic.
        # Let's replicate the logic from above for consistency.

        # ✅ ENGLISH-ONLY DB POLICY: Save only English text in database
        # POLICY: All messages in DB must be in English for consistency and analytics
        # SOLUTION: Save translated_user_message in DB, send same to LLM:
        #   1. Saves TRANSLATED user message in database (English only)
        #   2. Sends TRANSLATED message to LLM (consistent English context)
        #   3. User sees translated responses in their language via UI layer

        with context.record_timing("llm_send_and_get_response"):
            # EXTERNAL IMAGE CALL: Roleplay Service (can return image, legacy flow without config_id)
            message_dtos = await async_send_message_and_get_response(
                user_id, char_id, translated_user_message
            )  # ✅ Save English in DB, send English to LLM!

        # The response from this function would now need translation.

        logger.info(f"Message dtos: {message_dtos}")

        # --- Translate character's response from `message_dtos` ---
        final_messages_to_send = []
        with context.record_timing("translate_character_turn_no_config"):
            for message_dto in message_dtos:
                if message_dto.message_type == ChatTypesMessageType.TEXT.value:
                    original_char_text = message_dto.message.text or ""
                    translated_char_text = original_char_text
                    message_hash = hashlib.sha256(
                        original_char_text.encode()
                    ).hexdigest()
                    logger.info(
                        f"[{context.request_id}] [NO-CONFIG] Translation check: context={context is not None}, "
                        f"translator={context.translator is not None if context else 'N/A'}, "
                        f"user_language={context.user_language if context else 'N/A'}"
                    )
                    if (
                        context
                        and context.translator
                        and context.user_language
                        and context.user_language != "en"
                        and original_char_text
                    ):
                        try:
                            logger.info(
                                f"[{context.request_id}] [NO-CONFIG] Starting translation en → {context.user_language}"
                            )
                            # Translate it
                            req = TranslationRequest(
                                source_text=original_char_text,
                                source_lang="en",
                                target_lang=context.user_language,
                                context="A female character's chat message to a male user.",
                                context_key=f"char_response:{message_hash}",
                            )
                            res = await context.translator.translate(req)
                            translated_char_text = res.translated_text
                            logger.info(
                                f"[{context.request_id}] [NO-CONFIG] ✅ Translated: '{original_char_text[:50]}...' → '{translated_char_text[:50]}...'"
                            )
                        except Exception as e:
                            logger.error(
                                f"[{context.request_id}] [NO-CONFIG] ❌ Translation failed: {e}"
                            )
                            sentry_sdk.capture_exception(e)
                    else:
                        logger.info(
                            f"[{context.request_id}] [NO-CONFIG] Skipping translation (will send in English)"
                        )

                    final_messages_to_send.append(
                        SendChatMessageOutputSubDTO(message=translated_char_text)
                    )

                    # Process payment for the original message
                    paid_action_dataset = await async_get_paid_action_dataset(
                        PaidActions.MESSAGE.value
                    )
                    additional_data = {
                        "char_id": char_id,
                        "message_id": message_dto.message.id,
                        "tariff_plan_id": tariff_plan_id,
                    }
                    logger.info(
                        f"🔵 [BILLING DEBUG] CALLING MESSAGE BILLING (non-config): user_id={user_id}, char_id={char_id}, message_id={message_dto.message.id}, price={paid_action_dataset.price}"
                    )
                    await async_process_paid_action(
                        user_id,
                        paid_action_dataset,
                        SourceNames.TELEGRAM,
                        additional_data,
                    )
                    logger.info(
                        f"✅ [BILLING DEBUG] MESSAGE BILLING (non-config) CALL COMPLETED: user_id={user_id}, char_id={char_id}"
                    )

                elif message_dto.message_type == ChatTypesMessageType.IMAGE.value:
                    # Проверка баланса перед добавлением изображения (legacy flow без config_id)
                    # message_dto.message_image может быть ImageInfo или dict (из DetachedFullMessageDTO)
                    image_info = message_dto.message_image
                    image_id = None
                    image_rating = None

                    # Обрабатываем как ImageInfo объект или как dict
                    if image_info:
                        if isinstance(image_info, dict):
                            image_id = image_info.get("id")
                            image_rating = image_info.get("rating")
                        else:
                            # Это ImageInfo объект
                            image_id = image_info.id
                            image_rating = image_info.rating

                    if image_id and image_rating:
                        # Определяем paid_action на основе rating
                        paid_action_name = map_bff_image_type_to_paid_action_name(
                            image_rating
                        )
                        paid_action_dataset = await async_get_paid_action_dataset(
                            paid_action_name
                        )

                        # Проверяем баланс перед добавлением изображения
                        try:
                            await async_check_user_have_enough_currency(
                                user_id,
                                paid_action_dataset.price,
                                CurrenciesTypes.TOKEN.value,
                            )
                            # Баланс достаточен - добавляем изображение
                            final_messages_to_send.append(
                                SendChatMessageOutputSubDTO.from_attachment(
                                    message_dto.message
                                )
                            )

                            # Списываем токены за изображение
                            additional_data = {
                                "char_id": char_id,
                                "image_id": str(image_id),
                                "tariff_plan_id": tariff_plan_id,
                            }
                            logger.info(
                                f"🔵 [BILLING DEBUG] CALLING IMAGE BILLING (legacy, from text): user_id={user_id}, char_id={char_id}, image_id={image_id}, rating={image_rating}, price={paid_action_dataset.price}"
                            )
                            await async_process_paid_action(
                                user_id,
                                paid_action_dataset,
                                SourceNames.TELEGRAM,
                                additional_data,
                            )
                            logger.info(
                                f"✅ [BILLING DEBUG] IMAGE BILLING CALL COMPLETED (legacy, from text): user_id={user_id}, char_id={char_id}"
                            )

                            # Помечаем изображение как просмотренное ТОЛЬКО после успешной отправки
                            # Конвертируем image_id в UUID, если это строка
                            image_uuid = (
                                UUID(image_id)
                                if isinstance(image_id, str)
                                else image_id
                            )
                            user_view = UserImageView(
                                user_id=user_id, image_id=image_uuid
                            )
                            session.add(user_view)
                            logger.info(
                                f"✅ [IMAGE VIEW] Marked image {image_id} as viewed for user {user_id} (legacy)"
                            )
                        except NotEnoughCurrencyError:
                            # Недостаточно токенов - всегда добавляем NO_TOKENS сообщение с клавиатурой
                            logger.info(
                                f"❌ [BILLING DEBUG] Insufficient balance for image (legacy, from text): user_id={user_id}, char_id={char_id}, image_id={image_id}, rating={image_rating}"
                            )
                            final_messages_to_send.append(
                                SendChatMessageOutputSubDTO(
                                    message=TemplateMessages.NO_TOKENS.value,
                                    insufficient_balance=True,
                                )
                            )
                            # Изображение НЕ помечается как просмотренное, так как оно не было отправлено пользователю
                    else:
                        # Не удалось получить rating - добавляем изображение без проверки (fallback)
                        logger.warning(
                            f"⚠️ [BILLING DEBUG] Could not get rating for image (legacy), image_info={image_info}, adding without balance check"
                        )
                        final_messages_to_send.append(
                            SendChatMessageOutputSubDTO.from_attachment(
                                message_dto.message
                            )
                        )

        # Delete "Typing..." message after all processing is complete
        if (
            typing_message_id
            and context
            and context.telegram_chat_id
            and context.bot_token
        ):
            try:
                await delete_message(
                    context.telegram_chat_id, typing_message_id, context.bot_token
                )
            except Exception as e:
                logger.error(f"Failed to delete typing message: {e}")

        return SendChatMessageOutputDTO(messages=final_messages_to_send)

    except TariffPlanExpired:
        # Delete "Typing..." message if it was sent
        if (
            typing_message_id
            and context
            and context.telegram_chat_id
            and context.bot_token
        ):
            try:
                await delete_message(
                    context.telegram_chat_id, typing_message_id, context.bot_token
                )
            except Exception as e:
                logger.error(f"Failed to delete typing message: {e}")

        return SendChatMessageOutputDTO.from_single_text_message(
            message="Your tariff plan has expired"
        )
    except NotEnoughCurrencyError:
        # Delete "Typing..." message if it was sent
        if (
            typing_message_id
            and context
            and context.telegram_chat_id
            and context.bot_token
        ):
            try:
                await delete_message(
                    context.telegram_chat_id, typing_message_id, context.bot_token
                )
            except Exception as e:
                logger.error(f"Failed to delete typing message: {e}")

        return SendChatMessageOutputDTO(
            messages=[
                SendChatMessageOutputSubDTO(
                    message=TemplateMessages.NO_TOKENS.value, insufficient_balance=True
                )
            ]
        )
    except Exception as e:
        await session.rollback()
        # Delete "Typing..." message if it was sent
        if (
            typing_message_id
            and context
            and context.telegram_chat_id
            and context.bot_token
        ):
            try:
                await delete_message(
                    context.telegram_chat_id, typing_message_id, context.bot_token
                )
            except Exception as del_e:
                logger.error(
                    f"Failed to delete typing message on general exception: {del_e}"
                )
        raise e
    else:
        await session.commit()
    # This part of the code seems to be unreachable or has logic that is now handled above.
    # Refactoring it to be cleaner.
    # The return is now handled inside the main try block.
    return SendChatMessageOutputDTO(messages=[])
