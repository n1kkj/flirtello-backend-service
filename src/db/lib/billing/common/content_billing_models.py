from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from pydantic import Json
from sqlalchemy import ARRAY, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlmodel import Field, Relationship, SQLModel

from ..payment_system.enums import PaymentSystems
from .enums import InvoiceStatus, ServiceTypes, SourceNames, TransactionTypes


class UserPlan(SQLModel, table=True):
    __tablename__ = "user_plans"
    __table_args__ = {"schema": "content"}
    user_id: UUID = Field(primary_key=True, default_factory=uuid4)
    expired_at: Optional[datetime] = Field(nullable=True, default=None)
    tariff_plan_id: UUID = Field(foreign_key="content.tariff_plans.id", nullable=False)
    next_top_up: Optional[datetime] = Field(nullable=True, default=None)
    is_paid: Optional[bool] = Field(default=None, nullable=True)
    truevo_subscription_id: Optional[str] = Field(nullable=True)
    truevo_token_id: Optional[str] = Field(nullable=True)
    token_batches: Optional[list["TokenBatch"]] = Relationship(
        sa_relationship_kwargs={
            "order_by": "TokenBatch.expiration_date",
            "uselist": True,
        }
    )
    tariff_plan: "TariffPlan" = Relationship(sa_relationship_kwargs={"uselist": False})


class TokenBatch(SQLModel, table=True):
    __tablename__ = "token_batches"
    __table_args__ = {"schema": "content"}
    id: int = Field(primary_key=True)
    token_amount: Decimal = Field(nullable=False)
    expiration_date: Optional[datetime] = Field(nullable=True, default=None)
    user_plans_id: Optional[UUID] = Field(foreign_key="content.user_plans.user_id", nullable=True)


class UserBalance(SQLModel, table=True):
    __tablename__ = "balances"
    __table_args__ = {"schema": "content"}
    id: int = Field(primary_key=True)
    user_id: Optional[UUID] = Field(nullable=True)
    currency_type_id: Optional[int] = Field(foreign_key="content.currency_types.id", nullable=True)
    balance_amount: Decimal = Field(default=Decimal(0), nullable=True)
    is_official: bool = Field(nullable=False, default=False)

    balance_type: "CurrencyType" = Relationship(sa_relationship_kwargs={"uselist": False})


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    __table_args__ = {"schema": "content"}
    id: UUID = Field(primary_key=True, default_factory=uuid4)
    user_id: UUID = Field(nullable=True)
    balance_id_from: int = Field(nullable=False)
    balance_id_to: int = Field(nullable=False)
    transaction_type: str = Field(nullable=False)
    service_id: Optional[UUID] = Field(nullable=True)
    amount: Decimal = Field(nullable=True)
    source_name: SourceNames = Field(nullable=False)
    additional_data: Json = Field(sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    correlation_id: Optional[UUID] = Field(nullable=True)
    clearing_id: Optional[int] = Field(nullable=True, foreign_key="content.clearings.id")


# Abstract Base Class
class BaseService(SQLModel, table=False):
    id: UUID = Field(primary_key=True, default_factory=uuid4)
    name: str = Field(nullable=False)
    currency_type_id: Optional[int] = Field(foreign_key="content.currency_types.id", nullable=True)
    price: Optional[Decimal] = Field(nullable=True)
    is_archived: bool = Field(default=False, nullable=False)


class TariffPlan(BaseService, table=True):
    __tablename__ = "tariff_plans"
    __table_args__ = {"schema": "content"}
    tokens_per_month: Decimal = Field(nullable=True)
    duration_in_month: Optional[int] = Field(nullable=True)
    tariff_info: Optional[str] = Field(nullable=True)
    internal_name: Optional[str] = Field(nullable=True)
    is_trial: bool = Field(default=False, nullable=False)
    order: Optional[int] = Field(nullable=True)
    is_highlighted: Optional[bool] = Field(nullable=True)
    payment_system_plan_id: Optional[str] = Field(nullable=True)

    currency_type: Optional["CurrencyType"] = Relationship(sa_relationship_kwargs={"uselist": False})


class TokenPack(BaseService, table=True):
    __tablename__ = "token_packs"
    __table_args__ = {"schema": "content"}
    amount: Decimal = Field(nullable=True)
    order: Optional[int] = Field(nullable=True)
    is_highlighted: Optional[bool] = Field(nullable=True, default=False)

    currency_type: Optional["CurrencyType"] = Relationship(sa_relationship_kwargs={"uselist": False})


class PaidAction(SQLModel, table=True):
    __tablename__ = "paid_actions"
    __table_args__ = {"schema": "content"}
    id: UUID = Field(primary_key=True, default_factory=uuid4)
    name: str = Field(nullable=False)
    price: Decimal = Field(nullable=False)
    description: Optional[str] = Field(nullable=True)
    is_archived: bool = Field(default=False, nullable=False)
    is_public: bool = Field(default=False, nullable=False)


class CurrencyType(SQLModel, table=True):
    __tablename__ = "currency_types"
    __table_args__ = {"schema": "content"}
    id: int = Field(primary_key=True)
    name: str = Field(nullable=False, unique=True)


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"
    __table_args__ = {"schema": "content"}
    id: int = Field(primary_key=True)
    customer_id: Optional[UUID] = Field(foreign_key="public.user.id", nullable=True)
    service_id: UUID = Field(nullable=False)
    service_type: ServiceTypes = Field(nullable=False)
    total: Decimal = Field(nullable=False)
    currency_type_id: Optional[int] = Field(foreign_key="content.currency_types.id", nullable=True)
    status: InvoiceStatus = Field(nullable=False)
    callback_url: str = Field(nullable=False)
    payment_system_transaction_id: Optional[str] = Field(nullable=True)
    payment_system_name: Optional[PaymentSystems] = Field(nullable=True)


class Clearing(SQLModel, table=True):
    __tablename__ = "clearings"
    __table_args__ = {"schema": "content"}
    id: int = Field(primary_key=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class ContentWebhookData(SQLModel, table=True):
    __tablename__ = "content_webhook_data"
    __table_args__ = {"schema": "content"}
    id: int = Field(primary_key=True)
    payment_system_name: Optional[str] = Field(nullable=True)
    data: dict = Field(default=None, sa_column=Column(JSONB, nullable=False))
    is_handled: bool = Field(nullable=False)
    status: Optional[str] = Field(nullable=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
