from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class GiftCodeUserLink(SQLModel, table=True):
    """Junction table for many-to-many relationship between gift codes and users"""

    __tablename__ = "gift_codes_users"
    __table_args__ = {"schema": "content"}
    gift_code_id: Optional[UUID] = Field(
        default=None, foreign_key="content.gift_codes.id", primary_key=True
    )
    user_id: Optional[UUID] = Field(default=None, foreign_key="public.users.id", primary_key=True)
    activated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class GiftCode(SQLModel, table=True):
    __tablename__ = "gift_codes"
    __table_args__ = {"schema": "content"}

    id: Optional[UUID] = Field(default=None, primary_key=True)
    code: str = Field(unique=True)
    token_amount: int
    code_type: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    tokens_lifetime_hours: int = Field(default=48)
