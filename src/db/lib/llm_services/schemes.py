from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ImageCaptionResponse(BaseModel):
    caption: Optional[str]


class ContextImageResponseStatus(str, Enum):
    NO_REQUEST = "no_request"
    NOT_FOUND = "not_found"
    FOUND = "found"


class ContextImageResponse(BaseModel):
    status: ContextImageResponseStatus
    image_id: Optional[UUID] = None
    context: Optional[dict] = None


class GuardrailResponseTypes(Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FORMATTED = "FORMATTED"


class GuardrailResponse(BaseModel):
    response_type: GuardrailResponseTypes
    formatted_message: Optional[str] = None
