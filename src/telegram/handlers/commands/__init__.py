"""
Command router for Telegram bot commands.

This module provides a centralized routing function for all bot commands,
making it easy to add, remove, or modify command handlers.
"""
from typing import Optional
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.lib.chat_models import ChatUser
from src.telegram.context import RequestContext
from src.telegram.lib.sender_utils import send_mkt_event_fire_and_forget

from .continue_cmd import process_continue_command
from .flashbalance import process_flashbalance_command
from .flashdelme import process_flashdelme_command
from .gift import process_gift_command
from .help import process_help_command
from .lang import process_lang_command
from .list import process_list_command
from .me import process_me_command
from .photo import process_photo_command
from .start import process_start_command
from .stats import process_stats_command
from .story import process_story_command


async def route_command(
    text: str,
    data: dict,
    bot_type_is_mono: bool,
    mono_char_id: Optional[int],
    token: str,
    sender_chat_id: int,
    session: AsyncSession,
    user: ChatUser,
    active_char_id: Optional[int],
    config_id: Optional[UUID],
    context: RequestContext,
    background_tasks: BackgroundTasks,
    lang_code: str,
    get_image_command_text: str,
    engine: Engine,
) -> bool:
    """
    Routes commands to their respective handlers.
    
    Args:
        text: The command text from the message
        data: Full message data from Telegram
        bot_type_is_mono: Whether this is a mono-character bot
        mono_char_id: Character ID for mono bot (None for general bot)
        token: Bot token to use for API calls
        sender_chat_id: Telegram chat ID
        session: Database session
        user: ChatUser object
        active_char_id: Currently active character ID
        config_id: Current configuration ID
        context: Request context
        background_tasks: FastAPI background tasks
        lang_code: User's language code
        get_image_command_text: Translated "Get Image" button text
        engine: SQLAlchemy engine
    
    Returns:
        True if command was handled, False otherwise
    """
    
    # /start command
    if text.startswith("/start"):
        await process_start_command(
            data=data,
            MONO_CHAR_ID=mono_char_id,
            token=token,
            config_id_from_settings=config_id,
            sender_chat_id=sender_chat_id,
            session=session,
            user=user,
            context=context,
        )
        return True
    
    # /gift command
    elif text.startswith("/gift"):
        await process_gift_command(
            text=text,
            user=user,
            session=session,
            sender_chat_id=sender_chat_id,
            token=token,
            context=context,
        )
        return True
    
    # /lang command
    elif text.startswith("/lang"):
        await process_lang_command(
            data=data,
            text=text,
            user=user,
            session=session,
            sender_chat_id=sender_chat_id,
            token=token,
            context=context,
        )
        return True
    
    # /list command (general bot only)
    elif text == "/list" and not bot_type_is_mono:
        await process_list_command(
            sender_chat_id=sender_chat_id,
            session=session,
            user=user,
            token=token,
            context=context,
        )
        return True
    
    # /help command (general bot only)
    elif text == "/help" and not bot_type_is_mono:
        await process_help_command(
            sender_chat_id=sender_chat_id,
            token=token,
            context=context,
        )
        return True
    
    # /stats command (general bot only)
    elif text == "/stats" and not bot_type_is_mono:
        await process_stats_command(
            sender_chat_id=sender_chat_id,
            token=token,
            engine=engine,
        )
        return True
    
    # /story or /stories command (general bot only)
    elif (text == "/story" or text == "/stories") and not bot_type_is_mono:
        await process_story_command(
            sender_chat_id=sender_chat_id,
            session=session,
            user=user,
            token=token,
            context=context,
        )
        return True
    
    # /photo command or "Get Image" button
    elif text == "/photo" or text == get_image_command_text:
        # Получаем message_id из входящего сообщения для возможного удаления
        user_message_id = data.get("message", {}).get("message_id") if data.get("message") else None
        await process_photo_command(
            sender_chat_id=sender_chat_id,
            session=session,
            user=user,
            active_char_id=active_char_id,
            config_id=config_id,
            token=token,
            context=context,
            background_tasks=background_tasks,
            lang_code=lang_code,
            user_message_id=user_message_id,
        )
        return True
    
    # /continue command
    elif text == "/continue":
        # Send analytics event
        await send_mkt_event_fire_and_forget(user.id, "tg_continue_command")

        await process_continue_command(data, context)
        return False  # Continue to regular message processing
    
    # /me333 command (debug)
    elif text == "/me333":
        await process_me_command(
            user=user,
            session=session,
            sender_chat_id=sender_chat_id,
            token=token,
            context=context,
        )
        return True
    
    # /flashbalance333 command (debug - set balance)
    elif text.startswith("/flashbalance333"):
        await process_flashbalance_command(
            sender_chat_id=sender_chat_id,
            session=session,
            user=user,
            token=token,
            lang_code=lang_code,
            command_text=text,
        )
        return True
    
    # /flashdelme333 command (data deletion)
    elif text == "/flashdelme333":
        await process_flashdelme_command(
            user=user,
            session=session,
            sender_chat_id=sender_chat_id,
            token=token,
            context=context,
        )
        return True
    
    # Unknown command or not a command
    return False


__all__ = [
    "route_command",
    "process_start_command",
    "process_gift_command",
    "process_lang_command",
    "process_list_command",
    "process_help_command",
    "process_stats_command",
    "process_story_command",
    "process_photo_command",
    "process_continue_command",
    "process_me_command",
    "process_flashbalance_command",
    "process_flashdelme_command",
]
