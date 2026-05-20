import os
import random
from datetime import datetime, timedelta
from typing import Tuple

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlmodel import Session, select

from lib.llm.llm_methods import summarize_conversation

from .chat_models import Channel, ChatUser, Message
from .content_models import ContentCharacter, ContentContext, LLMStats, Summary

if os.environ.get("TEST_ENV") != "ci":
    from dotenv import load_dotenv

    load_dotenv()


# TODO: make sure that this goes asynchronously
def summarize_channel(session: Session, channel_id) -> Tuple[Summary, LLMStats]:
    # get last summary for channel

    channel = session.get(Channel, channel_id)
    if channel is None:
        print(f"Channel {channel_id} not found")
        return None

    # figure out the time-frame to summarize
    first_message_date = datetime(2024, 1, 1, 0, 0, 0, 0)
    summary = session.exec(
        select(Summary)
        .where(Summary.channel_id == channel_id)
        .order_by(Summary.message_date_to.desc())
    ).first()

    # if it's not the first summary, set the date for the date of the last summarized message
    if summary is not None:
        first_message_date = summary.message_date_to + timedelta(microseconds=1)

    # get mesages to summarize
    messages = session.exec(
        select(Message)
        .where(Message.channel_id == channel_id)
        .where(Message.inserted_at > first_message_date)
        .order_by(Message.inserted_at.asc())
    ).all()

    # run llm
    res, stats = summarize_conversation(messages)

    print(res, stats)
    # save summary

    summary = Summary(
        channel_id=channel_id,
        summary=res,
        message_date_from=messages[0],
        message_date_to=messages[-1].inserted_at,
    )

    return summary, stats
