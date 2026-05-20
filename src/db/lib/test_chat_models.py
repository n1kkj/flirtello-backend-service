import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from datetime import datetime
from uuid import uuid4

from supabase import create_client
from lib.chat_models import AuthUser, Channel, ChatUser, Message, UserStatus  # Assuming the models are in a file named models.py
import os
from sqlalchemy.orm.attributes import flag_modified

from lib.content_models import ContentCharacter
from .auth import SupabaseAuth

#if os.environ.get("TEST_ENV") != "ci":
from dotenv import load_dotenv
load_dotenv()


DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"

dbschema = "content,public,auth,extensions"

# Create the database engine
engine = create_engine(DATABASE_URL, echo=True, connect_args={'options': '-csearch_path={}'.format(dbschema)}) 

@pytest.fixture(name="session")
def session_fixture():
    with Session(engine) as session:
        yield session
        # Cleanup
        session.rollback()

def test_channel_and_messages(session):
    auth = SupabaseAuth(
        os.environ.get("API_URL"),
        os.environ.get("SERVICE_ROLE_KEY"),
        os.environ.get("PASSKEY"),
        engine
    )

    email = "testuser@flirtello.com"
    password = "weoifn2ofin2o3finwoeifn"
    auth.delete_user_by_email(email)
    user = auth.create_normal_user(email, password)


    char = session.exec(select(ContentCharacter).where(ContentCharacter.id == 1)).first()


    # Create a channel
    channel = Channel(user_id=user["id"], char_id=1, current_char_context=char.usable_contexts[0].id)
    session.add(channel)
    session.commit()

    # Verify the channel is created
    statement = select(Channel).where(Channel.user_id == user["id"])
    channels = session.exec(statement).all()
    assert len(channels) == 1
    assert channels[0].char_id == 1
    assert channels[0].current_char_context == char.usable_contexts[0].id

    # Post a message from the character (bot)
    bot_message = Message(
        text="Hello from the bot",
        user_id=None,
        char_id=1,
        channel_id=channel.id,
        inserted_at=datetime.utcnow()
    )
    session.add(bot_message)
    session.commit()

    # Post a message from the user
    user_message = Message(
        text="Hello from the user",
        user_id=user["id"],
        char_id=None,
        channel_id=channel.id,
        inserted_at=datetime.utcnow()
    )
    session.add(user_message)
    session.commit()

    # Verify the messages are created
    statement = select(Message).where(Message.channel_id == channel.id)
    messages = session.exec(statement).all()
    assert len(messages) == 2
    assert messages[0].text == "Hello from the bot"
    assert messages[1].text == "Hello from the user"

    # Cleanup: remove messages and channel
    # session.delete(user_message)
    # session.delete(bot_message)
    statement = select(Message).where(Message.channel_id == channel.id)
    messages = session.exec(statement).all()
    for message in messages:
        session.delete(message)
    session.delete(channel)
    session.commit()

    auth.delete_user_by_email(email)

    # Verify everything is removed
    statement = select(Message).where(Message.channel_id == channel.id)
    messages = session.exec(statement).all()
    assert len(messages) == 0

    statement = select(Channel).where(Channel.user_id == user["id"])
    channels = session.exec(statement).all()
    assert len(channels) == 0

    statement = select(AuthUser).where(AuthUser.id == user["id"])
    users = session.exec(statement).all()
    assert len(users) == 0



def test_user_settings(session):
    auth = SupabaseAuth(
        os.environ.get("API_URL"),
        os.environ.get("SERVICE_ROLE_KEY"),
        os.environ.get("PASSKEY"),
        engine
    )

    user = auth.create_tg_user(123456, "Basil")
    user_id = user.id
    with Session(engine):
        user = session.get(ChatUser, user_id)
        if user.settings is None:
            user.settings = {}
        
        user.settings['qwe'] = 'asd'
        flag_modified(user, 'settings')
        session.commit()
        session.refresh(user)

    with Session(engine):
        user = session.get(ChatUser, user_id)
        assert user.settings['qwe'] == 'asd'

        auth.delete_user(user_id)