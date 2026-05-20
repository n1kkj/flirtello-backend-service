from decimal import Decimal
from typing import Optional
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
from src.telegram.config import STORAGE_ROOT, logger
from src.telegram.context import RequestContext
from src.telegram.handlers.media import handle_photo_request
from src.telegram.keyboards import create_context_keyboard
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.lib.insufficient_balance import (
    check_and_notify_zero_balance,
    send_no_tokens_message_with_keyboards,
)
from src.telegram.template_messages import TemplateMessages


async def process_photo_command(
    sender_chat_id: int,
    session: AsyncSession,
    user: ChatUser,
    active_char_id: Optional[int],
    config_id: Optional[UUID],
    token: str,
    context: RequestContext,
    background_tasks: BackgroundTasks,
    lang_code: str,
    user_message_id: Optional[int] = None,
):
    """Processes the /photo command or 'Get Image' button to request a character photo."""
    if active_char_id is None:
        logger.error(
            f"Critical error: active_char_id is None for /photo for user {user.id} (TG: {sender_chat_id})."
        )
        await send_tg_message(
            sender_chat_id,
            "Произошла ошибка: не удалось определить персонажа. Пожалуйста, попробуйте выбрать персонажа снова через /list или /start.",
            token,
        )
        return
    
    # Проверка баланса ПЕРЕД запросом изображения
    _ = get_gettext_for_language(lang_code)
    try:
        # Проверяем, есть ли у пользователя хотя бы 1 токен
        await async_check_user_have_enough_currency(
            user.id, Decimal(1), CurrenciesTypes.TOKEN.value
        )
        logger.info(f"✅ [PHOTO] User {user.id} has enough tokens, proceeding with photo request")
    except NotEnoughCurrencyError:
        # Недостаточно токенов - отправляем сообщение с клавиатурами
        logger.info(f"❌ [PHOTO] User {user.id} failed pre-check for illustration due to insufficient funds (less than 1 token).")
        
        await send_no_tokens_message_with_keyboards(
            sender_chat_id=sender_chat_id,
            message_text=_(TemplateMessages.NO_TOKENS.value),
            token=token,
            lang_code=lang_code,
            context=context,
            source="photo_precheck",
            user_message_id=user_message_id,
        )
        logger.info(f"✅ [PHOTO] NO_TOKENS message sent with keyboards to user {user.id}")
        return
    
    photo_message_dto = await handle_photo_request(
        session=session,
        user_id=user.id,
        char_id=active_char_id,
        sender_chat_id=sender_chat_id,
        token=token,
        context=context,
        background_tasks=background_tasks,
        config_id=config_id,
    )
    
    if photo_message_dto:  # Если DTO вернулся, его нужно отправить
        if photo_message_dto.attachments:
            for attachment in photo_message_dto.attachments:
                if attachment.type == "image":
                    await send_tg_chat_action_upload_photo(
                        sender_chat_id, token
                    )
                    image = await session.get(ImageInfo, attachment.id)
                    if image is None:
                        logger.error(
                            f"ImageInfo {attachment.id} not found for /photo command."
                        )
                        await send_tg_message(
                            sender_chat_id,
                            "Ошибка: не удалось найти данные изображения для /photo.",
                            token,
                        )
                        continue
                    file = await session.get(DirectusFile, image.image)
                    if file is None:
                        logger.error(
                            f"DirectusFile {image.image} not found for ImageInfo {attachment.id} for /photo command."
                        )
                        await send_tg_message(
                            sender_chat_id,
                            "Ошибка: не удалось найти файл изображения для /photo.",
                            token,
                        )
                        continue
                    await download_and_send_image(
                        f"{STORAGE_ROOT}/{file.filename_disk}",
                        str(sender_chat_id),
                        True,
                        token,
                        caption=photo_message_dto.message,
                    )
                else:
                    logger.warning(
                        f"Unsupported attachment type '{attachment.type}' in /photo command processing."
                    )
        elif photo_message_dto.message:  # Если нет вложений, но есть текст
            _ = get_gettext_for_language(lang_code)
            
            if photo_message_dto.insufficient_balance:
                # NO_TOKENS - используем единую функцию для отправки с правильной логикой клавиатур
                await send_no_tokens_message_with_keyboards(
                    sender_chat_id=sender_chat_id,
                    message_text=_(photo_message_dto.message),
                    token=token,
                    lang_code=lang_code,
                    context=context,
                    source="photo_insufficient",
                )
            else:
                # Обычное сообщение
                await send_tg_message(
                    sender_chat_id,
                    photo_message_dto.message,
                    token,
                    reply_markup=create_context_keyboard(lang_code),
                )
        else:
            logger.info(
                f"Received empty DTO from handle_photo_request for /photo command: {photo_message_dto}"
            )
        
        # Проактивная проверка баланса (только если не было недостатка средств)
        if photo_message_dto and not photo_message_dto.insufficient_balance:
            await check_and_notify_zero_balance(
                user_id=user.id,
                sender_chat_id=sender_chat_id,
                token=token,
                context=context,
                session=session,
            )
    # Если photo_message_dto is None, значит handle_photo_request уже сам отправил сообщение об ошибке (напр. нет денег)
