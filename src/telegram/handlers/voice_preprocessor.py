"""
Voice message preprocessor for STT (Speech-to-Text).

This module handles the conversion of voice messages to text before regular message processing.
It also checks user balance for STT and TTS operations.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.lib.chat_models import ChatUser
from src.telegram.config import logger
from src.telegram.context import RequestContext


async def preprocess_voice_to_text(
    data: dict,
    token: str,
    user: ChatUser,
    sender_chat_id: int,
    session: AsyncSession,
    context: RequestContext,
) -> Optional[dict]:
    """
    ПРЕПРОЦЕССОР: Конвертирует voice в text с проверкой баланса на STT и TTS.
    
    Этот препроцессор выполняется на самом раннем этапе обработки сообщения.
    
    Логика:
    1. Проверяем, есть ли voice в data
    2. Получаем стоимость STT (PaidActions.VOICE_TO_TEXT)
    3. Проверяем баланс пользователя на STT
    4. Если денег НЕТ на STT → отправляем сообщение + клавиатура покупки → возвращаем None
    5. Если деньги ЕСТЬ на STT:
       - Проверяем баланс на TTS сразу (оптимизация!)
       - Устанавливаем context.can_afford_tts = True/False
       - Скачать voice file через Telegram API
       - STT → распознать текст
       - Списать деньги за STT
       - Заменить data["message"]["text"] = recognized_text
       - Установить context.is_voice_message = True
    
    Args:
        data: Telegram update data
        token: Bot token for API calls
        user: ChatUser object
        sender_chat_id: Telegram chat ID
        session: Database session
        context: Request context
    
    Returns:
        Модифицированный data с text вместо voice, или None если нет денег на STT
    """
    # Check if this is a voice message
    if "voice" not in data.get("message", {}):
        context.is_voice_message = False
        context.can_afford_tts = False
        return data
    
    # Mark as voice message
    context.is_voice_message = True
    
    # Import billing and API modules
    from src.db.lib.billing.common.enums import (
        CurrenciesTypes,
        PaidActions,
        SourceNames,
    )
    from src.db.lib.billing.common.exceptions import NotEnoughCurrencyError
    from src.telegram.api import send_tg_message, transcribe_telegram_audio
    from src.telegram.async_adapters import (
        async_check_user_have_enough_currency,
        async_get_paid_action_dataset,
        async_process_paid_action,
    )
    from src.telegram.keyboards import create_get_tokens_keyboard
    from src.telegram.lib.i18n import get_gettext_for_language
    
    lang_code = context.user_language or "en"
    _ = get_gettext_for_language(lang_code)
    
    # Получаем стоимость STT и TTS
    stt_action = await async_get_paid_action_dataset(PaidActions.SPEECH_TO_TEXT.value)
    tts_action = await async_get_paid_action_dataset(PaidActions.TEXT_TO_SPEECH.value)
    
    # Проверяем баланс на STT
    try:
        await async_check_user_have_enough_currency(
            user.id, stt_action.price, CurrenciesTypes.TOKEN.value
        )
    except NotEnoughCurrencyError:
        # НЕТ ДЕНЕГ на STT - сообщаем и показываем клавиатуру
        logger.info(f"User {user.id} has no tokens for STT")
        await send_tg_message(
            sender_chat_id,
            _("Sorry darling! 💋 You need tokens to use voice messages. "
              "Voice recognition costs {price} tokens.").format(price=stt_action.price),
            token,
            reply_markup=create_get_tokens_keyboard(lang_code)
        )
        return None  # Останавливаем обработку!
    
    # Деньги на STT есть - проверяем баланс на TTS сразу (оптимизация!)
    try:
        await async_check_user_have_enough_currency(
            user.id, tts_action.price, CurrenciesTypes.TOKEN.value
        )
        context.can_afford_tts = True
        logger.info(f"User {user.id} can afford both STT and TTS")
    except NotEnoughCurrencyError:
        context.can_afford_tts = False
        logger.info(f"User {user.id} can afford STT but not TTS - will respond with text")
    
    # Скачиваем и распознаем голос
    voice_file_id = data["message"]["voice"]["file_id"]
    recognized_text = await transcribe_telegram_audio(voice_file_id, token)
    
    # Списываем деньги за STT
    await async_process_paid_action(
        user.id, stt_action, SourceNames.TELEGRAM_VOICE_MESSAGE.value,
        {"voice_duration": data["message"]["voice"]["duration"]}
    )
    
    # Заменяем voice на text - теперь это обычное текстовое сообщение!
    data["message"]["text"] = recognized_text
    logger.info(
        f"Voice message transcribed for user {user.id}: {recognized_text[:50]}... "
        f"(can_afford_tts={context.can_afford_tts}, "
        f"user_language={context.user_language}, "
        f"has_translator={context.translator is not None})"
    )
    
    return data
