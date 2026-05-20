from src.telegram.context import RequestContext
from src.telegram.handlers.button_continue_preprocessor import (
    preprocess_button_continue,
)


async def process_continue_command(
    data: dict,
    context: RequestContext,
) -> None:
    """
    Process /continue command by replacing it with localized 'continue' text.
    
    This command handler replaces the command text with localized "continue"
    so that it can be processed as a regular message. Unlike the button,
    the command message is NOT deleted from the chat.
    
    Args:
        data: Telegram update data (modified in-place)
        context: Request context with user_language
    """
    # Replace command with localized text using preprocessor
    await preprocess_button_continue(data, context)

