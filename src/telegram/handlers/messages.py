import os
import random
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.lib.billing.common.enums import CurrenciesTypes
from src.db.lib.billing.common.exceptions import NotEnoughCurrencyError
from src.db.lib.chat_models import ChatUser
from src.db.lib.content_models import DirectusFile, ImageInfo
from src.telegram.api import (
    download_and_send_image,
    send_tg_chat_action_upload_photo,
    send_tg_message,
)
from src.telegram.async_adapters import async_check_user_have_enough_currency
from src.telegram.chat_logic import write_to_current_chat
from src.telegram.config import STORAGE_ROOT, logger
from src.telegram.context import RequestContext
from src.telegram.DTO.chat import SendChatMessageOutputSubDTO
from src.telegram.handlers.media import handle_photo_request
from src.telegram.handlers.utils import merge_attachment_messages
from src.telegram.keyboards import create_context_keyboard
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.lib.insufficient_balance import (
    check_and_notify_zero_balance,
    send_no_tokens_message_with_keyboards,
)
from src.telegram.template_messages import TemplateMessages


async def process_regular_message(
    data: dict,
    known_char_id: int,
    token: str,
    config_id: Optional[UUID],
    sender_chat_id: int,
    session: AsyncSession,
    user: ChatUser,
    context: RequestContext,
):
    # Сначала получаем ответ от персонажа на текстовое сообщение пользователя
    lang_code = context.user_language or "en"
    _ = get_gettext_for_language(lang_code)
    text_response_dto_list = await write_to_current_chat(
        data, known_char_id, token, user, session, config_id, context
    )

    all_messages_to_send: List[SendChatMessageOutputSubDTO] = []
    initial_text_responses_had_image = False

    if text_response_dto_list and text_response_dto_list.messages:
        all_messages_to_send.extend(text_response_dto_list.messages)
        # Check if any of these initial messages contain an image attachment
        for msg_dto in text_response_dto_list.messages:
            if msg_dto.attachments:
                for att in msg_dto.attachments:
                    if att.type == "image":
                        initial_text_responses_had_image = True
                        logger.info(
                            f"Initial response from write_to_current_chat already contained an image. Skipping additional photo request for user {user.id}, char {known_char_id}."
                        )
                        break  # Found an image, no need to check further in this msg_dto
            if initial_text_responses_had_image:
                break  # Found an image in one of the messages, no need to check other messages

    # Затем пытаемся получить иллюстрацию (картинку) от персонажа,
    # ЕСЛИ начальный ответ не содержал картинку
    if not initial_text_responses_had_image:
        # Новая логика: пытаемся добавить картинку случайно, если ее не было
        # Получаем N из переменной окружения, по умолчанию 2
        random_image_every_n = int(os.environ.get("RANDOM_IMAGE_EVERY_N_MESSAGES", 1))
        should_add_random_image = False
        if (
            random_image_every_n > 0
        ):  # Если N=0 или меньше, никогда не добавляем случайно
            should_add_random_image = (
                random.randint(0, random_image_every_n - 1) == 0
            )  # Вероятность 1/N

        if should_add_random_image:
            logger.info(
                f"Attempting to add random image (1 out of {random_image_every_n} chance). User: {user.id}, char: {known_char_id}."
            )

            # Проверка баланса ПЕРЕД запросом изображения (как в process_photo_command)
            try:
                # Проверяем, есть ли у пользователя хотя бы 1 токен
                await async_check_user_have_enough_currency(
                    user.id, Decimal(1), CurrenciesTypes.TOKEN.value
                )
                logger.info(
                    f"✅ [MESSAGES] User {user.id} has enough tokens for random image, proceeding"
                )
            except NotEnoughCurrencyError:
                # Недостаточно токенов - пропускаем добавление случайного изображения
                logger.info(
                    f"❌ [MESSAGES] User {user.id} failed pre-check for random image due to insufficient funds (less than 1 token). Skipping random image."
                )
                # Не добавляем изображение, продолжаем обработку обычных сообщений
            else:
                # Эта функция теперь возвращает DTO или None
                background_tasks = (
                    BackgroundTasks()
                )  # Создаем экземпляр для background tasks
                photo_message_dto = await handle_photo_request(
                    session=session,
                    user_id=user.id,
                    char_id=known_char_id,
                    sender_chat_id=sender_chat_id,
                    token=token,
                    context=context,
                    background_tasks=background_tasks,
                    config_id=config_id,
                )

                # ✅ ИСПРАВЛЕНИЕ: Запускаем background tasks вручную
                # В Telegram dispatcher нет автоматического выполнения BackgroundTasks
                if background_tasks.tasks:
                    for task in background_tasks.tasks:
                        import asyncio

                        asyncio.create_task(task.func(*task.args, **task.kwargs))
                    logger.info(
                        f"Started {len(background_tasks.tasks)} background tasks for user {user.id}"
                    )

                if photo_message_dto:
                    all_messages_to_send.append(photo_message_dto)
                    logger.info(
                        f"Random image DTO added. User: {user.id}, char: {known_char_id}."
                    )
                else:
                    logger.info(
                        f"Random image request was made but handle_photo_request returned None (e.g. error or no image). User: {user.id}, char: {known_char_id}."
                    )
        else:
            logger.info(
                f"Skipping random image addition based on chance (1 out of {random_image_every_n}). User: {user.id}, char: {known_char_id}."
            )
    else:
        logger.info(
            f"Skipped handle_photo_request as initial response already had an image for user {user.id}, char {known_char_id}."
        )

    logger.info(f"Total messages before merging: {all_messages_to_send}")

    # Разделяем сообщения на обычные и NO_TOKENS
    has_insufficient_balance = False

    # Объединяем все собранные сообщения (текстовые ответы + возможное сообщение с картинкой)
    if all_messages_to_send:
        merged_messages = merge_attachment_messages(all_messages_to_send)
        logger.info(f"Messages after merging: {merged_messages}")

        regular_messages = []

        for msg in merged_messages:
            if msg.insufficient_balance:
                has_insufficient_balance = True
                # НЕ добавляем в regular_messages - отправим отдельно в конце
                logger.info(
                    f"Detected insufficient_balance message: {msg.message[:50]}..."
                )
            else:
                regular_messages.append(msg)

        # Отправка обычных сообщений
        for message_dto in regular_messages:
            # Message is already translated in get_response_from_character
            translated_message = message_dto.message
            if message_dto.attachments:
                # Отправка изображения
                for attachment in message_dto.attachments:
                    if attachment.type == "image":
                        await send_tg_chat_action_upload_photo(sender_chat_id, token)
                        image = await session.get(ImageInfo, attachment.id)
                        if image is None:
                            logger.error(
                                f"ImageInfo {attachment.id} not found during sending."
                            )
                            await send_tg_message(
                                sender_chat_id,
                                _("Error: could not find image data."),
                                token,
                            )
                            continue
                        file = await session.get(DirectusFile, image.image)
                        if file is None:
                            logger.error(
                                f"DirectusFile {image.image} not found for ImageInfo {attachment.id}."
                            )
                            await send_tg_message(
                                sender_chat_id,
                                _("Error: could not find image file."),
                                token,
                            )
                            continue

                        await download_and_send_image(
                            f"{STORAGE_ROOT}/{file.filename_disk}",
                            str(sender_chat_id),
                            True,
                            token,
                            caption=translated_message,
                        )
                    else:
                        logger.warning(
                            f"Unsupported attachment type '{attachment.type}' in process_regular_message."
                        )
            elif message_dto.message:
                # Обычное текстовое сообщение с reply keyboard
                await send_tg_message(
                    sender_chat_id,
                    translated_message,
                    token,
                    reply_markup=create_context_keyboard(lang_code),
                )
            else:
                logger.info(f"Skipping empty message_dto after merge: {message_dto}")

        # Отправка NO_TOKENS сообщения ПОСЛЕДНИМ
        if has_insufficient_balance:
            await send_no_tokens_message_with_keyboards(
                sender_chat_id=sender_chat_id,
                message_text=_(TemplateMessages.NO_TOKENS.value),
                token=token,
                lang_code=lang_code,
                context=context,
                source="text_message_insufficient",
            )
            logger.info("✅ NO_TOKENS sent as last message with keyboards")
    else:
        logger.info("No messages to send after processing text and photo requests.")

    # Проактивная проверка баланса (только если не было сообщения о недостатке средств)
    if not has_insufficient_balance:
        await check_and_notify_zero_balance(
            user_id=user.id,
            sender_chat_id=sender_chat_id,
            token=token,
            context=context,
            session=session,
        )
