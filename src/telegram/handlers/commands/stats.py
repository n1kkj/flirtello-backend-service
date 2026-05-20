from sqlalchemy import Engine

from src.telegram.keyboards import send_response_with_keyboard
from src.telegram.lib.commands.stats import command as stats_command


async def process_stats_command(
    sender_chat_id: int,
    token: str,
    engine: Engine,
):
    """Processes the /stats command to show bot statistics."""
    stats_text = await stats_command(engine)
    await send_response_with_keyboard(sender_chat_id, stats_text, token)
