from typing import List, Optional, Type
from uuid import UUID

from pydantic import BaseModel

from src.db.lib.chat_models import Message


class SendChatMessageInputDTO(BaseModel):
    message: str
    config_id: Optional[UUID] = None


class Attachment(BaseModel):
    type: str
    id: UUID


class SendChatMessageOutputSubDTO(BaseModel):
    message: str
    attachments: Optional[List[Attachment]] = None
    message_type: Optional[str] = None
    insufficient_balance: bool = False

    @classmethod
    def from_attachment(cls, message) -> "SendChatMessageOutputSubDTO":
        # Поддерживаем как Message объекты, так и DetachedMessageDTO
        # Оба имеют одинаковые атрибуты text, attachments, message_type
        return cls(
            message=message.text if message.text else "",
            attachments=[
                Attachment(type=attachment["type"], id=attachment["id"])
                for attachment in message.attachments
            ] if message.attachments else None,
            message_type=message.message_type
        )


class SendChatMessageOutputDTO(BaseModel):
    messages: list[SendChatMessageOutputSubDTO]
    error: Optional[Type[Exception]] = None

    @classmethod
    def from_single_text_message(cls, message: str) -> "SendChatMessageOutputDTO":
        return cls(messages=[SendChatMessageOutputSubDTO(message=message)])
    


class StartNewChatOutputDTO(SendChatMessageOutputDTO):
    pass


class IllustrationOutputDTO(SendChatMessageOutputDTO):
    @classmethod
    def from_single_text_message(cls, message: str) -> "IllustrationOutputDTO":
        return cls(messages=[SendChatMessageOutputSubDTO(message=message)])