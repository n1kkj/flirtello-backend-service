import os
from decimal import Decimal
from typing import Optional
from uuid import UUID

import httpx
import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.lib.auth import SupabaseAuth
from src.db.lib.content_models import DirectusFile, ImageInfo
from src.telegram.api import (
    download_and_send_image,
    send_tg_chat_action_typing,
    send_tg_chat_action_upload_photo,
    send_tg_message,
)
from src.telegram.chat_logic import create_user_by_tg_data, start_new_chat_tg
from src.telegram.config import (
    STORAGE_ROOT,
    TELEGRAM_BOT_TOKEN,
    logger,
    personal_tokens,
)
from src.telegram.context import RequestContext
from src.telegram.handlers.utils import merge_attachment_messages
from src.telegram.keyboards import create_context_keyboard
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.lib.insufficient_balance import (
    check_and_notify_zero_balance,
    send_no_tokens_message_with_keyboards,
)
from src.telegram.template_messages import TemplateMessages
from src.telegram.utils.free_tokens import (
    give_user_free_tokens,
    should_give_free_tokens,
)
from src.telegram.utils.get_user_chat_setting import (
    get_current_config_id,
)


async def handle_callback_query(
    data: dict,
    session: AsyncSession,
    context_token: str,
    auth_handler: SupabaseAuth,
    context: RequestContext,
):
    lang_code = context.user_language or "en"
    _ = get_gettext_for_language(lang_code)
    callback_query = data["callback_query"]
    callback_data_str = callback_query["data"]
    sender_tg_id = callback_query["from"]["id"]
    message_id = callback_query["message"]["message_id"]

    token_for_callback_actions = context_token

    if callback_data_str == "get_free_tokens":
        user = auth_handler.find_user_by_tg_id(sender_tg_id)
        if user:
            if not await should_give_free_tokens(session, user.id):
                await give_user_free_tokens(session, user.id, Decimal("30.0"))
                await send_tg_message(
                    sender_tg_id,
                    _(
                        "Here's a gift for you, darling! 💝 30 free tokens just for you! Let's continue our chat... 😘"
                    ),
                    token_for_callback_actions,
                )
            else:
                await send_tg_message(
                    sender_tg_id,
                    _("You already have free tokens, darling! 💝 Let's continue our chat... 😘"),
                    token_for_callback_actions,
                )
        BASE_URL_CB_GF = f"https://api.telegram.org/bot{token_for_callback_actions}"
        answer_payload_gf = {"callback_query_id": callback_query["id"]}
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{BASE_URL_CB_GF}/answerCallbackQuery", json=answer_payload_gf)
        except Exception as e_ans_cb_gf:
            logger.error(f"Failed to answer get_free_tokens callback query: {e_ans_cb_gf}")

    elif callback_data_str.startswith("/start "):
        logger.info(f"Handling /start callback: {callback_data_str}")

        parsed_char_id: Optional[int] = None
        parsed_config_id_from_callback: Optional[UUID] = None

        parts = callback_data_str.split(" ")
        if len(parts) >= 2 and parts[1].isdigit():
            parsed_char_id = int(parts[1])
            if len(parts) >= 3:
                try:
                    parsed_config_id_from_callback = UUID(parts[2])
                    logger.info(
                        f"Parsed config_id from callback data: {parsed_config_id_from_callback}"
                    )
                except ValueError:
                    logger.warning(
                        f"Invalid UUID string in callback data '{parts[2]}'. Treating as no explicit config_id."
                    )
                    parsed_config_id_from_callback = None

        if parsed_char_id is None:
            logger.error(f"Could not parse char_id from callback data: {callback_data_str}")
            BASE_URL_CB_ERR = f"https://api.telegram.org/bot{token_for_callback_actions}"
            err_payload = {
                "callback_query_id": callback_query["id"],
                "text": _("Error: invalid character data"),
            }
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(f"{BASE_URL_CB_ERR}/answerCallbackQuery", json=err_payload)
            except Exception as e_ans_cb_err:
                logger.error(f"Failed to answer error callback query: {e_ans_cb_err}")
            return

        user = auth_handler.find_user_by_tg_id(sender_tg_id)
        if not user:
            try:
                user = create_user_by_tg_data(callback_query["from"])
                logger.info(
                    f"Created new user for TG ID {sender_tg_id} from callback query: user ID {user.id}"
                )
            except Exception as e_create_user:
                logger.error(
                    f"Failed to create user from callback for TG ID {sender_tg_id}: {e_create_user}",
                    exc_info=True,
                )
                await send_tg_message(
                    sender_tg_id,
                    _(
                        "Error: could not create or find your user. Please send /start to the bot first."
                    ),
                    token_for_callback_actions,
                )
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            f"https://api.telegram.org/bot{token_for_callback_actions}/answerCallbackQuery",
                            json={
                                "callback_query_id": callback_query["id"],
                                "text": _("User error"),
                            },
                        )
                except Exception:
                    pass
            return
        else:
            logger.info(f"Found existing user: {user.id}, TG ID: {sender_tg_id}")

        mock_message_data = {"message": {"chat": {"type": "private"}}}

        try:
            await send_tg_chat_action_typing(sender_tg_id, token_for_callback_actions)

            token_for_selected_char = TELEGRAM_BOT_TOKEN
            if parsed_char_id in personal_tokens:
                token_for_selected_char = personal_tokens[parsed_char_id]
            else:
                env_token_name = f"PERSON_BOT_TOKEN_{parsed_char_id}"
                char_specific_token = os.environ.get(env_token_name)
                if char_specific_token:
                    personal_tokens[parsed_char_id] = char_specific_token
                    token_for_selected_char = char_specific_token
            logger.info(
                f"Token for selected char {parsed_char_id} messages: {' персон.' if token_for_selected_char != TELEGRAM_BOT_TOKEN else ' общий'}"
            )

            logger.info(
                f"Calling start_new_chat_tg from callback with char_id={parsed_char_id}, user_id={user.id}, explicit_config_id={parsed_config_id_from_callback}"
            )

            # Determine the effective config_id to use for the callback
            # If the callback data contains an explicit config_id, use that.
            # Otherwise, pass None to start_new_chat_tg. It should then use the character's default config.
            # We explicitly DO NOT want to use config_id_from_user_settings here when a user selects a character from a list,
            # as the expectation is to start fresh with that character's default, not a potentially unrelated config.
            config_id_from_user_settings = await get_current_config_id(
                session, user.id
            )  # Logged for context, but not used for fallback here
            logger.info(
                f"Callback: config_id from user settings (for context only): {config_id_from_user_settings} for user {user.id}"
            )

            effective_config_id_for_callback = parsed_config_id_from_callback
            if effective_config_id_for_callback is not None:
                logger.info(
                    f"Callback: Using explicit config_id from callback data: {effective_config_id_for_callback}"
                )
            else:
                logger.info(
                    "Callback: No explicit config_id in callback data. Passing None to start_new_chat_tg for explicit_config_id."
                )

            logger.info(
                f"Calling start_new_chat_tg from callback with char_id={parsed_char_id}, user_id={user.id}, effective_config_id_to_use={effective_config_id_for_callback}"
            )
            first_messages_response = await start_new_chat_tg(
                data=mock_message_data,
                char_id=parsed_char_id,
                user=user,
                session=session,
                explicit_config_id=effective_config_id_for_callback,
                context=context,
            )
            logger.info(f"start_new_chat_tg response: {first_messages_response}")
            # session.commit() должен вызываться после всех операций с сессией в start_new_chat_tg или здесь, если start_new_chat_tg его не делает
            # В текущей реализации start_new_chat_tg делает коммит.
            # Однако, reset_images_user также вызывается в start_new_chat_tg и делает коммит.
            # Это может быть избыточным. Но для сохранения логики, оставляем как есть.

            # Ответ на callback и удаление сообщения лучше делать после успешного старта чата
            BASE_URL_CB_ACTION = f"https://api.telegram.org/bot{token_for_callback_actions}"

            answer_payload_cs = {"callback_query_id": callback_query["id"]}
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{BASE_URL_CB_ACTION}/answerCallbackQuery", json=answer_payload_cs
                    )
                    logger.info(f"Successfully answered callback query {callback_query['id']}")
            except Exception as e_ans_cb_cs:
                logger.error(f"Failed to answer char selection callback query: {e_ans_cb_cs}")

            logger.info(
                f"Attempting to delete original character selection message {message_id} for chat {sender_tg_id}"
            )
            delete_payload = {"chat_id": sender_tg_id, "message_id": message_id}
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(f"{BASE_URL_CB_ACTION}/deleteMessage", json=delete_payload)
                    logger.info(f"Successfully deleted message {message_id} for chat {sender_tg_id}")
            except Exception as e_delete:
                logger.warning(
                    f"Failed to delete message {message_id} for chat {sender_tg_id}: {e_delete}",
                    exc_info=True,
                )

            logger.info(
                f"Processing first messages from new chat. Count: {len(first_messages_response.messages) if first_messages_response and first_messages_response.messages else 0}"
            )
            if first_messages_response and first_messages_response.messages:
                processed_messages = merge_attachment_messages(first_messages_response.messages)
                
                # Разделяем сообщения на обычные и NO_TOKENS
                regular_messages = []
                has_insufficient_balance = False
                
                for msg in processed_messages:
                    if msg.insufficient_balance:
                        has_insufficient_balance = True
                        logger.info(f"Detected insufficient_balance in callback: {msg.message[:50]}...")
                    else:
                        regular_messages.append(msg)
                
                # Отправка обычных сообщений
                for msg_dto in regular_messages:
                    logger.info(
                        f"Sending first message part: '{str(msg_dto.message)[:50]}...', attachments: {len(msg_dto.attachments) if msg_dto.attachments else 0}"
                    )
                    # Message is already translated in start_chat_with_char
                    translated_message = msg_dto.message
                    if msg_dto.attachments:
                        for attachment in msg_dto.attachments:
                            await send_tg_chat_action_upload_photo(
                                sender_tg_id, token_for_selected_char
                            )
                            image = await session.get(ImageInfo, attachment.id)
                            if image is None:
                                logger.error(
                                    f"Image {attachment.id} not found for char {parsed_char_id}"
                                )
                                await send_tg_message(
                                    sender_tg_id,
                                    _("Problems loading the picture... 💔"),
                                    token_for_selected_char,
                                )
                                continue
                            file_entry = await session.get(DirectusFile, image.image)
                            if file_entry is None:
                                logger.error(
                                    f"File {image.image} not found for char {parsed_char_id}"
                                )
                                await send_tg_message(
                                    sender_tg_id,
                                    _("Picture file not found... 💔"),
                                    token_for_selected_char,
                                )
                                continue
                            await download_and_send_image(
                                f"{STORAGE_ROOT}/{file_entry.filename_disk}",
                                str(sender_tg_id),
                                True,
                                token_for_selected_char,
                                caption=translated_message,
                            )
                    else:
                        # Обычное текстовое сообщение
                        await send_tg_message(
                            sender_tg_id,
                            translated_message,
                            token_for_selected_char,
                            reply_markup=create_context_keyboard(lang_code),
                        )
                
                # NO_TOKENS сообщение ПОСЛЕДНИМ
                if has_insufficient_balance:
                    await send_no_tokens_message_with_keyboards(
                        sender_chat_id=sender_tg_id,
                        message_text=_(TemplateMessages.NO_TOKENS.value),
                        token=token_for_selected_char,
                        lang_code=lang_code,
                        context=context,
                        source="character_selection",
                    )
                    logger.info("✅ NO_TOKENS sent as last message in callback with keyboards")
                
                # Проактивная проверка баланса (только если не было недостатка средств)
                if not has_insufficient_balance:
                    await check_and_notify_zero_balance(
                        user_id=user.id,
                        sender_chat_id=sender_tg_id,
                        token=token_for_selected_char,
                        context=context,
                        session=session,
                    )
                
                # Коммит сессии, если он не был сделан в start_new_chat_tg или если были другие операции с сессией здесь
                await session.commit()  # Добавляем коммит здесь, так как reset_images_user и сохранение настроек могут быть в start_new_chat_tg
                # и get_illustration в handle_photo_request также работает с сессией.
                # Основной коммит после всей обработки запроса.
        except Exception as e_char_select_logic:
            await session.rollback()
            sentry_sdk.capture_exception(e_char_select_logic)
            logger.error(
                f"Error processing char selection callback: {e_char_select_logic}", exc_info=True
            )
            await send_tg_message(
                sender_tg_id,
                _("An internal error occurred while selecting the character."),
                token_for_callback_actions,
            )
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{token_for_callback_actions}/answerCallbackQuery",
                        json={"callback_query_id": callback_query["id"], "text": _("Processing error")},
                    )
            except Exception as answer_e:
                logger.error(f"Failed to answer processing error callback query: {answer_e}")
    else:
        # Неизвестный callback_data
        logger.warning(f"Unknown callback_data received: {callback_data_str}")
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{token_for_callback_actions}/answerCallbackQuery",
                    json={"callback_query_id": callback_query["id"], "text": _("Unknown action")},
                )
        except Exception as e:
            logger.error(f"Failed to answer unknown callback query: {e}")

    # session.commit() # Коммит убран отсюда, будет в dispatcher'e 