import json

import sentry_sdk
from sqlmodel import Session

from src.db.lib.auth import SupabaseAuth
from src.telegram.api import send_tg_message
from src.telegram.config import client, engine, logger
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.use_cases.process_payment_callback import process_payment_callback


async def handle_pre_checkout_query(data: dict, token: str):
    """
    Handle pre_checkout_query from Telegram payments.

    Args:
        data (dict): The pre_checkout_query data from Telegram
        token (str): The bot token to use for API calls
    """
    pre_checkout = data["pre_checkout_query"]
    query_id = pre_checkout["id"]
    try:
        # Parse the invoice payload
        payload = json.loads(pre_checkout["invoice_payload"])
        invoice_id = payload.get("invoice_id")

        if not invoice_id:
            logger.error(f"Invalid invoice payload: {payload}")
            # Reject the payment if invoice_id is missing
            BASE_URL = f"https://api.telegram.org/bot{token}"
            reject_payload = {
                "pre_checkout_query_id": query_id,
                "ok": False,
                "error_message": "Invalid payment data",
            }
            await client.post(f"{BASE_URL}/answerPreCheckoutQuery", json=reject_payload)
            return

        # Here you can add additional validation if needed
        # For example, check if the invoice exists in your database
        # or verify the amount matches what you expect

        # Accept the payment
        BASE_URL = f"https://api.telegram.org/bot{token}"
        accept_payload = {"pre_checkout_query_id": query_id, "ok": True}
        await client.post(f"{BASE_URL}/answerPreCheckoutQuery", json=accept_payload)
        logger.info(f"Pre-checkout query {query_id} accepted for invoice {invoice_id}")
    except Exception as e:
        logger.error(f"Error processing pre_checkout_query: {e}", exc_info=True)
        sentry_sdk.capture_exception(e)
        # Reject the payment in case of any error
        BASE_URL = f"https://api.telegram.org/bot{token}"
        reject_payload = {
            "pre_checkout_query_id": query_id,
            "ok": False,
            "error_message": "Internal server error",
        }
        try:
            await client.post(f"{BASE_URL}/answerPreCheckoutQuery", json=reject_payload)
        except Exception as e2:
            logger.error(f"Failed to send reject response: {e2}", exc_info=True)


async def handle_successful_payment(
    data: dict, token: str, session: Session, auth_handler: SupabaseAuth, context=None
):
    """
    Handle successful_payment from Telegram payments.

    Args:
        data (dict): The successful_payment data from Telegram
        token (str): The bot token to use for API calls
        session (Session): Database session (unused, kept for compatibility)
        context: Request context for language settings
    """
    try:
        payment_data = data["message"]["successful_payment"]
        payload = json.loads(payment_data["invoice_payload"])
        invoice_id = payload.get("invoice_id")

        if not invoice_id:
            logger.error(f"Invalid invoice payload in successful_payment: {payload}")
            lang_code = context.user_language if context else "en"
            _ = get_gettext_for_language(lang_code)
            await send_tg_message(
                data["message"]["chat"]["id"],
                _("Oops, darling! 💋 Something's not quite right with your payment data. Let's try that again, shall we? 😘"),
                token,
            )
            return

        # Get user from the message
        sender_chat_id = data["message"]["chat"]["id"]
        user = auth_handler.find_user_by_tg_id(sender_chat_id)
        if not user:
            logger.error(f"User not found for successful payment. TG ID: {sender_chat_id}")
            lang_code = context.user_language if context else "en"
            _ = get_gettext_for_language(lang_code)
            await send_tg_message(
                sender_chat_id,
                _("Oh no, sweetie! 💔 I can't seem to find your profile. Have we met before? Let's start fresh with /start 😉"),
                token,
            )
            return

        # Create a synchronous session for billing operations that require sync session
        with Session(engine) as sync_session:
            lang_code = context.user_language if context else "en"
            result_message = await process_payment_callback(
                invoice_id=invoice_id,
                telegram_payment_status="success",
                user_id=user.id,
                session=sync_session,
                lang_code=lang_code,
            )

        # Send the result message to the user
        await send_tg_message(sender_chat_id, result_message, token)
    except Exception as e:
        logger.error(f"Error processing successful payment: {e}", exc_info=True)
        sentry_sdk.capture_exception(e)
        try:
            lang_code = context.user_language if context else "en"
            _ = get_gettext_for_language(lang_code)
            await send_tg_message(
                data["message"]["chat"]["id"],
                _("Oh honey! 🌹 Something's not working quite right with our payment processing. Don't worry though - let's try again later or you can always reach out to our support team. They're as friendly as I am! 😘"),
                token,
            )
        except Exception:
            pass 