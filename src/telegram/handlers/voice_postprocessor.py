"""
Voice message postprocessor for TTS (Text-to-Speech).

This module handles the conversion of text responses to voice messages
if the user sent a voice message and has sufficient balance.
"""
from src.db.lib.chat_models import ChatUser
from src.telegram.config import logger
from src.telegram.context import RequestContext


async def postprocess_text_to_voice(
    response_text: str,
    sender_chat_id: int,
    token: str,
    user: ChatUser,
    context: RequestContext,
) -> bool:
    """
    ПОСТПРОЦЕССОР: Озвучиваем ответ если была голосовашка и хватает денег.
    
    Этот постпроцессор выполняется после получения ответа от LLM.
    Баланс на TTS уже был проверен в препроцессоре и сохранен в context.can_afford_tts.
    
    Логика:
    1. Проверяем context.is_voice_message
    2. Если False → возвращаем False (обычное текстовое сообщение)
    3. Если True:
       - Проверяем context.can_afford_tts (уже проверено в препроцессоре!)
       - Если False → возвращаем False (ответ уже отправлен текстом, ничего страшного)
       - Если True:
         * TTS → синтезировать голос
         * Списать деньги за TTS
         * Отправить голосовое сообщение
         * Возвращаем True
    
    Args:
        response_text: Text response from the character
        sender_chat_id: Telegram chat ID
        token: Bot token for API calls
        user: ChatUser object
        context: Request context with is_voice_message and can_afford_tts flags
    
    Returns:
        True если отправили голосом, False если текстом
    """
    # Check if this was a voice message
    if not context.is_voice_message:
        return False  # Обычное текстовое сообщение
    
    # Check if user can afford TTS (already checked in preprocessor)
    if not context.can_afford_tts:
        # Не хватает на TTS - ничего страшного, текст уже отправлен
        logger.info(
            f"User {user.id} sent voice but cannot afford TTS - response sent as text"
        )
        return False
    
    # TODO: Реализовать когда будут TTS и биллинг
    #
    # from src.db.lib.billing.common.enums import PaidActions, SourceNames
    # from src.telegram.async_adapters import (
    #     async_get_paid_action_dataset,
    #     async_process_paid_action,
    # )
    # from src.telegram.api import send_telegram_voice
    # from src.telegram.services.speech.tts_service import synthesize
    #
    # # Получаем стоимость TTS (для биллинга)
    # tts_action = await async_get_paid_action_dataset(PaidActions.TEXT_TO_SPEECH)
    #
    # # Получаем ID голоса персонажа (из конфигурации)
    # # voice_id = get_character_voice_id(active_char_id)  # TODO: Implement
    # voice_id = "default_voice"  # Заглушка
    #
    # # Синтезируем голос
    # audio_data = await synthesize(
    #     response_text,
    #     voice_id,
    #     context.user_language or "en"
    # )
    #
    # # Списываем деньги за TTS
    # await async_process_paid_action(
    #     user.id, tts_action, SourceNames.TELEGRAM_VOICE_TTS,
    #     {"text_length": len(response_text)}
    # )
    #
    # # Отправляем голосовое сообщение
    # await send_telegram_voice(sender_chat_id, audio_data, token)
    # logger.info(f"TTS response sent to {sender_chat_id}")
    #
    # return True
    
    # Заглушка - пока TTS не реализован
    logger.info(
        f"Would send TTS response to {sender_chat_id} for user {user.id}: "
        f"{response_text[:50]}... (TTS not implemented)"
    )
    return False
