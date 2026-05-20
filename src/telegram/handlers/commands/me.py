import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.db.lib.chat_models import Channel, ChatUser
from src.telegram.api import send_tg_message
from src.telegram.context import RequestContext
from src.telegram.utils.get_user_chat_setting import (
    get_current_char_id,
    get_current_config_id,
)


async def process_me_command(
    user: ChatUser,
    session: AsyncSession,
    sender_chat_id: int,
    token: str,
    context: RequestContext,
):
    """Handles the /me333 command to show user debug info."""
    active_char_id = await get_current_char_id(session, user.id)
    current_config_id_from_settings = await get_current_config_id(session, user.id)

    # Получаем текущий channel_id
    channel_id = None
    if active_char_id:
        # Строим условие для config_id с учетом NULL значений
        # В SQL NULL = NULL не равно TRUE, поэтому нужно явно проверять is_(None)
        config_condition = (
            (Channel.config_id == current_config_id_from_settings)
            if current_config_id_from_settings is not None
            else Channel.config_id.is_(None)
        )

        result = await session.execute(
            select(Channel).where(
                Channel.char_id == active_char_id,
                Channel.user_id == user.id,
                config_condition,
            )
        )
        channel = result.scalars().first()
        if channel:
            channel_id = channel.id

    user_dict = {
        "tg_id": str(sender_chat_id),
        "id": str(user.id),
        "active_char_id": str(active_char_id),
        "config_id": str(current_config_id_from_settings),
        "channel_id": str(channel_id) if channel_id else None,
        "sb_id": str(user.id),
    }
    await send_tg_message(
        sender_chat_id,
        f"```json\n{json.dumps(user_dict, indent=2)}\n```",
        token,
    )
