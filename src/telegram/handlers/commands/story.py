from sqlalchemy.ext.asyncio import AsyncSession

from src.db.lib.chat_models import ChatUser
from src.telegram.api import send_tg_chat_action_typing, send_tg_message
from src.telegram.config import WEB_APP_FULL_LIST_URL
from src.telegram.context import RequestContext
from src.telegram.keyboards import create_all_configs_selection_keyboard
from src.telegram.utils.get_user_chat_setting import get_user_language


async def process_story_command(
    sender_chat_id: int,
    session: AsyncSession,
    user: ChatUser,
    token: str,
    context: RequestContext,
):
    """Processes the /story or /stories command to show available story configurations."""
    await send_tg_chat_action_typing(sender_chat_id, token)
    message_text, configs_keyboard_markup = await create_all_configs_selection_keyboard(
        session,
        web_app_url=WEB_APP_FULL_LIST_URL,
        language_code=await get_user_language(session, user.id) or "en",
        context=context,
    )
    await send_tg_message(
        sender_chat_id, message_text, token, reply_markup=configs_keyboard_markup
    )
