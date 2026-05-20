#!/usr/bin/env python3
"""
Fetch test messages from PostgreSQL database, categorized by length.
Gets character messages (user_id IS NULL) for character_id 24.
"""

import os
import re
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

CHARACTER_ID = 24
NUM_PER_CATEGORY = 3  # How many messages to fetch per length category


def count_words(text: str) -> int:
    """Count words in text"""
    if not text:
        return 0
    # Remove markdown formatting and count words
    text_clean = re.sub(r"\*[^*]+\*", "", text)  # Remove italic/bold
    text_clean = re.sub(r"[^\w\s]", " ", text_clean)  # Replace punctuation with spaces
    words = text_clean.split()
    return len(words)


def count_sentences(text: str) -> int:
    """Count sentences in text"""
    if not text:
        return 0
    # Count sentence endings
    sentences = re.split(r"[.!?]+", text)
    # Filter out empty strings
    sentences = [s.strip() for s in sentences if s.strip()]
    return len(sentences)


def classify_message_length(text: str) -> str:
    """Classify message as short, medium, or long"""
    word_count = count_words(text)
    sentence_count = count_sentences(text)

    # Short: 1-5 sentences, up to ~40 words
    if sentence_count <= 5 and word_count <= 40:
        return "short"
    # Medium: 4-6 sentences, ~35-70 words
    elif sentence_count <= 6 and word_count <= 70:
        return "medium"
    # Long: 6+ sentences or 70+ words
    else:
        return "long"


def get_message_position_simple(total_messages: int) -> str:
    """Simple position determination - just use 'middle' for all"""
    # For message transformation experiments, position is not critical
    return "middle"


def main():
    base_dir = Path(__file__).parent
    output_dir = base_dir / "test_messages"
    output_dir.mkdir(exist_ok=True)

    # Find existing message numbers
    existing_files = list(output_dir.glob("message_*.md"))
    existing_numbers = []
    for f in existing_files:
        try:
            num = int(f.stem.split("_")[1])
            existing_numbers.append(num)
        except (ValueError, IndexError):
            pass

    next_number = max(existing_numbers) + 1 if existing_numbers else 1

    print(f"Fetching messages for character_id {CHARACTER_ID}...")
    print(f"Target: {NUM_PER_CATEGORY} messages per category (short, medium, long)\n")

    # Track messages by category - process one by one
    messages_by_category = {
        "short": [],
        "medium": [],
        "long": [],
    }
    seen_content = set()

    with Session(engine) as session:
        # Get character messages (user_id IS NULL) from channels with char_id 24
        query = text("""
            SELECT 
                m.id,
                m.text,
                (SELECT COUNT(*) FROM public.messages WHERE channel_id = m.channel_id) as total_messages
            FROM public.messages m
            JOIN public.channels c ON c.id = m.channel_id
            WHERE c.char_id = :char_id
              AND m.user_id IS NULL
              AND m.text IS NOT NULL
              AND m.text != ''
              AND LENGTH(m.text) > 10
            ORDER BY m.inserted_at DESC
            LIMIT 3000
        """)

        result = session.execute(query, {"char_id": CHARACTER_ID})

        for row in result:
            # Check if we have enough messages in all categories
            if all(
                len(messages_by_category[cat]) >= NUM_PER_CATEGORY
                for cat in messages_by_category
            ):
                break

            message_id, message_text, total_messages = row

            if not message_text or not message_text.strip():
                continue

            # Skip if we've seen similar content
            text_hash = hash(message_text[:200])
            if text_hash in seen_content:
                continue
            seen_content.add(text_hash)

            # Classify message length
            word_count = count_words(message_text)
            sentence_count = count_sentences(message_text)
            length_category = classify_message_length(message_text)

            # Check if we need more of this category
            if len(messages_by_category[length_category]) >= NUM_PER_CATEGORY:
                continue

            # Simple position - just use middle
            position = get_message_position_simple(total_messages)

            messages_by_category[length_category].append(
                {
                    "text": message_text,
                    "length": length_category,
                    "position": position,
                    "word_count": word_count,
                    "sentence_count": sentence_count,
                }
            )

            print(
                f"Found {length_category} message: {word_count} words, {sentence_count} sentences"
            )

    # Save messages
    for category, messages in messages_by_category.items():
        for msg in messages:
            filename = (
                output_dir
                / f"message_{next_number:03d}_{msg['length']}_{msg['position']}.md"
            )
            with open(filename, "w", encoding="utf-8") as f:
                f.write(msg["text"])

            print(
                f"Saved: {filename.name} ({msg['word_count']} words, {msg['sentence_count']} sentences)"
            )
            next_number += 1

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary:")
    for category, messages in messages_by_category.items():
        print(f"  {category}: {len(messages)} messages")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
