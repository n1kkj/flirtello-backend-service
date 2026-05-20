import asyncio
import logging
import random
from typing import TYPE_CHECKING, Optional
from uuid import UUID

import sentry_sdk
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from src.telegram.context import RequestContext
    from src.telegram.handlers.media import IllustrationLockManager

from src.db.lib.content_models import DirectusFile, ImageInfo
from src.telegram.api import (
    delete_message,
    edit_message_media,
    send_tg_message,
)
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.lib.insufficient_balance import send_no_tokens_message_with_keyboards
from src.telegram.use_cases.get_illustration import get_illustration

logger = logging.getLogger(__name__)


async def generate_and_update_illustration(
    context: "RequestContext",  # type: ignore
    session: AsyncSession,
    user_id: UUID,
    char_id: int,
    sender_chat_id: int,
    message_id_to_edit: int,
    token: str,
    lock_manager: "IllustrationLockManager",  # type: ignore
    config_id: Optional[UUID] = None,
):
    """
    This is a background task that generates an illustration and then edits
    an existing message to include it.
    """
    logger.info(
        f"🎨 [ILLUSTRATION TASK] STARTED: user_id={user_id}, char_id={char_id}, message_id={message_id_to_edit}"
    )
    from src.telegram.context import RequestContext
    from src.telegram.dependecies import get_async_session

    final_image_info: Optional[ImageInfo] = None
    final_caption: Optional[str] = None
    error_message: Optional[str] = None
    insufficient_balance: bool = False

    try:
        # Re-create a session and context for the background task
        async for session in get_async_session():
            # Create a new context for this background task to ensure isolated timings and logging
            task_context = RequestContext.build(
                translator=context.translator, user_language=context.user_language
            )

            # 1. Call the original get_illustration logic
            illustration_result = await get_illustration(
                char_id, user_id, session, task_context, config_id
            )

            # 2. Process the result
            if illustration_result.error:
                # Map error to a user-friendly message
                error_message = (
                    illustration_result.messages[0].message
                    if illustration_result.messages
                    else "An unexpected error occurred. Please try again. ❤️"
                )
                logger.error(
                    f"[Task] Illustration generation failed for user {user_id}: {illustration_result.error.__name__}"
                )

            elif (
                illustration_result.messages
                and illustration_result.messages[0].attachments
            ):
                # Success case
                attachment = illustration_result.messages[0].attachments[0]
                image_info_id = attachment.id
                final_image_info = await session.get(ImageInfo, image_info_id)
                final_caption = illustration_result.messages[0].message
                if not final_image_info:
                    raise Exception(
                        f"ImageInfo {image_info_id} not found after generation."
                    )

            else:
                # Fallback case (no image, just text)
                # Проверяем, является ли это сообщением о недостатке баланса
                if illustration_result.messages:
                    first_message = illustration_result.messages[0]
                    # Проверяем атрибут insufficient_balance напрямую (Pydantic модель)
                    insufficient_balance = (
                        first_message.insufficient_balance
                        if hasattr(first_message, "insufficient_balance")
                        else False
                    )
                    error_message = first_message.message
                    logger.info(
                        f"[Task] Processing fallback message for user {user_id}. "
                        f"insufficient_balance={insufficient_balance}, message={error_message[:50]}..."
                    )
                else:
                    error_message = "I couldn't create an image right now, but I'm thinking of you. 💋"
                    insufficient_balance = False

                if insufficient_balance:
                    logger.info(
                        f"[Task] Insufficient balance detected for user {user_id}. Message: {error_message}"
                    )
                else:
                    logger.warning(
                        f"[Task] Illustration fallback for user {user_id}. Message: {error_message}"
                    )

    except SQLTimeoutError as e:
        # Специальная обработка ошибок пула соединений
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("error_type", "database_pool_timeout")
            scope.set_context(
                "pool_info",
                {
                    "error": str(e),
                    "user_id": str(user_id),
                    "char_id": char_id,
                    "message_id": message_id_to_edit,
                },
            )
            scope.level = "error"
            sentry_sdk.capture_exception(e)
        logger.error(
            f"⚠️ [TASK] DATABASE POOL TIMEOUT in generate_and_update_illustration for user {user_id}: {e}",
            exc_info=True,
        )
        error_message = "Something went really wrong. 😥 Let's try again in a moment."
    except Exception as e:
        logger.error(
            f"[Task] Unexpected exception in generate_and_update_illustration for user {user_id}: {e}",
            exc_info=True,
        )
        sentry_sdk.capture_exception(e)
        error_message = "Something went really wrong. 😥 Let's try again in a moment."
    finally:
        # 4. Always release the lock
        lock_manager.release(user_id)
        logger.info(f"[Task] Lock released for user {user_id}.")

    # 3. Edit the original message
    if final_image_info:
        # Introduce a small, random delay to make it feel more natural
        await asyncio.sleep(random.uniform(0.5, 2.0))

        # Manually fetch the DirectusFile using the foreign key
        image_file_id = final_image_info.image
        image_file = await session.get(DirectusFile, image_file_id)

        if not image_file or not image_file.filename_disk:
            logger.error(
                f"[Task] DirectusFile not found for ImageInfo {final_image_info.id} or filename_disk is missing."
            )
            # Set a more specific error message if the file itself is missing
            error_message = "I created a masterpiece, but it got lost on the way to you. 😥 Please try again!"
        else:
            # Assuming STORAGE_ROOT is configured and accessible
            from src.telegram.config import STORAGE_ROOT

            image_full_url = f"{STORAGE_ROOT}/{image_file.filename_disk}"

            logger.info(
                f"[Task] Success for user {user_id}. Editing message {message_id_to_edit} with image URL: {image_full_url}"
            )
            await edit_message_media(
                chat_id=sender_chat_id,
                message_id=message_id_to_edit,
                token=token,
                image_url=image_full_url,
                caption=final_caption,
            )
            # Early return on success
            return

    if error_message:
        logger.info(
            f"[Task] Failure for user {user_id}. Deleting loader message {message_id_to_edit} and sending error: {error_message}"
        )

        # Get user language for translation
        lang_code = context.user_language or "en"
        _ = get_gettext_for_language(lang_code)

        # Delete the loader message
        await delete_message(
            chat_id=sender_chat_id,
            message_id=message_id_to_edit,
            token=token,
        )

        # Send new translated error message
        translated_error = (
            _(error_message)
            if error_message
            else _(
                "Mmm... 🙈 I was just taking the perfect selfie for you, but my camera got too hot from all this passion! 🔥 Give me another try in a moment, baby... 💋 I promise to make it extra special for you! ✨💖"
            )
        )

        # Если это сообщение о недостатке баланса, добавляем клавиатуру
        if insufficient_balance:
            logger.info(
                f"🔑 [TASK] Insufficient balance detected, adding keyboard for user {user_id}"
            )
            await send_no_tokens_message_with_keyboards(
                sender_chat_id=sender_chat_id,
                message_text=translated_error,
                token=token,
                lang_code=lang_code,
                context=context,
                source="illustration_generation",
            )
            logger.info(
                f"✅ [TASK] NO_TOKENS message sent with keyboard to user {user_id}"
            )
        else:
            logger.info(
                f"⚠️ [TASK] Sending error message without keyboard for user {user_id}"
            )
            await send_tg_message(sender_chat_id, translated_error, token)

    else:
        # This case should ideally not be reached
        logger.error(
            f"[Task] Final state reached with no image and no error message for user {user_id}."
        )

        # Get user language for translation
        lang_code = context.user_language or "en"
        _ = get_gettext_for_language(lang_code)

        # Delete the loader message
        await delete_message(
            chat_id=sender_chat_id,
            message_id=message_id_to_edit,
            token=token,
        )

        # Send new translated fallback message
        await send_tg_message(
            sender_chat_id, _("Something went wrong, and I'm speechless. 💔"), token
        )

    logger.info(
        f"🎨 [ILLUSTRATION TASK] COMPLETED: user_id={user_id}, char_id={char_id}, message_id={message_id_to_edit}, success={'Yes' if final_image_info else 'No'}"
    )
