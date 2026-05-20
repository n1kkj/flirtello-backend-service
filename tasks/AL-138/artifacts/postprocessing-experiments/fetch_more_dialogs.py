#!/usr/bin/env python3
"""
Fetch more test dialogs from PostgreSQL database.
Gets last 10 messages from different channels for character_id 24.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlmodel import Session

# Load environment variables
load_dotenv("src/.env")
load_dotenv(".env")

# Database connection
DATABASE_URL = os.environ.get("DB_URL")
dbschema = "content,public"

engine = create_engine(
    DATABASE_URL, connect_args={"options": "-csearch_path={}".format(dbschema)}
)

CHARACTER_ID = 24
DIALOG_LENGTH = 10  # Last 10 messages
NUM_DIALOGS = 30  # How many dialogs to fetch


def format_dialog(messages):
    """Format messages as dialogue"""
    dialog_lines = []
    for msg in messages:
        role = "character" if msg["user_id"] is None else "user"
        text = msg["text"] or ""
        if text.strip():
            dialog_lines.append(f"{role}: {text}")
    return "\n".join(dialog_lines)


def get_dialog_position(channel_id, total_messages):
    """Determine if dialog is from start, middle, or end of conversation"""
    if total_messages <= DIALOG_LENGTH:
        return "start"
    # Get message position in conversation
    with Session(engine) as session:
        result = session.execute(
            text("""
                SELECT COUNT(*) as pos
                FROM public.messages
                WHERE channel_id = :channel_id
                  AND inserted_at <= (
                      SELECT inserted_at
                      FROM public.messages
                      WHERE channel_id = :channel_id
                        AND user_id IS NULL
                      ORDER BY inserted_at DESC
                      LIMIT 1
                  )
            """),
            {"channel_id": channel_id},
        )
        pos = result.fetchone()[0]

    if pos <= DIALOG_LENGTH:
        return "start"
    elif pos >= total_messages - DIALOG_LENGTH:
        return "end"
    else:
        return "middle"


def main():
    base_dir = Path(__file__).parent
    output_dir = base_dir / "test_dialogs"
    output_dir.mkdir(exist_ok=True)

    # Find existing dialog numbers
    existing_files = list(output_dir.glob("dialog_*.md"))
    existing_numbers = []
    for f in existing_files:
        try:
            num = int(f.stem.split("_")[1])
            existing_numbers.append(num)
        except (ValueError, IndexError):
            pass

    next_number = max(existing_numbers) + 1 if existing_numbers else 13

    print(f"Fetching {NUM_DIALOGS} dialogs for character_id {CHARACTER_ID}...")
    print(f"Starting from dialog_{next_number:03d}\n")

    with Session(engine) as session:
        # Get channels with char_id 24, ordered by message count
        # First, get channel IDs with enough messages
        channel_query = text("""
            SELECT 
                c.id as channel_id,
                COUNT(m.id) as message_count
            FROM public.channels c
            JOIN public.messages m ON m.channel_id = c.id
            WHERE c.char_id = :char_id
              AND m.text IS NOT NULL
              AND m.text != ''
            GROUP BY c.id
            HAVING COUNT(m.id) >= :dialog_length
            ORDER BY COUNT(m.id) DESC
            LIMIT :limit
        """)

        channel_result = session.execute(
            channel_query,
            {
                "char_id": CHARACTER_ID,
                "dialog_length": DIALOG_LENGTH,
                "limit": NUM_DIALOGS * 2,
            },
        )

        channels_data = [(row[0], row[1]) for row in channel_result]

        dialogs_fetched = 0
        seen_content = set()

        # For each channel, get last N messages
        for channel_id, message_count in channels_data:
            if dialogs_fetched >= NUM_DIALOGS:
                break

            # Get last N messages for this channel
            messages_query = text("""
                SELECT 
                    text,
                    user_id,
                    inserted_at
                FROM public.messages
                WHERE channel_id = :channel_id
                  AND text IS NOT NULL
                  AND text != ''
                ORDER BY inserted_at DESC
                LIMIT :dialog_length
            """)

            messages_result = session.execute(
                messages_query,
                {
                    "channel_id": channel_id,
                    "dialog_length": DIALOG_LENGTH,
                },
            )

            messages_list = [
                {
                    "text": row[0],
                    "user_id": row[1],
                    "inserted_at": row[2],
                }
                for row in messages_result
            ]

            if not messages_list:
                continue

            # Reverse to get chronological order (oldest to newest)
            messages = list(reversed(messages_list))

            # Format dialog
            dialog_text = format_dialog(messages)

            # Skip if we've seen similar content
            dialog_hash = hash(dialog_text[:200])  # Hash first 200 chars
            if dialog_hash in seen_content:
                continue
            seen_content.add(dialog_hash)

            # Determine position
            position = get_dialog_position(channel_id, message_count)

            # Save to file
            filename = output_dir / f"dialog_{next_number:03d}_{position}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(dialog_text)

            print(
                f"Saved: {filename.name} (channel_id={channel_id}, {message_count} total messages)"
            )
            dialogs_fetched += 1
            next_number += 1

    print(f"\n✅ Fetched {dialogs_fetched} dialogs")
    print(f"Files saved to: {output_dir}")


if __name__ == "__main__":
    main()
