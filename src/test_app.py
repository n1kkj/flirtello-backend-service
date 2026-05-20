from typing import Annotated, Any, Callable
from fastapi import Depends
from fastapi.security import HTTPBearer
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
import pytest

import os

from src.db.lib.auth import SupabaseAuth
if os.environ.get("TEST_ENV") != "CI":
    from dotenv import load_dotenv
    load_dotenv(".env.dev")

from src.db.lib.chat_models import Channel
from src.lib.config import config

from .dependencies import get_current_user
from src.lib.verifier import TokenData

from .app import app
from sqlmodel import Session, create_engine, select

http_bearer = HTTPBearer()


async def mock_get_current_user(token: Annotated[str, Depends(http_bearer)]):
    return TokenData(user_id="mock_user")

def create_mock_get_current_user(user_id) -> Callable:
    async def mock_get_current_user(token: str = Depends(http_bearer)):
        return TokenData(user_id=user_id)
    
    return mock_get_current_user

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

class TestData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    session: Session
    user: Any

@pytest.fixture(scope="session")
def test_data():
    engine = create_engine(config.database_url)
    auth = SupabaseAuth(config.supabase_url, config.supabase_service_role_key, "", engine)
    email = "test_user@dev.flirtello.com"
    auth.delete_user_by_email(email)
    user = auth.create_normal_user(email, "test_password123")
    session = Session(engine)
    app.dependency_overrides[get_current_user] = create_mock_get_current_user(user['id'])
    yield TestData(session=session, user=user)
    # Удаление данных после завершения всех тестов
    auth.delete_user_by_email(email)


def test_roor(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}

headers={"Authorization": "Bearer mock_token"}

def test_read_users_me(client, test_data):
    response = client.get("/chat/me", headers=headers)
    print(response.text)
    assert response.status_code == 200
    assert response.json() == {"user_id": test_data.user['id']}

def test_chat_new_chat(client, test_data):
    response = client.put("/chat/with/char/1", headers=headers)
    print(response.text)
    assert response.status_code == 200
    assert response.json() == {"is_new": True}

    chans = test_data.session.exec(select(Channel).where(Channel.user_id == test_data.user['id'])).all()
    assert len(chans) == 1

def test_send_message(client, test_data):
    response = client.put("/chat/1/message", headers=headers, json={"message": "Hi!"})
    assert response.status_code == 200
    response_obj = response.json()
    assert response_obj['message'] is not None
    