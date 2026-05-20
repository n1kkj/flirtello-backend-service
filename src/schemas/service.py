from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from src.schemas.character import Character


class EmailExistingRequest(BaseModel):
    email: str


class EmailExistingResponse(BaseModel):
    exists: bool


class RoleplayConfig(BaseModel):
    id: UUID
    character: Character
    public_name: str
    description: Optional[str]
    background_file_url: Optional[str] = None
    style_name: Optional[str] = None


class RoleplayConfigsResponse(BaseModel):
    configs: List[RoleplayConfig]
