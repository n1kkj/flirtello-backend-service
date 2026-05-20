from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import Json
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, HSTORE, JSON, JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .content_models import ContentCharacter, ContentContext, LLMStats, Summary


class AuthUser(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    instance_id: Optional[UUID] = Field(default=None, primary_key=False)
    id: UUID = Field(default=None, primary_key=True)
    aud: Optional[str] = Field(max_length=255)
    role: Optional[str] = Field(max_length=255)
    email: Optional[str] = Field(max_length=255)
    encrypted_password: Optional[str] = Field(max_length=255)
    email_confirmed_at: Optional[datetime] = Field(default=None)
    invited_at: Optional[datetime] = Field(default=None)
    confirmation_token: Optional[str] = Field(max_length=255)
    confirmation_sent_at: Optional[datetime] = Field(default=None)
    recovery_token: Optional[str] = Field(max_length=255)
    recovery_sent_at: Optional[datetime] = Field(default=None)
    email_change_token_new: Optional[str] = Field(max_length=255)
    email_change: Optional[str] = Field(max_length=255)
    email_change_sent_at: Optional[datetime] = Field(default=None)
    last_sign_in_at: Optional[datetime] = Field(default=None)
    raw_app_meta_data: Optional[Json] = Field(default=None, sa_column=Column(JSON))
    raw_user_meta_data: Optional[Json] = Field(default=None, sa_column=Column(JSON))
    is_super_admin: Optional[bool] = Field(default=None)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    phone_confirmed_at: Optional[datetime] = Field(default=None)
    phone_change: Optional[str] = Field(default="")
    phone_change_token: Optional[str] = Field(default="")
    phone_change_sent_at: Optional[datetime] = Field(default=None)
    confirmed_at: Optional[datetime] = Field(default=None)
    email_change_token_current: Optional[str] = Field(default="")
    email_change_confirm_status: Optional[int] = Field(default=0, ge=0, le=2)
    banned_until: Optional[datetime] = Field(default=None)
    reauthentication_token: Optional[str] = Field(default="")
    reauthentication_sent_at: Optional[datetime] = Field(default=None)
    is_sso_user: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)
    is_anonymous: bool = Field(default=False)


class UserStatus(PyEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class ChatUser(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id: UUID = Field(primary_key=True, foreign_key="auth.users.id", nullable=False)
    display_name: Optional[str] = Field(default=None)
    tg_id: Optional[str] = Field(default=None)
    status: UserStatus = Field(
        default=UserStatus.OFFLINE, sa_column_kwargs={"server_default": "OFFLINE"}
    )
    settings: dict = Field(sa_column=Column(HSTORE), default={})

    channels: List["Channel"] = Relationship(back_populates="user")
    messages: List["Message"] = Relationship(back_populates="user")


class Channel(SQLModel, table=True):
    __tablename__ = "channels"
    __table_args__ = {"schema": "public"}

    id: int = Field(default=None, primary_key=True)
    inserted_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": "timezone('utc', now())"},
    )
    user_id: UUID = Field(foreign_key="public.users.id", nullable=False)
    char_id: int = Field(default=None, foreign_key="content.content_characters.id", nullable=False)
    current_char_context: Optional[int] = Field(
        default=None, foreign_key="content.content_contexts.id", nullable=True
    )
    config_id: Optional[UUID] = Field(default=None, nullable=True)
    stage_name: Optional[str] = Field(default=None, nullable=True)

    messages: List["Message"] = Relationship(back_populates="channel")
    summaries: list["Summary"] = Relationship(back_populates="channel")

    user: "ChatUser" = Relationship(back_populates="channels")
    character: "ContentCharacter" = Relationship(back_populates="channels")
    context: "ContentContext" = Relationship(back_populates="channels")


class ReviewStatus(PyEnum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"
    NEUTRAL = "NEUTRAL"


class MessageType(PyEnum):
    DEFAULT_TEXT = "DEFAULT_TEXT"
    ONBOARDING_TEXT = "ONBOARDING_TEXT"
    GREETING_TEXT = "GREETING_TEXT"
    GREETING_IMAGE = "GREETING_IMAGE"
    DEFAULT_IMAGE = "DEFAULT_IMAGE"
    SCENARIO_TEXT = "SCENARIO_TEXT"


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    __table_args__ = {"schema": "public"}

    id: Optional[int] = Field(default=None, primary_key=True)
    inserted_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": "timezone('utc', now())"},
    )
    text: Optional[str] = Field(default=None)
    attachments: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    user_id: Optional[UUID] = Field(foreign_key="public.users.id", nullable=True)
    char_id: Optional[int] = Field(default=None, foreign_key="content.content_characters.id")
    channel_id: int = Field(foreign_key="public.channels.id", nullable=False)
    review_status: ReviewStatus = Field(
        sa_column=Column(
            ENUM(ReviewStatus, name="message_review_status"), default=ReviewStatus.NEUTRAL
        )
    )
    review_categories: Optional[list[str]] = Field(
        sa_column=Column(ARRAY(String), default=None, nullable=True)
    )
    review_text: Optional[str] = Field(default=None, nullable=True)
    message_type: MessageType = Field(
        nullable=True, sa_column_kwargs={"server_default": MessageType.DEFAULT_TEXT.value}
    )
    stage_name: Optional[str] = Field(default=None, nullable=True)

    user: "ChatUser" = Relationship(back_populates="messages")
    channel: "Channel" = Relationship(back_populates="messages")
