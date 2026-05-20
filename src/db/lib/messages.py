import os
import random
import uuid
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import List, Optional, Tuple

from dotenv import load_dotenv
from sqlalchemy import func, text
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, col, select, update

from .chat_models import Channel, ChatUser, Message, ReviewStatus
from .chat_models import MessageType as ChatMessageType
from .chat_types import MessageDTO, MessageType
from .config import config
from .content_models import (
    ContentCharacter,
    ContentContext,
    ImageInfo,
    ImagesUserSettings,
    LLMStats,
)
from .images import process_image_getting
from .llm.llm_methods import get_next_turn
from .llm_services.api import LLMServiceAPI
from .llm_services.schemes import (
    ContextImageResponse,
    ContextImageResponseStatus,
    GuardrailResponse,
    GuardrailResponseTypes,
)

# Constants
CHANNEL_CONTEXT_KEY_FORMAT = "channel_{}_context"

if os.environ.get("TEST_ENV") != "ci":
    from dotenv import load_dotenv

    load_dotenv()
logger = getLogger(__name__)


def send_message(
    session: Session,
    char_id,
    user_id,
    sender,
    text,
    llm_stats: Optional[LLMStats] = None,
    attachments=None,
    message_type: Optional[MessageType] = None,
    config_id: Optional[uuid.UUID] = None,
    stage_name: Optional[str] = None,
) -> Message:
    """
    Sends a message in a chat application. Commits!

    Args:
        session (Session): A SQLAlchemy session object used to interact with the database.
        char_id (int): The ID of the character sending the message.
        user_id (int): The ID of the user receiving the message.
        sender (str): The type of sender, either "user" or "character".
        text (str): The content of the message.
        llm_stats (LLMStats, optional): Statistics about the message, if the sender is a "character".
        attachments (List[Attachment], optional): A list of attachments to be included with the message.

    Returns:
        int: The ID of the newly created message.

    Raises:
        ValueError: If the `sender` parameter is not "user" or "character", or if `llm_stats` is not provided when the sender is a "character".
    """

    if sender != "user" and sender != "character":
        raise ValueError('sender must be "user" or "character"')

    if sender == "character" and llm_stats is None:
        raise ValueError("llm_stats must be provided for character sender")

    # find or create channel
    channel_id = find_or_create_channel_id(session, char_id, user_id, config_id)
    print(f"channel_id: {channel_id}")
    m_char_id = char_id if sender == "character" else None
    m_user_id = user_id if sender == "user" else None

    msg = Message(
        channel_id=channel_id,
        text=text,
        attachments=attachments,
        user_id=m_user_id,
        char_id=m_char_id,
        inserted_at=datetime.utcnow(),
        message_type=message_type,
        stage_name=stage_name,
    )
    session.add(msg)
    if sender == "character":
        if llm_stats is None:
            raise ValueError("llm_stats must be provided for character sender")
        session.flush()
        llm_stats.ref_type = "message"
        llm_stats.ref_id = msg.id  # type: ignore
        llm_stats.user_id = user_id
        session.add(llm_stats)
    session.commit()
    session.refresh(msg)

    return msg


def find_or_create_channel_id(
    session: Session, char_id: int, user_id, config_id: Optional[uuid.UUID] = None
) -> int:
    stmt = select(Channel).where(
        Channel.char_id == char_id, Channel.user_id == user_id, Channel.config_id == config_id
    )
    result = session.exec(stmt)
    channel = result.first()
    print(f"char_id: {char_id}, user_id: {user_id}, config_id: {config_id}, channel: {channel}")
    if channel is None:
        char: ContentCharacter = session.get(ContentCharacter, char_id)
        if char is None:
            print(f"No character with id {char_id}")
            return None
        suitable_contexts = list(
            filter(lambda x: x.context_type == "first_interaction", char.usable_contexts)
        )
        if len(suitable_contexts) == 0:
            print(f"No suitable contexts for character {char_id}")
            return None
        channel = Channel(
            char_id=char_id,
            user_id=user_id,
            current_char_context=random.choice(suitable_contexts).id,
        )
        session.add(channel)
        session.commit()
        session.refresh(channel)
    return channel.id


def get_messages(session: Session, char_id, user_id):
    channel_id = find_or_create_channel_id(session, char_id, user_id)
    stmt = (
        select(Message).where(Message.channel_id == channel_id).order_by(Message.inserted_at.asc())
    )
    result = session.exec(stmt)
    return result.all()


