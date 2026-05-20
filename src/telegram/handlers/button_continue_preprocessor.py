"""
Button Continue preprocessor.

This module handles the replacement of "Continue" button text with localized "continue"
for processing as a regular message.
"""
from src.telegram.config import logger
from src.telegram.context import RequestContext
from src.telegram.lib.i18n import get_gettext_for_language


async def preprocess_button_continue(
    data: dict,
    context: RequestContext,
) -> dict:
    """
    ПРЕПРОЦЕССОР: Заменяет текст кнопки "Continue 💬" на локализованное "продолжай".
    
    Этот препроцессор вызывается из dispatcher после проверки, что текст сообщения
    совпадает с локализованным текстом кнопки "Continue 💬".
    
    Логика:
    1. Получает локализованное слово "продолжай" на языке пользователя
    2. Заменяет data["message"]["text"] на локализованное "продолжай"
    3. Возвращает модифицированный data
    
    Args:
        data: Telegram update data
        context: Request context with user_language
    
    Returns:
        Модифицированный data с замененным текстом
    """
    lang_code = context.user_language or "en"
    _ = get_gettext_for_language(lang_code)
    localized_continue = _("continue")
    
    # Заменяем текст на локализованное "продолжай"
    data["message"]["text"] = localized_continue
    
    logger.info(
        f"Replaced Continue button text with localized '{localized_continue}' "
        f"for user language '{lang_code}'"
    )
    
    return data

