from src.telegram.context import RequestContext
from src.telegram.keyboards import send_response_with_keyboard
from src.telegram.lib.i18n import get_gettext_for_language


async def process_help_command(
    sender_chat_id: int,
    token: str,
    context: RequestContext,
):
    """Processes the /help command to show available commands."""
    lang_code = context.user_language or "en"
    _ = get_gettext_for_language(lang_code)
    
    # Define the list of commands for help messages
    GENERAL_BOT_COMMANDS = [
        "/start",
        "/list",
        "/help",
        "/stats",
        "/story",
        "/photo",
        "/gift",
        "/lang",
    ]
    commands_text = ", ".join(GENERAL_BOT_COMMANDS)
    
    help_text = _("Available commands:") + f" {commands_text}"
    await send_response_with_keyboard(sender_chat_id, help_text, token)
