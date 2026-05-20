import threading
import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from datetime import datetime

from lib.crypto import encrypt
from .chat_models import ChatUser
from .content_models import ContentCharacter # just to load to the SQLModel context

from uuid import uuid4
import os

#if os.environ.get("TEST_ENV") != "ci":
from dotenv import load_dotenv
load_dotenv()

from .auth import SupabaseAuth

DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"
dbschema = "content,public,auth"

# Create the database engine
engine = create_engine(DATABASE_URL, connect_args={'options': '-csearch_path={}'.format(dbschema)}) 

auth = SupabaseAuth(
    os.environ.get("API_URL"),
    os.environ.get("SERVICE_ROLE_KEY"),
    os.environ.get("PASSKEY"),
    engine
)

users_created = []

def test_create_user():
    email = "qwe@qwe.com"
    password = "XXXXXX"

    auth.delete_user_by_email(email)

    user = auth.create_normal_user(email, password)
    assert user["email"] == email

    gu_resp = auth.get_user(user["id"])
    assert gu_resp.user.id == user["id"]

    auth.delete_user(gu_resp.user.id)
    
def test_create_tg_user():
    tg_id = "12345"
    auth.delete_user_by_email(f"{tg_id}@tg.flirtello.com")
    user = auth.create_tg_user(tg_id, "Вася")
    assert str(user.tg_id) == tg_id

    user = SupabaseAuth.find_user_by_tg_id(engine, tg_id)
    assert str(user.tg_id) == tg_id

    client = auth.login_with_password_and_get_client(f"{tg_id}@tg.flirtello.com", encrypt(f"{tg_id}@tg.flirtello.com", auth.passkey))
    client.from_("channels").select("*").execute()
    client.auth.sign_out()
    
    auth.delete_user_by_email(f"{tg_id}@tg.flirtello.com")
