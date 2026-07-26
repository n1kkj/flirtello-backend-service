import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import HSTORE, JSON, JSONB
from sqlmodel import Field, Relationship, SQLModel

from .llm.llm_enums import LLMModels, LLMProviders

if TYPE_CHECKING:
    from .chat_models import Channel


class DirectusUser(SQLModel, table=True):
    __tablename__ = "directus_users"
    __table_args__ = {"schema": "content"}
    id: UUID = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, max_length=255)
    first_name: Optional[str] = Field(default=None, max_length=255)
    last_name: Optional[str] = Field(default=None, max_length=255)
    # Additional fields as needed


class ContentContextCharacter(SQLModel, table=True):
    __tablename__ = "content_contexts_content_characters"
    __table_args__ = {"schema": "content"}
    id: int = Field(default=None, primary_key=True)
    content_contexts_id: Optional[int] = Field(
        default=None, foreign_key="content.content_contexts.id"
    )
    content_characters_id: Optional[int] = Field(
        default=None, foreign_key="content.content_characters.id"
    )


class ContentTraitCharacter(SQLModel, table=True):
    __tablename__ = "content_traits_content_characters"
    __table_args__ = {"schema": "content"}
    id: int = Field(default=None, primary_key=True)
    content_traits_id: Optional[int] = Field(default=None, foreign_key="content.content_traits.id")
    content_characters_id: Optional[int] = Field(
        default=None, foreign_key="content.content_characters.id"
    )


class ContentCharacter(SQLModel, table=True):
    __tablename__ = "content_characters"
    __table_args__ = {"schema": "content"}
    id: int = Field(default=None, primary_key=True)
    status: str = Field(default="draft", max_length=255)
    sort: Optional[int] = Field(default=None)
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = Field(default=None)
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = Field(default=None)
    name: Optional[str] = Field(default=None, max_length=255)
    personality: Optional[str] = Field(default=None)
    onboarding_message: Optional[str] = Field(nullable=True)
    telegram_description: Optional[str] = Field(nullable=True)
    background_image_id: Optional[UUID] = Field(
        default=None, foreign_key="content.directus_files.id", nullable=True
    )
    usable_contexts: List["ContentContext"] = Relationship(
        back_populates="used_by_characters", link_model=ContentContextCharacter
    )
    traits: List["ContentTrait"] = Relationship(
        back_populates="characters", link_model=ContentTraitCharacter
    )
    channels: List["Channel"] = Relationship(back_populates="character")

    system_prompt_override: str
    use_system_prompt_override: bool
    message_addendum_override: str
    use_message_addendum_override: bool


class ContentContext(SQLModel, table=True):
    __tablename__ = "content_contexts"
    __table_args__ = {"schema": "content"}
    id: int = Field(default=None, primary_key=True)
    status: str = Field(default="draft", max_length=255)
    sort: Optional[int] = Field(default=None)
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = Field(default=None)
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = Field(default=None)
    name: Optional[str] = Field(default=None, max_length=255)
    scenario: Optional[str] = Field(default=None)
    first_message: Optional[str] = Field(default=None)
    first_image: Optional[UUID] = Field(default=None, foreign_key="content.content_images.id")
    context_type: Optional[str] = Field(default="first_interaction")
    used_by_characters: List["ContentCharacter"] = Relationship(
        back_populates="usable_contexts", link_model=ContentContextCharacter
    )
    channels: List["Channel"] = Relationship(back_populates="context")


class ContentTrait(SQLModel, table=True):
    __tablename__ = "content_traits"
    __table_args__ = {"schema": "content"}
    id: int = Field(default=None, primary_key=True)
    status: str = Field(default="draft", max_length=255)
    sort: Optional[int] = Field(default=None)
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = Field(default=None)
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = Field(default=None)
    name: Optional[str] = Field(default=None, max_length=255)
    characters: List["ContentCharacter"] = Relationship(
        back_populates="traits", link_model=ContentTraitCharacter
    )


class LLMStats(SQLModel, table=True):
    __tablename__ = "llm_stats"
    __table_args__ = {"schema": "content"}

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: UUID
    ref_type: str
    ref_id: int
    model_id: str
    model_latency: int
    input_tokens: int
    output_tokens: int
    system_prompt: str
    chat_history: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    prompt: str
    response: str
    llm_provider: Optional[LLMProviders] = Field(nullable=True)

    @staticmethod
    def dummy():
        return LLMStats(
            model_id=LLMModels.DUMMY.value,
            model_latency=0,
            input_tokens=0,
            output_tokens=0,
        )


class Summary(SQLModel, table=True):
    __tablename__ = "summaries"
    __table_args__ = {"schema": "content"}

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    channel_id: int = Field(foreign_key="public.channels.id", nullable=False)
    message_date_from: datetime = Field(nullable=False)
    message_date_to: datetime = Field(nullable=False)
    summary: str = Field(nullable=False)

    channel: "Channel" = Relationship(back_populates="summaries")


