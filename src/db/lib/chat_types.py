from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .chat_models import Message
from .content_models import ImageInfo


class MessageType(Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"


@dataclass(frozen=True)
class MessageDTO:
    message_type: MessageType
    message: Message
    message_image: Optional[ImageInfo] = None
