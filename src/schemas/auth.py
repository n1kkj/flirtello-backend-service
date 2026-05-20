from typing import Optional

from pydantic import BaseModel


class TelegramUser(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    photo_url: Optional[str] = None


class TelegramAuthRequest(BaseModel):
    init_data: str


class TelegramAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_info: TelegramUser
    language: Optional[str] = None
