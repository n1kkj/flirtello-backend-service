import sentry_sdk

from src.db.lib.auth import SupabaseAuth
from src.telegram.config import (
    MKT_COLLECTOR_API_KEY,
    MKT_COLLECTOR_URL,
    logger,
)
from src.telegram.lib.sender_utils import send_marketing_event


async def handle_my_chat_member(data: dict, auth_handler: SupabaseAuth):
    """Handles 'my_chat_member' updates, e.g., when a user blocks (kicks) the bot."""
    my_chat_member = data.get("my_chat_member")
    if not my_chat_member:
        return

    new_member_status = my_chat_member.get("new_chat_member", {}).get("status")
    if new_member_status == "kicked":
        chat_id = my_chat_member.get("chat", {}).get("id")
        if not chat_id:
            logger.warning("Received 'kicked' status in my_chat_member but no chat.id found.")
            return

        logger.info(f"Bot was kicked/blocked by user in chat {chat_id}. Logging this event.")

        # Find user by tg_id. They might not exist if they never started the bot.
        user = auth_handler.find_user_by_tg_id(chat_id)
        if user:
            if not MKT_COLLECTOR_URL or not MKT_COLLECTOR_API_KEY:
                logger.error("MKT Collector URL or API Key is not configured. Cannot send event.")
                return

            success, message = await send_marketing_event(
                mkt_collector_url=MKT_COLLECTOR_URL,
                mkt_collector_api_key=MKT_COLLECTOR_API_KEY,
                user_uuid=str(user.id),
                event_name="tg_kicked",
                params={"tg_id": chat_id},
                retries=3,
                retry_delay=1.0,
            )

            if success:
                logger.info(f"Successfully sent mkt event 'tg_kicked' for user {user.id}")
            else:
                error_message = (
                    f"Failed to send mkt event 'tg_kicked' for user {user.id}. Reason: {message}"
                )
                logger.error(error_message)
                sentry_sdk.capture_message(
                    f"MKT Collector 'tg_kicked' event sending failed: {message}", level="error"
                )
        else:
            logger.debug(
                f"User with TG ID {chat_id} not found for 'tg_kicked' event. Event not sent."
            ) 