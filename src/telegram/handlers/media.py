import os
import random
import threading
from typing import Optional
from uuid import UUID

import sentry_sdk
from fastapi import BackgroundTasks
from sqlmodel import Session

from src.db.lib.billing.common.exceptions import NotEnoughCurrencyError
from src.telegram.api import (
    send_animation_placeholder,
    send_tg_chat_action_typing,
    send_tg_message,
    send_video_placeholder,
)
from src.telegram.config import logger
from src.telegram.context import RequestContext
from src.telegram.DTO.chat import Attachment, SendChatMessageOutputSubDTO
from src.telegram.keyboards import create_get_tokens_keyboard
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.use_cases.generate_illustration_task import (
    generate_and_update_illustration,
)
from src.telegram.use_cases.get_illustration import get_illustration


# --- START: In-memory lock for illustration generation ---
class IllustrationLockManager:
    def __init__(self):
        self._locks = set()
        self._lock = threading.Lock()

    def acquire(self, user_id: UUID) -> bool:
        with self._lock:
            if user_id in self._locks:
                return False
            self._locks.add(user_id)
            return True

    def release(self, user_id: UUID):
        with self._lock:
            if user_id in self._locks:
                self._locks.remove(user_id)


lock_manager = IllustrationLockManager()
# --- END: In-memory lock ---


async def handle_photo_request(
    session: Session,
    user_id: UUID,
    char_id: int,
    sender_chat_id: int,
    token: str,
    context: RequestContext,
    background_tasks: BackgroundTasks,
    config_id: Optional[UUID] = None,
) -> None:
    lang_code = context.user_language or "en"
    _ = get_gettext_for_language(lang_code)

    # --- Acquire Lock ---
    if not lock_manager.acquire(user_id):
        logger.info(
            f"Illustration request for user {user_id} rejected due to active lock."
        )
        await send_tg_message(
            sender_chat_id,
            _(
                "I'm already drawing a masterpiece for you! 🎨 Please wait a moment before asking for another one."
            ),
            token,
        )
        return
    # --- Lock Acquired ---

    try:
        # 1. Send placeholder animation or video
        placeholder_dir = "src/telegram/images"
        placeholders = [
            f for f in os.listdir(placeholder_dir) if f.endswith((".gif", ".mp4"))
        ]
        if not placeholders:
            logger.error(
                "No .gif or .mp4 placeholder files found in src/telegram/images."
            )
            # Fallback to simple text message if no video is available
            placeholder_response = await send_tg_message(
                sender_chat_id, _("Getting ready..."), token
            )
            placeholder_message_data = await placeholder_response.json()
        else:
            chosen_placeholder_name = random.choice(placeholders)
            chosen_placeholder_path = os.path.join(
                placeholder_dir, chosen_placeholder_name
            )

            if chosen_placeholder_name.endswith(".gif"):
                placeholder_message_data = await send_animation_placeholder(
                    chat_id=sender_chat_id,
                    token=token,
                    animation_path=chosen_placeholder_path,
                    caption=_("Your illustration is being generated... 👨‍🎨"),
                )
            else:  # .mp4
                placeholder_message_data = await send_video_placeholder(
                    chat_id=sender_chat_id,
                    token=token,
                    video_path=chosen_placeholder_path,
                    caption=_("Your illustration is being generated... 👨‍🎨"),
                )

        if not placeholder_message_data or "result" not in placeholder_message_data:
            logger.warning(
                f"Failed to send placeholder animation/video to user {user_id} in chat {sender_chat_id}. Trying text fallback..."
            )
            # Fallback to text message if animation/video failed (e.g., due to rate limiting)
            try:
                placeholder_response = await send_tg_message(
                    sender_chat_id,
                    _("Your illustration is being generated... 👨‍🎨"),
                    token,
                )
                placeholder_message_data = await placeholder_response.json()

                if (
                    not placeholder_message_data
                    or "result" not in placeholder_message_data
                ):
                    logger.error(
                        f"Failed to send text placeholder message to user {user_id} in chat {sender_chat_id}."
                    )
                    await send_tg_message(
                        sender_chat_id,
                        _(
                            "Something went wrong while preparing your request. Please try again. ❤️"
                        ),
                        token,
                    )
                    # Release lock on failure to send placeholder
                    lock_manager.release(user_id)
                    return
            except Exception as fallback_error:
                logger.error(
                    f"Failed to send text placeholder fallback to user {user_id} in chat {sender_chat_id}: {fallback_error}",
                    exc_info=True,
                )
                await send_tg_message(
                    sender_chat_id,
                    _(
                        "Something went wrong while preparing your request. Please try again. ❤️"
                    ),
                    token,
                )
                # Release lock on failure to send placeholder
                lock_manager.release(user_id)
                return

        message_id_to_edit = placeholder_message_data["result"]["message_id"]

        # 2. Schedule the background task
        background_tasks.add_task(
            generate_and_update_illustration,
            context=context,
            session=session,
            user_id=user_id,
            char_id=char_id,
            sender_chat_id=sender_chat_id,
            message_id_to_edit=message_id_to_edit,
            token=token,
            config_id=config_id,
            lock_manager=lock_manager,  # Pass the lock manager to the task
        )

        logger.info(
            f"Scheduled illustration generation task for user {user_id} and message {message_id_to_edit}."
        )

    except Exception as e:
        logger.error(
            f"Error in handle_photo_request for user {user_id}: {e}", exc_info=True
        )
        lock_manager.release(user_id)  # Ensure lock is released on unexpected error
        # Optionally, notify the user
        await send_tg_message(
            sender_chat_id, _("An unexpected error occurred. Please try again."), token
        )

    return None
