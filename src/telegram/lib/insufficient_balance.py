"""
Проактивное уведомление о нулевом балансе.

Этот модуль содержит логику для проверки баланса пользователя после обработки запроса
и отправки уведомления, если баланс достиг нуля.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.lib.billing.balance_transactions import async_get_user_balance
from src.telegram.api import delete_message, send_tg_message
from src.telegram.context import RequestContext
from src.telegram.keyboards import create_get_tokens_keyboard
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.lib.sender_utils import send_mkt_event_fire_and_forget

logger = logging.getLogger(__name__)


async def send_no_tokens_message_with_keyboards(
    sender_chat_id: int,
    message_text: str,
    token: str,
    lang_code: str,
    context: RequestContext,
    source: str = "unknown",
    user_message_id: Optional[int] = None,
) -> None:
    """
    Отправляет сообщение NO_TOKENS с inline клавиатурой "Get Tokens".

    Используется только inline клавиатура, так как пользователь не может выполнять действия
    без токенов. Reply клавиатура (Get Image, Continue) не нужна в этом случае.

    Args:
        sender_chat_id: Telegram chat ID для отправки сообщения
        message_text: Текст сообщения (уже переведенный)
        token: Bot token для API вызовов
        lang_code: Код языка пользователя
        context: Request context с user_id для аналитики
        source: Источник показа клавиатуры для аналитики
        user_message_id: Опциональный ID сообщения пользователя для удаления
    """
    # Удаляем сообщение пользователя, если указано
    if user_message_id:
        try:
            await delete_message(sender_chat_id, user_message_id, token)
            logger.info(f"🗑️ [NO_TOKENS] Deleted user message {user_message_id}")
        except Exception as e:
            logger.warning(f"⚠️ [NO_TOKENS] Failed to delete user message: {e}")

    # Отправляем сообщение с inline клавиатурой "Get Tokens"
    inline_markup = create_get_tokens_keyboard(lang_code)
    logger.info("🔑 [NO_TOKENS] Sending NO_TOKENS message with inline keyboard")
    await send_tg_message(
        sender_chat_id,
        message_text,
        token,
        reply_markup=inline_markup,
    )

    # Send analytics event
    if context.user_id:
        event_params = {"source": source}
        if context.active_char_id is not None:
            event_params["active_char_id"] = context.active_char_id

        await send_mkt_event_fire_and_forget(
            context.user_id, "tg_no_tokens_keyboard_shown", event_params
        )

    logger.info(
        f"✅ [NO_TOKENS] NO_TOKENS message sent with keyboards to chat {sender_chat_id}"
    )


async def check_and_notify_zero_balance(
    user_id: UUID,
    sender_chat_id: int,
    token: str,
    context: RequestContext,
    session: AsyncSession,
) -> None:
    """
    Проверяет баланс пользователя после обработки запроса.
    Если баланс = 0, отправляет проактивное уведомление с клавиатурой покупки токенов.

    Эта функция должна вызываться в конце каждого handler'а (messages, photo, start, callbacks)
    после основной обработки запроса, но ДО того как было отправлено сообщение о недостатке баланса
    через use case (чтобы не дублировать уведомления).

    Логика:
    1. Проверяем текущий баланс пользователя
    2. Если баланс = 0, отправляем уведомление
    3. Уведомление содержит:
       - Inline кнопку "Get Tokens" для пополнения

    Args:
        user_id: UUID пользователя
        sender_chat_id: Telegram chat ID для отправки сообщения
        token: Bot token для API вызовов
        context: Request context с языком пользователя
        session: Database session

    Note:
        Функция не отправляет уведомление, если баланс > 0.
        Уведомление отправляется только один раз за запрос (при достижении нуля).
    """
    try:
        # Получаем текущий баланс пользователя
        balance = await async_get_user_balance(session, user_id, "TOKEN")

        # Если баланс = 0, отправляем проактивное уведомление
        if balance <= 0:
            lang_code = context.user_language or "en"
            _ = get_gettext_for_language(lang_code)

            # Сообщение о нулевом балансе (переведенное)
            message = _(
                "⚠️ Your token balance has reached 0.\n"
                "Get more tokens to continue chatting! 💝"
            )

            # Используем единую функцию для отправки NO_TOKENS с правильной логикой клавиатур
            await send_no_tokens_message_with_keyboards(
                sender_chat_id=sender_chat_id,
                message_text=message,
                token=token,
                lang_code=lang_code,
                context=context,
                source="balance_reached_zero",
            )

            logger.info(
                f"✅ Proactive zero-balance notification sent to user {user_id} "
                f"(chat_id: {sender_chat_id})"
            )
        else:
            logger.debug(
                f"Balance check for user {user_id}: {balance} tokens (no notification needed)"
            )

    except Exception as e:
        # Логируем ошибку, но не прерываем обработку запроса
        logger.error(
            f"Error checking balance for proactive notification for user {user_id}: {e}",
            exc_info=True,
        )