def archive_messages(
    session: Session,
    char_id: int,
    user_id: uuid.UUID,
    config_id: Optional[uuid.UUID] = None,
) -> Tuple[uuid.UUID, List[int]]:
    # TODO: acquire distributed lock
    # with lock(session, f"archive_messages_{char_id}_{user_id}", 10 sec):
    try:
        session.begin()

        channel_id = find_or_create_channel_id(session, char_id, user_id, config_id)
        session.execute(
            text("SELECT id FROM public.messages WHERE channel_id = :channel_id FOR UPDATE"),
            {"channel_id": channel_id},
        )

        archive_id = uuid.uuid4()
        archive_time = datetime.now()

        result = session.execute(
            text(
                """
            INSERT INTO content.message_archive (id, inserted_at, text, attachments, user_id, char_id, channel_id, archive_id, archive_time)
            SELECT id, inserted_at, text, attachments, user_id, char_id, channel_id, :archive_id, :archive_time
            FROM public.messages
            WHERE channel_id = :channel_id
            RETURNING id
            """
            ),
            {
                "channel_id": channel_id,
                "archive_id": archive_id,
                "archive_time": archive_time,
            },
        )

        ids = [x[0] for x in result.all()]
        session.execute(
            text(
                """
            UPDATE content.llm_stats
            SET ref_type = 'message_archive'
            WHERE ref_type = 'message' AND ref_id IN (
                SELECT id FROM public.messages WHERE channel_id = :channel_id
            )
            """
            ),
            {"channel_id": channel_id},
        )

        session.execute(
            text("DELETE FROM public.messages WHERE channel_id = :channel_id"),
            {"channel_id": channel_id},
        )

        session.commit()

        print(f"Number of archived rows: {len(ids)}")
        return archive_id, ids

    except Exception as e:
        session.rollback()
        print(f"Transaction failed: {e}")

    finally:
        # Закрытие сессии
        session.close()


@dataclass(frozen=True)
class MessageDataset:
    message_id: int
    message_text: str


def start_new_chat_and_send_first_message(
    session: Session, user_id, char_id, archive_existing=False
) -> MessageDataset | str:
    # check that both user and character exist
    user = session.get(ChatUser, user_id)
    if user is None:
        return "User not found"
    char = session.get(ContentCharacter, char_id)
    if char is None:
        return "Character not found"
    print(char)

    # find or create the channel
    chan_id = find_or_create_channel_id(session, char.id, user.id)

    # archive old messages if there are any in this channel
    if archive_existing:
        count_messages = session.exec(
            select(func.count()).where(Message.channel_id == chan_id)
        ).one()
        if count_messages > 0:
            session.commit()
            archive_id, message_ids = archive_messages(session, char_id, user_id)
            print("Archived: ", archive_id, len(message_ids))

    # setup the context
    chan = session.get(Channel, chan_id)
    char = session.get(ContentCharacter, char_id)
    suitable_contexts = list(
        filter(lambda x: x.context_type == "first_interaction", char.usable_contexts)
    )
    if len(suitable_contexts) == 0:
        err = f"Err: No suitable contexts for character {char_id}"
        print(err)
        return err

    current_char_context = random.choice(suitable_contexts)
    chan.current_char_context = current_char_context.id
    session.add(chan)
    session.commit()

    if current_char_context.first_image:
        # Send first image
        send_message(
            session,
            char_id,
            user_id,
            "character",
            "",
            LLMStats.dummy(),
            [{"type": "image", "id": current_char_context.first_image.hex}],
            message_type=ChatMessageType.GREETING_IMAGE,
        )
    # Send onboarding text message
    if char.onboarding_message:
        send_message(
            session,
            char_id,
            user_id,
            "character",
            char.onboarding_message,
            llm_stats=LLMStats.dummy(),
            message_type=ChatMessageType.ONBOARDING_TEXT,
        )
    # Send first text message
    message_id = send_message(
        session,
        char_id,
        user_id,
        "character",
        current_char_context.first_message,
        llm_stats=LLMStats.dummy(),
        message_type=ChatMessageType.GREETING_TEXT,
    ).id

    return MessageDataset(message_id=message_id, message_text=current_char_context.first_message)


def get_channel_image_context(
    session: Session, user_id: uuid.UUID, channel_id: int
) -> Optional[dict]:
    """Get the saved image context for a specific channel from user settings."""
    user_settings = session.get(ImagesUserSettings, user_id)
    if not user_settings:
        logger.debug(f"No user settings found for user {user_id}")
        return None

    base_key = CHANNEL_CONTEXT_KEY_FORMAT.format(channel_id)
    context = {}

    # Collect all values for this channel's context
    if user_settings.settings:
        for key, value in user_settings.settings.items():
            if key.startswith(f"{base_key}_"):
                context_key = key.replace(f"{base_key}_", "")
                context[context_key] = value

    logger.debug(f"Retrieved channel context: {context}")
    return context if context else None


