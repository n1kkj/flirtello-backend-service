from datetime import datetime
import pytest
# from pytest_mock import mocker
from sqlalchemy import Engine, create_engine
from supabase import create_client

from lib.auth import SupabaseAuth
from lib.memory import summarize_channel
from .content_models import LLMStats, Summary
from .chat_models import ChatUser, Channel, Message
from sqlmodel import select, Session
import os

from .messages import send_message, get_messages, find_or_create_channel_id

from dotenv import load_dotenv
load_dotenv()


DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"

dbschema = "content,public"

# Create the database engine
engine = create_engine(
    DATABASE_URL, connect_args={"options": "-csearch_path={}".format(dbschema)}
)


@pytest.fixture(name="session")
def session_fixture():
    with Session(engine) as session:
        yield session
        # Cleanup after each test
        session.rollback()


auth = SupabaseAuth(
    os.environ.get("API_URL"),
    os.environ.get("SERVICE_ROLE_KEY"),
    os.environ.get("PASSKEY"),
    engine,
)


def test_summary_crud(session):
    auth.delete_user_by_email("summaries@flirtello.com")
    c_u1 = create_client(
        os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY")
    )
    u1 = c_u1.auth.sign_up(
        {"email": "summaries@flirtello.com", "password": "qweqwe123123"}
    ).user

    send_message(session, 1, u1.id, "user", "test")
    channel = session.exec(select(Channel)).first()
    summary = Summary(
        channel_id=channel.id,
        summary="test",
        message_date_from=datetime(2024, 1, 1, 1, 1, 1, 1),
        message_date_to=datetime(2024, 1, 1, 1, 1, 1, 1)
    )
    session.add(summary)
    session.commit()
    session.refresh(summary)
    session.delete(summary)
    session.commit()
    c_u1.auth.sign_out()
    auth.delete_user_by_email("summaries@flirtello.com")


def test_summaries(session):
    return
    try:
        auth.delete_user_by_email("summaries@flirtello.com")

        c_u1 = create_client(
            os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY")
        )
        u1 = c_u1.auth.sign_up(
            {"email": "summaries@flirtello.com", "password": "qweqwe123123"}
        ).user

        with open("lib/test_dialog.txt", "r") as f:
            dialog = f.read()
        
        dialog = dialog.split("\n")

        char = True
        for line in dialog:
            if line == "":
                continue
            if char:
                send_message(session, 1, u1.id, "character", line, LLMStats(model_id="dummy", model_latency=0, input_tokens=0, output_tokens=0))
            else:
                send_message(session, 1, u1.id, "user", line)
            char = not char

        messages = get_messages(session, 1, u1.id)
        assert len(messages) == 14
        assert messages[0].text.startswith("Hey")
        # mocker.patch('lib.llm_methods.summarize_conversation', return_value=("hi!", LLMStats(model_id="dummy", model_latency=0, input_tokens=0, output_tokens=0)))
        res, stats = summarize_channel(session, messages[0].channel_id)
        assert res is not None

    finally:
        c_u1.auth.sign_out()
        auth.delete_user_by_email("summaries@flirtello.com")
