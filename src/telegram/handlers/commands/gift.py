import sentry_sdk
from sqlmodel import Session

from src.db.lib.chat_models import ChatUser
from src.db.lib.gift_codes.common.exceptions import (
    GiftCodeAlreadyActivated,
    GiftCodeInactive,
    GiftCodeNotFound,
)
from src.telegram.api import send_tg_message
from src.telegram.config import logger
from src.telegram.context import RequestContext
from src.telegram.lib.i18n import get_gettext_for_language


async def process_gift_command(
    text: str,
    user: ChatUser,
    session: Session,
    sender_chat_id: int,
    token: str,
    context: RequestContext,
):
    """Processes the /gift command to activate a promotional code."""
    lang_code = context.user_language or "en"
    _ = get_gettext_for_language(lang_code)
    logger.info(f"Processing /gift command for user {user.id}")
    logger.info(f"[GIFT_LANG_DEBUG] User {user.id}: context.user_language='{context.user_language}', lang_code='{lang_code}'")
    command_parts = text.split(" ")
    if len(command_parts) < 2:
        await send_tg_message(
            sender_chat_id,
            _("Please provide a gift code. Usage: /gift YOUR_CODE"),
            token,
        )
        return

    gift_code = command_parts[1]

    try:
        # The sync wrapper handles activation, crediting, and committing.
        from src.telegram.async_adapters import async_gift_code_process
        activated_code_details = await async_gift_code_process(gift_code, user.id)

        if activated_code_details:
            # GiftCodeUserLink doesn't have token_amount field, so we send generic message
            success_message = _(
                "Congratulations! 💖 You've successfully activated the gift code "
                "and received tokens. Enjoy your chat! 💋"
            )
            await send_tg_message(sender_chat_id, success_message, token)
        else:
            # Fallback message if details can't be fetched for some reason
            await send_tg_message(sender_chat_id, _("Gift code activated successfully! ✨"), token)

    except GiftCodeNotFound:
        await send_tg_message(
            sender_chat_id, _("Sorry, darling, that gift code doesn't exist. 💔"), token
        )
    except GiftCodeAlreadyActivated:
        await send_tg_message(
            sender_chat_id, _("Oops! It looks like you've already used this gift code. 😉"), token
        )
    except GiftCodeInactive:
        await send_tg_message(sender_chat_id, _("This gift code is no longer active. 😔"), token)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while activating gift code {gift_code} for user {user.id}: {e}",
            exc_info=True,
        )
        sentry_sdk.capture_exception(e)
        await send_tg_message(
            sender_chat_id, _("An unexpected error occurred. Please try again later. 🙏"), token
        )