def update_channel_image_context(
    session: Session, user_id: uuid.UUID, channel_id: int, context: dict
) -> None:
    """Update or create image context for a specific channel in user settings."""
    user_settings = session.get(ImagesUserSettings, user_id)
    if not user_settings:
        logger.debug(f"Creating new ImagesUserSettings for user {user_id}")
        user_settings = ImagesUserSettings(id=user_id, settings={})
        session.add(user_settings)

    if not user_settings.settings:
        user_settings.settings = {}

    # Store each context value as a separate key-value pair
    base_key = CHANNEL_CONTEXT_KEY_FORMAT.format(channel_id)
    for key, value in context.items():
        context_key = f"{base_key}_{key}"
        user_settings.settings[context_key] = str(value)

    flag_modified(user_settings, "settings")
    session.add(user_settings)
    try:
        session.commit()
    except Exception as e:
        logger.error(f"Failed to update channel context: {e}")
        session.rollback()


async def send_message_and_get_response(
    session: Session, user_id, char_id, message_text
) -> list[MessageDTO]:
    channel = session.exec(
        select(Channel).where(
            Channel.char_id == char_id,
            Channel.user_id == user_id,
        )
    ).first()
    if channel is None:
        raise Exception("Channel not found")

    char = session.get(ContentCharacter, char_id)
    user = session.get(ChatUser, user_id)
    context = session.get(ContentContext, channel.current_char_context)

    # Add user message to the messages table
    send_message(session, char_id, user_id, "user", message_text)

    # Get saved channel context from user settings
    saved_context = get_channel_image_context(session, user_id, channel.id)
    logger.debug(f"Using saved context for channel {channel.id}: {saved_context}")
    # Polling context image service for a possible contextual image
    params = {
        "user_id": str(user_id),
        "message_text": message_text,
        "char_id": char_id,
        "last_image_context": saved_context,
    }
    # Добавляем config_id: None -> "null", UUID -> str
    if channel.config_id is not None:
        params["config_id"] = str(channel.config_id)
    else:
        params["config_id"] = "null"
    logger.debug(f"Calling context image service with params: {params}")
    context_image_service = LLMServiceAPI(
        api_url=config.context_image_service_url.__str__(),
        api_key=config.llm_services_api_key.get_secret_value(),
    )
    context_image_service_response: Optional[ContextImageResponse] = (
        await context_image_service.post(params=params, validation_schema=ContextImageResponse)
    )
    logger.debug(f"Context image service response: {context_image_service_response}")

    # Initialize image context for system prompt
    image_context = ""
    image_message = None
    # Handle different image status responses
    if context_image_service_response:
        if context_image_service_response.status == ContextImageResponseStatus.FOUND:
            # Image found case
            image = session.get(ImageInfo, context_image_service_response.image_id)
            logger.debug(f"Found image with ID {context_image_service_response.image_id}: {image}")
            if image:
                # First send the image message
                image_message = await process_image_getting(session, user_id, char_id, image)
                logger.debug(f"Sent image message: {image_message}")

                # Update channel context in user settings if we have context
                if context_image_service_response.context:
                    ctx = context_image_service_response.context
                    if isinstance(ctx, dict):
                        logger.debug(f"Updating channel context with new context: {ctx}")
                        update_channel_image_context(session, user_id, channel.id, ctx)

                # Prepare context for the text response
                image_context = "\nSystem: The user asked to see a photo. You already found a matching photo and are showing it."
                if context_image_service_response.context:
                    ctx = context_image_service_response.context
                    if isinstance(ctx, dict):
                        subject = ctx.get("current_subject", "")
                        rating = ctx.get("rating", "")
                        if subject or rating:
                            image_context += f" It's a {rating} photo that shows {subject}. CRITICAL: NEVER describe photos in square brackets like [Photo of...] or [I'm sending a photo of...]. This is strictly forbidden. Just act naturally as if the photo is part of your natural expression. NEVER break the 4th wall! It's better to not mention the photo at all than mention it in an unnatural way."
                            logger.debug(f"Added image context to system prompt: {image_context}")

        elif context_image_service_response.status == ContextImageResponseStatus.NOT_FOUND:
            image_context = "\nSystem: The user asked to see a photo, but you don't have a matching one. Explain this naturally, maybe suggest why you don't have such a photo. NEVER break the 4th wall!"

    # Get messages for LLM context
    messages = session.exec(
        select(Message)
        .where(
            Message.channel_id == channel.id,
            col(Message.text).is_not(None),
            Message.text != "",
        )
        .order_by(col(Message.inserted_at).asc())
    ).all()

    if len(messages) > 1:
        messages = messages[:-1]

    system_prompt_override = None
    if char.system_prompt_override and char.use_system_prompt_override:
        system_prompt_override = char.system_prompt_override

    message_addendum_override = None
    if char.message_addendum_override and char.use_message_addendum_override:
        message_addendum_override = char.message_addendum_override

    
    # add image context to the user message itself
    if image_context:
        message_text = f"{message_text}\n{image_context}"


    # Get response from LLM
    res, stats = get_next_turn(
        char.name,
        user.display_name,
        char.personality,
        context.scenario,
        message_text,
        messages,
        system_prompt_override=system_prompt_override,
        message_addendum_override=message_addendum_override,
    )

    # # Check LLM response using guardrail service
    # params = {"message_text": res}
    # guardrail_service = LLMServiceAPI(
    #     api_url=config.guardrail_service_url.__str__(),
    #     api_key=config.llm_services_api_key.get_secret_value(),
    # )
    # guardrail_service_response: Optional[GuardrailResponse] = await guardrail_service.get(
    #     params=params, validation_schema=GuardrailResponse
    # )

    # # Handle guardrail response
    # if guardrail_service_response:
    #     if guardrail_service_response.response_type == GuardrailResponseTypes.REJECTED:
    #         # Trying to get valid response from LLM
    #         retries = config.guardrail_retries - 1
    #         while retries > 0:
    #             res, stats = get_next_turn(
    #                 char.name,
    #                 user.display_name,
    #                 char.personality,
    #                 context.scenario,
    #                 message_text,
    #                 messages,
    #                 system_prompt_override=system_prompt_override,
    #                 message_addendum_override=message_addendum_override,
    #             )
    #             params = {"message_text": res}
    #             guardrail_service_response: Optional[GuardrailResponse] = (
    #                 await guardrail_service.get(params=params, validation_schema=GuardrailResponse)
    #             )
    #             if (
    #                 guardrail_service_response
    #                 and guardrail_service_response.response_type != GuardrailResponseTypes.REJECTED
    #             ):
    #                 if guardrail_service_response.formatted_message:
    #                     res = guardrail_service_response.formatted_message
    #                 break
    #             logger.info(
    #                 f"Invalid LLM text response(Guardrail status: {guardrail_service_response.response_type.value}): {res} "
    #             )
    #             retries -= 1
    #             logger.info(f"Retrying, retries left {retries}")

    # Send the text response message
    message = send_message(session, char_id, user_id, "character", res, stats)
    if image_message:
        # Order isn't important here cause this is only for billing purposes
        return [image_message, MessageDTO(MessageType.TEXT, message)]
    else:
        return [MessageDTO(MessageType.TEXT, message)]