class ArchivedMessage(SQLModel, table=True):
    __tablename__ = "message_archive"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True, index=True)
    inserted_at: datetime
    text: str
    attachments: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    user_id: UUID
    char_id: int
    channel_id: int
    archive_id: UUID
    archive_time: datetime


class ImageInfo(SQLModel, table=True):
    __tablename__ = "content_images"
    __table_args__ = {"schema": "content"}

    id: UUID = Field(primary_key=True, index=True, default_factory=uuid.uuid4)
    name: str = Field(max_length=255, nullable=False, unique=True)
    hash: str = Field(max_length=255, nullable=False)
    character: int = Field(foreign_key="content.content_characters.id")
    image: UUID = Field(default=None, foreign_key="content.directus_files.id", nullable=False)
    image_blurred: UUID = Field(
        default=None, foreign_key="content.directus_files.id", nullable=False
    )
    location: str = Field(max_length=255, nullable=False)
    cloths: str = Field(max_length=255, nullable=False)
    rating: str = Field(max_length=255, nullable=False)
    behavior: str = Field(max_length=255, nullable=False)
    prompt: str = Field(nullable=False)
    char_name: str = Field(max_length=255, nullable=False)
    is_free: bool = Field(nullable=False, default=False)
    config_id: Optional[UUID] = Field(foreign_key="content.character_configs.id", nullable=True)


class ImagesUserSettings(SQLModel, table=True):
    __tablename__ = "images_user_settings"
    __table_args__ = {"schema": "content"}

    id: UUID = Field(primary_key=True, index=True)
    settings: dict = Field(sa_column=Column(HSTORE), default={})


class UserImageView(SQLModel, table=True):
    __tablename__ = "images_views"
    __table_args__ = {"schema": "content"}

    id: UUID = Field(primary_key=True, index=True, default_factory=uuid.uuid4)
    image_id: UUID = Field(foreign_key="content.content_images.id", nullable=False)
    user_id: UUID = Field(nullable=False)


class ReviewTypes(PyEnum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class ContentReviewCategories(SQLModel, table=True):
    __tablename__ = "content_review_categories"
    __table_args__ = {"schema": "content"}

    id: UUID = Field(primary_key=True, index=True, default_factory=uuid.uuid4)
    review_type: ReviewTypes = Field(nullable=False)
    category_name: str = Field(nullable=False)


class DirectusFile(SQLModel, table=True):
    __tablename__ = "directus_files"
    __table_args__ = {"schema": "content"}

    id: UUID = Field(default=None, primary_key=True)
    storage: str = Field(max_length=255)
    filename_disk: Optional[str] = Field(default=None, max_length=255)
    filename_download: str = Field(max_length=255)
    title: Optional[str] = Field(default=None, max_length=255)
    type: Optional[str] = Field(default=None, max_length=255)
    folder: Optional[UUID] = Field(default=None, foreign_key="content.directus_files.id")
    uploaded_by: Optional[UUID] = Field(default=None, foreign_key="content.directus_files.id")
    uploaded_on: datetime = Field(default_factory=datetime.utcnow)
    modified_by: Optional[UUID] = Field(default=None, foreign_key="content.directus_files.id")
    modified_on: datetime = Field(default_factory=datetime.utcnow)
    charset: Optional[str] = Field(default=None, max_length=50)
    filesize: Optional[int] = Field(default=None)
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    duration: Optional[int] = Field(default=None)
    embed: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    tags: Optional[str] = Field(default=None)
    directus_metadata: Optional[dict] = Field(sa_column=Column("metadata", JSON, default=None))
    focal_point_x: Optional[int] = Field(default=None)
    focal_point_y: Optional[int] = Field(default=None)


class Banner(SQLModel, table=True):
    __tablename__ = "content_banners"
    __table_args__ = {"schema": "content"}
    id: int = Field(primary_key=True)
    title: str = Field(nullable=False)
    description: Optional[str] = Field(nullable=True)
    button_text: str = Field(nullable=False)
    button_url: str = Field(nullable=False)
    number: int = Field(nullable=True)
    subscript: Optional[str] = Field(nullable=True)
    number_text: Optional[str] = Field(nullable=True)
    desktop_background: UUID = Field(
        default=None, foreign_key="content.directus_files.id", nullable=True
    )
    mobile_background: UUID = Field(
        default=None, foreign_key="content.directus_files.id", nullable=True
    )
    is_active: bool = Field(nullable=False)
    is_prioritized: bool = Field(nullable=True, default=False)


class Config(SQLModel, table=True):
    __tablename__ = "character_configs"
    __table_args__ = {"schema": "content"}

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    public_name: str = Field(nullable=False)
    description: Optional[str] = Field(nullable=True)
    character_id: int = Field(nullable=False, foreign_key="content.content_characters.id")
    config: str = Field(nullable=False)  # storing yaml as plain text
    path: str = Field(nullable=False)
    status: str = Field(default="draft", max_length=255)
    background_file_id: Optional[UUID] = Field(nullable=True, foreign_key="content.directus_files.id")
    style_name: Optional[str] = Field(nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
