from sqlalchemy.ext.asyncio import AsyncSession

from src.db.lib.chat_models import ChatUser
from src.telegram.api import send_tg_chat_action_typing, send_tg_message
from src.telegram.config import WEB_APP_FULL_LIST_URL
from src.telegram.context import RequestContext
from src.telegram.keyboards import create_character_selection_keyboard
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.utils.get_user_chat_setting import get_user_language


async def process_list_command(
    sender_chat_id: int,
    session: AsyncSession,
    user: ChatUser,
    token: str,
    context: RequestContext,
):
    """Processes the /list command to show available characters."""
    lang_code = context.user_language or "en"
    _ = get_gettext_for_language(lang_code)
    
    await send_tg_chat_action_typing(sender_chat_id, token)
    message_text, character_keyboard_markup = await create_character_selection_keyboard(
        session,
        include_descriptions_in_message=True,
        web_app_url=WEB_APP_FULL_LIST_URL,
        language_code=await get_user_language(session, user.id) or "en",
        context=context,
    )
    has_character_buttons = False
    if character_keyboard_markup and character_keyboard_markup.get("inline_keyboard"):
        for row in character_keyboard_markup["inline_keyboard"]:
            if any(
                button.get("callback_data", "").startswith("/start ") for button in row
            ):  # Проверяем, что это кнопка выбора персонажа
                has_character_buttons = True
                break
    if not has_character_buttons:
        text_for_no_chars = _(
            "No characters available for quick selection yet. Please check the full list!"
        )
        only_webapp_keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": _("✨ Open all characters"),
                        "web_app": {"url": f"{WEB_APP_FULL_LIST_URL}?lang={lang_code}"},
                    }
                ]
            ]
        }
        await send_tg_message(
            sender_chat_id,
            text_for_no_chars,
            token,
            reply_markup=only_webapp_keyboard,
        )
        return
    else:
        await send_tg_message(
            sender_chat_id,
            message_text,
            token,
            reply_markup=character_keyboard_markup,
        )