def add_review_to_message(
    session: Session,
    message_id: int,
    review_status: ReviewStatus,
    review_categories: list[str] | None = None,
    review_text: str | None = None,
) -> None:
    stmt = (
        update(Message)
        .where(Message.id == message_id)
        .values(
            review_status=review_status,
            review_categories=review_categories,
            review_text=review_text,
        )
    )

    session.exec(stmt)
    session.commit()


def group_messages_attachments(messages: list[Message]) -> list[Message]:
    """
    Groups consecutive messages with attachments but no text into single messages.
    Skips grouping for greeting images and the last message.
    Maximum size of grouped attachments is 9.

    Args:
        messages (list[Message]): List of messages to process

    Returns:
        list[Message]: List of messages with attachments grouped where appropriate
    """
    if not messages:
        return []

    result = []
    current_group = None
    base_message = None

    # Process all messages except the last one
    for message in messages[:-1]:
        # Skip grouping for greeting images
        if message.message_type == ChatMessageType.GREETING_IMAGE:
            if current_group:
                result.append(base_message)
                current_group = None
                base_message = None
            result.append(message)
            continue

        # Handle messages with attachments but no text
        if message.attachments and not message.text:
            if current_group is None:
                # Start new group
                current_group = []
                base_message = message
                current_group.extend(message.attachments)
            else:
                # Only add to group if it won't exceed max size
                if len(current_group) + len(message.attachments) <= 9:
                    # Add to existing group at the end to maintain order
                    current_group.extend(message.attachments)
                    base_message.attachments = current_group
                else:
                    # Current group is full, start a new one
                    result.append(base_message)
                    current_group = []
                    base_message = message
                    current_group.extend(message.attachments)
        else:
            # Message has text or no attachments - end current group if exists
            if current_group:
                base_message.attachments = current_group
                result.append(base_message)
                current_group = None
                base_message = None
            result.append(message)

    # Handle any remaining group before the last message
    if current_group:
        base_message.attachments = current_group
        result.append(base_message)

    # Always append the last message without grouping
    if messages:
        result.append(messages[-1])
    logger.info(f"Grouped messages: {result}")
    return result


def get_message_images(messages: list[Message]) -> list[uuid.UUID]:
    res = []

    for message in messages:
        if message.attachments:
            for attachment in message.attachments:
                if attachment["type"] == "image":
                    res.append(uuid.UUID(attachment["id"]))
    return res
