import os
import uuid
from datetime import datetime

import pytest
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, delete, text
from sqlmodel import Session, select

from lib.auth import SupabaseAuth
from supabase import create_client

from .chat_models import Channel, ChatUser, Message, MessageType, ReviewStatus
from .content_models import ArchivedMessage, ContentCharacter, ContentContext, LLMStats
from .messages import (
    add_review_to_message,
    archive_messages,
    find_or_create_channel_id,
    get_message_images,
    get_messages,
    group_messages_attachments,
    send_message,
    send_message_and_get_response,
    start_new_chat_and_send_first_message,
)

load_dotenv()


DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"

dbschema = "content,public"

# Create the database engine
engine = create_engine(DATABASE_URL, connect_args={"options": "-csearch_path={}".format(dbschema)})


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


def test_archived_messages_crud(session):
    msg = ArchivedMessage(
        id=1,
        inserted_at=datetime.now(),
        text="test",
        attachments=None,
        user_id=uuid.uuid4(),
        char_id=1,
        channel_id=1,
        archive_id=uuid.uuid4(),
        archive_time=datetime.now(),
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    assert msg.id == 1
    assert msg.text == "test"
    session.delete(msg)
    session.commit()


def test_channel_creation(session):
    auth.delete_user_by_email("rlstest1@flirtello.com")
    c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
    u1 = c_u1.auth.sign_up({"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}).user
    try:
        channel_id = find_or_create_channel_id(session, 1, u1.id)
        channel = session.exec(select(Channel).where(Channel.id == channel_id)).one()
        assert channel.id == channel_id
        assert channel.current_char_context != None
        context = session.exec(
            select(ContentContext).where(ContentContext.id == channel.current_char_context)
        ).one()
        assert context is not None
    finally:
        c_u1.auth.sign_out()
        auth.delete_user_by_email("rlstest1@flirtello.com")


def test_messages():
    try:
        with Session(engine) as session:
            auth.delete_user_by_email("rlstest1@flirtello.com")
            auth.delete_user_by_email("rlstest2@flirtello.com")

            c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
            u1 = c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user
            c_u2 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
            u2 = c_u2.auth.sign_up(
                {"email": "rlstest2@flirtello.com", "password": "qweqwe123123"}
            ).user

            start_new_chat_and_send_first_message(session, u1.id, 1)
            start_new_chat_and_send_first_message(session, u2.id, 1)

            send_message(session, 1, u1.id, "user", "yo!")
            messages = get_messages(session, 1, u1.id)
            assert len(messages) == 2
            assert messages[1].text == "yo!"

            send_message(session, 1, u2.id, "user", "hey!")
            messages = get_messages(session, 1, u2.id)
            assert len(messages) == 2
            assert messages[1].text == "hey!"

            result1 = c_u1.table("messages").select("*").execute()
            assert len(result1.data) == 2
            result2 = c_u2.table("messages").select("*").execute()
            assert len(result2.data) == 2

            # Test RLS
            result1 = c_u1.table("channels").select("*").execute()
            assert len(result1.data) == 1
            result2 = c_u2.table("channels").select("*").execute()
            assert len(result2.data) == 1

            result1 = c_u1.table("users").select("*").execute()
            assert len(result1.data) == 0
            result2 = c_u2.table("users").select("*").execute()
            assert len(result2.data) == 0

            # test LLM stats for the character messages
            with pytest.raises(ValueError):
                send_message(session, 1, u2.id, "character", "hey!")
            msg_id = send_message(
                session, 1, u1.id, "character", "hey!", llm_stats=LLMStats.dummy()
            ).id

            msg = session.get(Message, msg_id)
            assert msg.text == "hey!"
            session.commit()

            # commented out not to use tokens for every test run
            # rrr = send_message_and_get_response(session, u1.id, 1, "I want you!")
            # assert rrr is not None

            archive_id, ids = archive_messages(session, 1, u1.id)
            assert len(ids) == 3
            archived_items = session.exec(
                select(ArchivedMessage).where(ArchivedMessage.archive_id == archive_id)
            ).all()
            assert len(archived_items) == 3
            [session.delete(msg) for msg in archived_items]

            u2_msg_id = send_message(
                session, 1, u2.id, "character", "hey!", llm_stats=LLMStats.dummy()
            ).id
            llm_stats = session.exec(
                select(LLMStats).where(
                    (LLMStats.ref_id == u2_msg_id) & (LLMStats.ref_type == "message")
                )
            ).first()
            assert llm_stats.model_id == "dummy"
            session.delete(llm_stats)
            session.exec(
                delete(LLMStats).where(
                    (LLMStats.ref_id.in_(ids) == True) & (LLMStats.ref_type == "message_archive")
                )
            )
            session.commit()

    finally:
        c_u1.auth.sign_out()
        c_u2.auth.sign_out()

        auth.delete_user_by_email("rlstest1@flirtello.com")
        auth.delete_user_by_email("rlstest2@flirtello.com")


def test_messages_reviews():
    try:
        with Session(engine) as session:
            auth.delete_user_by_email("rlstest1@flirtello.com")
            c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
            u1 = c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user
            start_new_chat_and_send_first_message(session, u1.id, 1)
            reviewing_message_id = send_message(
                session, 1, u1.id, "character", "hello", llm_stats=LLMStats.dummy()
            ).id
            dislike_rew_cat = ["Awful", "Ugly"]
            like_rew_text = "so cool!"

            # Checking for all review types
            add_review_to_message(
                session, reviewing_message_id, ReviewStatus.DISLIKE, dislike_rew_cat
            )
            messages = get_messages(session, 1, u1.id)
            assert messages[-1].review_status == ReviewStatus.DISLIKE
            assert messages[-1].review_categories == dislike_rew_cat
            assert messages[-1].review_text is None
            add_review_to_message(session, reviewing_message_id, ReviewStatus.NEUTRAL)
            messages = get_messages(session, 1, u1.id)

            # Checking default fields if review status is neutral
            assert messages[-1].review_status == ReviewStatus.NEUTRAL
            assert messages[-1].review_categories is None
            assert messages[-1].review_text is None
            add_review_to_message(
                session,
                reviewing_message_id,
                ReviewStatus.LIKE,
                review_text=like_rew_text,
            )
            messages = get_messages(session, 1, u1.id)
            assert messages[-1].review_status == ReviewStatus.LIKE
            assert messages[-1].review_categories is None
            assert messages[-1].review_text == like_rew_text

            # Sending new message
            reviewing_message_id2 = send_message(
                session, 1, u1.id, "character", "hello again", llm_stats=LLMStats.dummy()
            ).id
            messages = get_messages(session, 1, u1.id)

            # Checking default fields
            assert messages[-1].review_status == ReviewStatus.NEUTRAL
            assert messages[-1].review_categories is None
            assert messages[-1].review_text is None

            # Adding review to new message
            add_review_to_message(
                session,
                reviewing_message_id2,
                ReviewStatus.DISLIKE,
            )
            assert messages[-2].review_status == ReviewStatus.LIKE

            # Ensure that previous message don't change his review status
            assert messages[-1].review_status == ReviewStatus.DISLIKE

    finally:
        c_u1.auth.sign_out()
        auth.delete_user_by_email("rlstest1@flirtello.com")


def test_group_messages_attachments(session):
    # Create test messages with different scenarios
    messages = (
        [
            # Greeting image - should not be grouped
            Message(
                id=1,
                text="",
                attachments=[{"type": "image", "id": "greeting1"}],
                message_type=MessageType.GREETING_IMAGE,
                channel_id=1,
            ),
            # Empty text messages with attachments - should be grouped
            Message(
                id=2,
                text="",
                attachments=[{"type": "image", "id": "img1"}],
                message_type=MessageType.DEFAULT_IMAGE,
                channel_id=1,
            ),
            Message(
                id=3,
                text="",
                attachments=[{"type": "image", "id": "img2"}],
                message_type=MessageType.DEFAULT_IMAGE,
                channel_id=1,
            ),
            # Message with text - should break group
            Message(
                id=4,
                text="Hello!",
                attachments=None,
                message_type=MessageType.DEFAULT_TEXT,
                channel_id=1,
            ),
            # Series of messages that should be grouped up to max size (9)
        ]
        + [
            Message(
                id=5 + i,
                text="",
                attachments=[{"type": "image", "id": f"img{i}"}],
                message_type=MessageType.DEFAULT_IMAGE,
                channel_id=1,
            )
            for i in range(10)  # 10 messages with single attachment each
        ]
        + [
            # Last message - should not be grouped even if it could be
            Message(
                id=15,
                text="",
                attachments=[{"type": "image", "id": "last_img"}],
                message_type=MessageType.DEFAULT_IMAGE,
                channel_id=1,
            ),
        ]
    )

    result = group_messages_attachments(messages)

    # Test assertions
    assert len(result) == 6  # greeting + first group + text + second group + remaining + last

    # First message should be greeting image, unchanged
    assert result[0].id == 1
    assert result[0].message_type == MessageType.GREETING_IMAGE
    assert len(result[0].attachments) == 1
    assert result[0].attachments[0]["id"] == "greeting1"

    # Second message should be grouped from messages 2 and 3
    assert result[1].id == 2
    assert len(result[1].attachments) == 2
    assert result[1].attachments[0]["id"] == "img1"  # Should be prepended
    assert result[1].attachments[1]["id"] == "img2"

    # Third message should be the text message
    assert result[2].id == 4
    assert result[2].text == "Hello!"
    assert result[2].attachments is None

    # Fourth message should contain first 9 attachments from the series
    assert result[3].id == 5
    assert len(result[3].attachments) == 9  # Max size
    for i in range(9):
        assert result[3].attachments[i]["id"] == f"img{i}"

    # Fifth message should contain the remaining attachment
    assert result[4].id == 14  # Last message from the series
    assert len(result[4].attachments) == 1
    assert result[4].attachments[0]["id"] == "img9"

    # Sixth message should be the last message, not grouped
    assert result[5].id == 15
    assert len(result[5].attachments) == 1
    assert result[5].attachments[0]["id"] == "last_img"

    # Test empty input
    assert group_messages_attachments([]) == []

    # Test single message
    single_message = Message(
        id=1,
        text="",
        attachments=[{"type": "image", "id": "single"}],
        message_type=MessageType.DEFAULT_IMAGE,
        channel_id=1,
    )
    result = group_messages_attachments([single_message])
    assert len(result) == 1
    assert result[0].id == 1
    assert len(result[0].attachments) == 1
    assert result[0].attachments[0]["id"] == "single"


def test_get_message_images(session):
    # Create test messages with different scenarios
    image_id1 = uuid.uuid4()
    image_id2 = uuid.uuid4()
    image_id3 = uuid.uuid4()

    messages = [
        # Message with no attachments
        Message(
            id=1,
            text="Hello",
            attachments=None,
            channel_id=1,
        ),
        # Message with one image attachment
        Message(
            id=2,
            text="",
            attachments=[{"type": "image", "id": str(image_id1)}],  # Convert UUID to string
            channel_id=1,
        ),
        # Message with multiple attachments including non-image
        Message(
            id=3,
            text="Check these out",
            attachments=[
                {"type": "image", "id": str(image_id2)},  # Convert UUID to string
                {"type": "file", "id": str(uuid.uuid4())},
                {"type": "image", "id": str(image_id3)},  # Convert UUID to string
            ],
            channel_id=1,
        ),
    ]

    # Get image IDs using the function
    result = get_message_images(messages)

    # Verify results
    assert len(result) == 3
    assert image_id1 in result
    assert image_id2 in result
    assert image_id3 in result

    # Test with empty message list
    assert len(get_message_images([])) == 0

    # Test with message containing empty attachments
    empty_message = Message(id=4, text="No attachments", attachments=[], channel_id=1)
    assert len(get_message_images([empty_message])) == 0
