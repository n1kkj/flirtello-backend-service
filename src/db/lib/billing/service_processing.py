import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, and_, select, text, update

from .balance_transactions import (
    check_user_have_enough_currency,
    transfer_currency_from_balance_to_balance,
)
from .clearing.clearing import create_token_batch
from .common.content_billing_models import (
    BaseService,
    PaidAction,
    TariffPlan,
    TokenBatch,
    TokenPack,
    Transaction,
    UserPlan,
)
from .common.enums import (
    PurchaseSaleTransactionTypes,
    ServiceTypes,
    SourceNames,
    TopUpWithdrawTransactionTypes,
)
from .common.exceptions import NoSuchServiceError, TariffPlanExpired
from .invoicing import ServiceDataset


@dataclass(eq=False, repr=False)
class ServiceProcessor(ABC):
    session: Session
    user_id: uuid.UUID
    service_dataset: ServiceDataset
    source_name: SourceNames

    def __post_init__(self):
        self.service = self._get_service_model(self.service_dataset.service_id)

    @abstractmethod
    def sell_service(self, payment_system_balance_id: int, additional_data: dict = None):
        pass

    @abstractmethod
    def apply_service(self):
        pass

    @abstractmethod
    def _get_service_model(self, service_id: uuid.UUID) -> BaseService:
        pass

    def _make_initial_charges(
        self,
        payment_system_balance_id: int,
        additional_data: dict = None,
    ):
        # TODO not flexible if currency have changed ex. from eur to usd, maybe select this balance id...
        eur_company_balance_id = os.environ.get("EUR_COMPANY_BALANCE_ID")
        assert eur_company_balance_id, "Eur company balance id is't set"
        eur_company_balance_id = int(eur_company_balance_id)

        transfer_currency_from_balance_to_balance(
            session=self.session,
            balance_from=payment_system_balance_id,
            balance_to=self.user_id,
            amount=self.service.price,
            currency_type=self.service.currency_type.name,
            transactions_type=TopUpWithdrawTransactionTypes,
            service_id=self.service.id,
            source_name=self.source_name,
            additional_data=additional_data,
        )
        transfer_currency_from_balance_to_balance(
            session=self.session,
            balance_from=self.user_id,
            balance_to=eur_company_balance_id,
            amount=self.service.price,
            currency_type=self.service.currency_type.name,
            transactions_type=TopUpWithdrawTransactionTypes,
            service_id=self.service.id,
            source_name=self.source_name,
            additional_data=additional_data,
        )


@dataclass(eq=False, repr=False)
class TariffPlanProcessor(ServiceProcessor):
    def sell_service(
        self,
        payment_system_balance_id: int,
        additional_data: dict = None,
    ):
        self._make_initial_charges(payment_system_balance_id, additional_data)

        company_service_balance_id = os.environ.get("SERVICE_COMPANY_BALANCE_ID")
        assert company_service_balance_id, "Service company balance id is't set"
        company_service_balance_id = int(company_service_balance_id)

        transfer_currency_from_balance_to_balance(
            session=self.session,
            balance_from=company_service_balance_id,
            balance_to=self.user_id,
            amount=1,
            currency_type="SERVICE",
            transactions_type=PurchaseSaleTransactionTypes,
            service_id=self.service.id,
            source_name=self.source_name,
            additional_data=additional_data,
        )

    def apply_service(self) -> bool:
        expiration_date = datetime.now(UTC)
        expiration_date += relativedelta(months=self.service.duration_in_month)
        stmt = select(UserPlan).where(UserPlan.user_id == self.user_id)
        user_plan = self.session.exec(stmt).first()

        is_origin_tariff_plan_trial = user_plan.tariff_plan.is_trial
        user_plan.tariff_plan_id = self.service.id

        user_plan.expired_at = expiration_date

        self.session.add(user_plan)
        return is_origin_tariff_plan_trial

    def _get_service_model(self, service_id: uuid.UUID) -> BaseService:
        stmt = select(TariffPlan).where(
            (TariffPlan.id == service_id) & (TariffPlan.is_trial == False)
        )
        res = self.session.exec(stmt).first()
        if not res:
            raise NoSuchServiceError(service_id, ServiceTypes.TARIFF_PLAN.value)
        return res


@dataclass(eq=False, repr=False)
class TokenPackProcessor(ServiceProcessor):
    def sell_service(
        self,
        payment_system_balance_id: int,
        additional_data: dict = None,
    ):
        self._make_initial_charges(payment_system_balance_id, additional_data)

        company_token_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
        assert company_token_balance_id, "Token company balance id is't set"
        company_token_balance_id = int(company_token_balance_id)

        transfer_currency_from_balance_to_balance(
            session=self.session,
            balance_from=company_token_balance_id,
            balance_to=self.user_id,
            amount=self.service.amount,
            currency_type="TOKEN",
            transactions_type=TopUpWithdrawTransactionTypes,
            service_id=self.service.id,
            source_name=self.source_name,
            additional_data=additional_data,
        )

    def apply_service(self):
        expiration_date = datetime.now(UTC) + relativedelta(years=1)
        create_token_batch(
            session=self.session,
            user_id=self.user_id,
            tokens_amount=self.service.amount,
            expiration_date=expiration_date,
        )

    def _get_service_model(self, service_id: uuid.UUID) -> BaseService:
        stmt = select(TokenPack).where((TokenPack.id == service_id))
        res = self.session.exec(stmt).first()
        if not res:
            raise NoSuchServiceError(service_id, ServiceTypes.TOKEN_PACK.value)
        return res
