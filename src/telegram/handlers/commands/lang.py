from typing import Optional
from uuid import UUID

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.lib.chat_models import ChatUser
from src.telegram.api import send_tg_message, set_chat_menu_button
from src.telegram.config import WEB_APP_FULL_LIST_URL, logger
from src.telegram.context import RequestContext
from src.telegram.keyboards import create_context_keyboard
from src.telegram.lib.i18n import get_gettext_for_language


async def set_user_language_override_async_wrapper(session: AsyncSession, user_id: UUID, lang_code: str):
    """Async wrapper for setting user language."""
    from src.telegram.utils.get_user_chat_setting import set_user_language_override
    
    await set_user_language_override(session, user_id, lang_code)


async def get_user_language_override_async_wrapper(session: AsyncSession, user_id: UUID) -> Optional[str]:
    """Async wrapper for getting user language override."""
    from src.telegram.utils.get_user_chat_setting import (
        get_user_language,
        is_language_overridden_by_user,
    )
    
    # Check if user has language override flag set
    has_override = await is_language_overridden_by_user(session, user_id)
    if has_override:
        return await get_user_language(session, user_id)
    return None


async def process_lang_command(
    data: dict,
    text: str,
    user: ChatUser,
    session: AsyncSession,
    sender_chat_id: int,
    token: str,
    context: RequestContext,
):
    """Processes the /lang command to set the user's language preference."""
    # Use the async version directly instead of sync_to_async wrapper
    _ = get_gettext_for_language(context.user_language or "en")  # For initial error messages
    logger.info(f"Processing /lang command for user {user.id}")
    command_parts = text.split(" ")

    supported_langs = ["ru", "en", "auto"]

    # Get current language setting
    current_lang_override = await get_user_language_override_async_wrapper(session, user.id)
    if current_lang_override:
        current_lang_display = current_lang_override
    else:
        current_lang_display = _("auto (detected: {detected_lang})").format(detected_lang=context.user_language or "en")

    if len(command_parts) < 2:
        # Show current language + usage
        usage_message = _(
            "Current language: {current_lang}\n\n"
            "Usage: /lang [lang]\n"
            "Supported languages: ru, en\n"
            "Use 'auto' to reset to automatic detection."
        ).format(current_lang=current_lang_display)
        await send_tg_message(sender_chat_id, usage_message, token)
        return

    if command_parts[1].lower() not in supported_langs:
        # Show current language + usage for invalid language
        usage_message = _(
            "Current language: {current_lang}\n\n"
            "Invalid language '{invalid_lang}'\n"
            "Usage: /lang [lang]\n"
            "Supported languages: ru, en\n"
            "Use 'auto' to reset to automatic detection."
        ).format(current_lang=current_lang_display, invalid_lang=command_parts[1])
        await send_tg_message(sender_chat_id, usage_message, token)
        return

    lang_code = command_parts[1].lower()

    try:
        await set_user_language_override_async_wrapper(session, user.id, lang_code)

        # Determine the language to use for UI updates
        lang_for_ui = lang_code
        if lang_code == "auto":
            # For 'auto', we need the user's client language, not the one from context (which is the old override)
            client_lang = "en"  # Default fallback
            if "message" in data and "from" in data["message"] and "language_code" in data["message"]["from"]:
                client_lang = data["message"]["from"]["language_code"]
            lang_for_ui = client_lang

        # Get the translator for the UI language
        _ = get_gettext_for_language(lang_for_ui)

        # 1. Update the menu button (WebApp)
        try:
            if WEB_APP_FULL_LIST_URL:
                lang_param = f"?lang={lang_for_ui}" if lang_for_ui else ""
                final_web_app_url = f"{WEB_APP_FULL_LIST_URL}{lang_param}"
                await set_chat_menu_button(
                    token,
                    text=_("✨ Open all characters"),
                    web_app_url=final_web_app_url,
                    chat_id=sender_chat_id,
                )
        except Exception as e:
            logger.warning(f"Failed to set localized chat menu button for user {user.id}: {e}")

        # 2. Prepare confirmation message and keyboard in the new language
        if lang_code == "auto":
            success_message = _("Language has been reset to automatic detection. 🌐")
        else:
            # The success message should be in the new language
            _new_lang = get_gettext_for_language(lang_code)
            success_message = _new_lang("Language successfully set to {lang_code}. 💬").format(lang_code=lang_code)

        # The reply keyboard should also be in the new/correct language
        reply_markup = create_context_keyboard(lang_for_ui)

        await send_tg_message(sender_chat_id, success_message, token, reply_markup=reply_markup)

    except Exception as e:
        logger.error(
            f"An unexpected error occurred while setting language for user {user.id}: {e}",
            exc_info=True,
        )
        sentry_sdk.capture_exception(e)
        await send_tg_message(
            sender_chat_id, _("An unexpected error occurred. Please try again later. 🙏"), token
        )
