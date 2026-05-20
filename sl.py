import os

import streamlit as st
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select

from src.db.lib.chat_models import Message
from src.db.lib.content_models import ContentCharacter

load_dotenv("src/.env")

DB_URL = os.getenv("DB_URL", None)
dbschema = "content,public,auth,extensions"

if DB_URL is None:
    raise ValueError("DB_URL is not set")

engine = create_engine(
    DB_URL, echo=False, connect_args={"options": "-csearch_path={}".format(dbschema)}
)

st.title("Hello World")

st.write("This is a test")

with Session(engine) as session:
    characters = session.exec(select(ContentCharacter)).all()
    # st.write(characters)

    messages = session.exec(select(Message).where(Message.char_id == 1)).all()
    # st.write(messages)