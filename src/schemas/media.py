from typing import Optional

from pydantic import BaseModel

from src.routers.images import ImagesDataResponse


class MediaResponse(BaseModel):
    attachments: Optional[list[ImagesDataResponse]]
