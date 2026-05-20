from typing import Optional
from urllib.parse import urljoin
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from src.db.lib.content_models import ImageInfo
from src.lib.config import config
from src.lib.images import get_images_data
from src.routers.images import ImagesDataResponse


class Character(BaseModel):
    id: int
    status: str
    sort: Optional[int]
    name: str
    public_description: Optional[str]
    traits: list[str]
    filters: list[str]
    locations: list[str]
    main_photo: Optional[str]
    profile_images_ids: list[ImagesDataResponse] | list[UUID]
    tags: list[dict[str, str]]
    caption: Optional[str]
    video_preview: Optional[str]
    onboarding_message: Optional[str]
    background_image: Optional[str]

    @field_validator("main_photo", mode="before")
    @classmethod
    def resolve_main_photo_path(cls, value: Optional[str]):
        if not value:
            return None
        main_photo_path = urljoin(config.storage_root, value)
        return main_photo_path

    @field_validator("video_preview", mode="before")
    @classmethod
    def resolve_video_preview_path(cls, value: Optional[str]):
        if not value:
            return None
        video_preview_path = urljoin(config.storage_root, value)
        return video_preview_path

    model_config = ConfigDict(extra="ignore")

    @field_validator("background_image", mode="before")
    @classmethod
    def resolve_background_image_path(cls, value: Optional[str]):
        if not value:
            return None
        background_image_path = urljoin(config.storage_root, value)
        return background_image_path
