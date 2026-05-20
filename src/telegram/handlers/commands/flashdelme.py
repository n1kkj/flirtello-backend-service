import asyncio

from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.lib.chat_models import ChatUser
from src.scripts.user_deletion import delete_user_data
from src.telegram.api import send_tg_message
from src.telegram.config import engine
from src.telegram.context import RequestContext


async def process_flashdelme_command(
    user: ChatUser,
    session: AsyncSession,
    sender_chat_id: int,
    token: str,
    context: RequestContext,
):
    """Handles the /flashdelme333 command to delete user data."""

    await send_tg_message(
        sender_chat_id,
        "Data deletion process has been initiated. This may take a moment. You will be notified upon completion.",
        token,
    )

    sync_engine = engine

    await asyncio.to_thread(
        delete_user_data,
        engine=sync_engine,
        auth_client=context.auth_client,
        user_id=user.id,
        dry_run=False,
    )

    await send_tg_message(
        sender_chat_id,
        "Your data has been successfully deleted from our systems.",
        token,
    )
