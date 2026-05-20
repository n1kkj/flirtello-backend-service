import pytest
import lib.content_models as content_models
from sqlmodel import create_engine, SQLModel, Session, select
from uuid import uuid4
from datetime import datetime
import os

ContentCharacter = content_models.ContentCharacter

DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"

dbschema = "content,public"

# Create the database engine
engine = create_engine(DATABASE_URL, connect_args={'options': '-csearch_path={}'.format(dbschema)})

@pytest.fixture(name="temporary_session")
def session_fixture():
    with Session(engine) as session:
        yield session
        # Cleanup after each test
        session.rollback()

def test_create_content_character(temporary_session):
    session = temporary_session
    user = session.exec(select(content_models.DirectusUser)).first()
    context = content_models.ContentContext(
            name="Test Context",
            context_type="first_interaction"
        )
    character = ContentCharacter(
        status="published",
        sort=1,
        user_created=user.id,
        date_created=datetime.utcnow(),
        user_updated=None,
        date_updated=None,
        name="Test Character",
        personality="Test Personality",
        usable_contexts=[context]
    )
    session.add(context)
    session.add(character)
    session.commit()
    session.refresh(character)
    assert character.id is not None
    assert character.usable_contexts[0].context_type == "first_interaction"
    
    # Cleanup
    session.delete(character)
    session.delete(context)
    session.commit()

def test_read_content_character(temporary_session):
    session = temporary_session
    character = ContentCharacter(
        status="draft",
        name="Test Character Read"
    )
    session.add(character)
    session.commit()
    session.refresh(character)

    retrieved_character = session.get(ContentCharacter, character.id)
    assert retrieved_character is not None
    assert retrieved_character.name == "Test Character Read"
    
    # Cleanup
    session.delete(character)
    session.commit()

def test_update_content_character(temporary_session):
    session = temporary_session
    character = ContentCharacter(
        status="draft",
        name="Test Character Update"
    )
    session.add(character)
    session.commit()
    session.refresh(character)

    character.name = "Updated Character"
    session.add(character)
    session.commit()
    session.refresh(character)

    updated_character = session.get(ContentCharacter, character.id)
    assert updated_character.name == "Updated Character"
    
    # Cleanup
    session.delete(character)
    session.commit()

def test_delete_content_character(temporary_session):
    session = temporary_session
    character = ContentCharacter(
        status="draft",
        name="Test Character Delete"
    )
    session.add(character)
    session.commit()
    session.refresh(character)

    session.delete(character)
    session.commit()

    deleted_character = session.get(ContentCharacter, character.id)
    assert deleted_character is None
