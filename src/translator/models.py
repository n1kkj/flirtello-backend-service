from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Translation(SQLModel, table=True):
    __tablename__ = "translations"
    __table_args__ = {"schema": "translator"}

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True)
    translated_text_hash: Optional[str] = Field(default=None, index=True)
    language: str = Field(index=True)
    source_text: str
    translated_text: str
    is_verified_by_human: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
