#!/usr/bin/env python3
"""
Fetch dialogs from PostgreSQL database for error detection experiments.
Gets channels with at least 2 user messages and saves full dialogues.
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
if not DATABASE_URL:
    print("Error: DB_URL environment variable not set")
    print("Please set DB_URL in your .env file or environment")
    sys.exit(1)

dbschema = "content,public"

engine = create_engine(
    DATABASE_URL, connect_args={"options": "-csearch_path={}".format(dbschema)}
)

NUM_CHANNELS = 10  # How many channels to fetch
MIN_USER_MESSAGES = 2  # Minimum user messages in channel


def format_dialog(messages):
    """Format messages as dialogue"""
    dialog_lines = []
    for msg in messages:
        role = "character" if msg["user_id"] is None else "user"
        text = msg["text"] or ""
        if text.strip():
            dialog_lines.append(f"{role}: {text}")
        elif msg.get("message_type") and msg["message_type"] not in ["DEFAULT_IMAGE", "GREETING_IMAGE"]:
            # Include message type for empty messages if it's meaningful
            dialog_lines.append(f"{role}: [{msg['message_type']}]")
    return "\n".join(dialog_lines)


def main():
    base_dir = Path(__file__).parent
    output_dir = base_dir / "test_dialogs"
    output_dir.mkdir(exist_ok=True)
    
    # Find existing channel numbers
    existing_files = list(output_dir.glob("channel_*.md"))
    existing_numbers = []
    for f in existing_files:
        try:
            num = int(f.stem.split("_")[1])
            existing_numbers.append(num)
        except (ValueError, IndexError):
            pass
    
    next_number = max(existing_numbers) + 1 if existing_numbers else 57049
    
    print(f"Fetching {NUM_CHANNELS} channels with at least {MIN_USER_MESSAGES} user messages...")
    print(f"Starting from channel_{next_number}\n")
    
    seen_content = set()
    channels_fetched = 0
    
    with Session(engine) as session:
        # Get channels with at least MIN_USER_MESSAGES from user
        query = text("""
            SELECT 
                c.id as channel_id,
                c.char_id,
                COUNT(CASE WHEN m.user_id IS NOT NULL THEN 1 END) as user_message_count,
                COUNT(m.id) as total_messages
            FROM public.channels c
            JOIN public.messages m ON m.channel_id = c.id
            WHERE m.text IS NOT NULL
              AND m.text != ''
            GROUP BY c.id, c.char_id
            HAVING COUNT(CASE WHEN m.user_id IS NOT NULL THEN 1 END) >= :min_user_messages
            ORDER BY c.id DESC
            LIMIT :limit
        """)
        
        channel_result = session.execute(
            query,
            {
                "min_user_messages": MIN_USER_MESSAGES,
                "limit": NUM_CHANNELS * 3,  # Get more to filter out duplicates
            },
        )
        
        channels_data = [(row[0], row[1], row[2], row[3]) for row in channel_result]
        
        for channel_id, char_id, user_message_count, total_messages in channels_data:
            if channels_fetched >= NUM_CHANNELS:
                break
            
            # Get all messages for this channel
            messages_query = text("""
                SELECT 
                    text,
                    user_id,
                    inserted_at,
                    message_type
                FROM public.messages
                WHERE channel_id = :channel_id
                  AND (text IS NOT NULL OR message_type IS NOT NULL)
                ORDER BY inserted_at ASC
            """)
            
            messages_result = session.execute(
                messages_query,
                {"channel_id": channel_id},
            )
            
            messages_list = [
                {
                    "text": row[0],
                    "user_id": row[1],
                    "inserted_at": row[2],
                    "message_type": row[3],
                }
                for row in messages_result
            ]
            
            if not messages_list:
                continue
            
            # Format dialog
            dialog_text = format_dialog(messages_list)
            
            # Skip if we've seen similar content
            dialog_hash = hash(dialog_text[:500])  # Hash first 500 chars
            if dialog_hash in seen_content:
                continue
            seen_content.add(dialog_hash)
            
            # Get character name if available
            char_name = None
            if char_id:
                char_query = text("""
                    SELECT name
                    FROM content.content_characters
                    WHERE id = :char_id
                    LIMIT 1
                """)
                char_result = session.execute(char_query, {"char_id": char_id})
                char_row = char_result.fetchone()
                if char_row:
                    char_name = char_row[0]
            
            # Save to file
            filename = output_dir / f"channel_{channel_id}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# Channel {channel_id} - Full Dialogue\n\n")
                f.write(f"## Channel Info\n")
                f.write(f"- Channel ID: {channel_id}\n")
                if char_name:
                    f.write(f"- Character: {char_name} (ID: {char_id})\n")
                elif char_id:
                    f.write(f"- Character ID: {char_id}\n")
                f.write(f"- Total messages: {total_messages}\n")
                f.write(f"- User messages: {user_message_count}\n")
                f.write(f"\n---\n\n")
                f.write(f"## Messages\n\n")
                f.write(dialog_text)
            
            print(f"Saved: channel_{channel_id}.md ({total_messages} messages, {user_message_count} from user)")
            channels_fetched += 1
    
    print(f"\n{'=' * 60}")
    print(f"Summary: Fetched {channels_fetched} channels")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()

