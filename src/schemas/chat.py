from pydantic import BaseModel

from src.db.lib.chat_models import Message


class StartChatWithCharacterOutputDTO(BaseModel):
    is_new: bool
    channel_id: int
    messages: list[Message]


class GetResponseFromCharacterOutputDTO(BaseModel):
    messages: list[Message]
