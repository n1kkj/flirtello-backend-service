import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, and_, select, text

from .balance_transactions import (
    check_user_have_enough_currency,
    transfer_currency_from_balance_to_balance,
)
from .common.content_billing_models import PaidAction, Transaction, UserPlan
from .common.enums import (
    PurchaseSaleTransactionTypes,
    SourceNames,
    TopUpWithdrawTransactionTypes,
)
from .common.exceptions import TariffPlanExpired


def is_image_paid(session: Session, user_id: uuid.UUID, image_id: uuid.UUID) -> bool:
    stmt = text(
        """
            SELECT 1 
            FROM content.transactions
            WHERE user_id = :req_user_id
            AND additional_data->>'image_id' = :req_image_id
            LIMIT 1
        """
    ).params(req_user_id=user_id, req_image_id=str(image_id))

    result = session.exec(stmt).first()
    return bool(result)


def validate_tariff_plan(session: Session, user_id: uuid.UUID):
    stmt = select(UserPlan).where(UserPlan.user_id == user_id)
    user_stats = session.exec(stmt).first()
    if user_stats.expired_at and user_stats.expired_at < datetime.now(UTC):
        raise TariffPlanExpired(user_stats.expired_at, user_stats.tariff_plan.name)


@dataclass(frozen=True)
class PaidActionDataset:
    price: Decimal
    id: uuid.UUID


def get_paid_action_dataset(session: Session, paid_action_name: str) -> PaidActionDataset:
    stmt = select(PaidAction).where(
        (PaidAction.name == paid_action_name) & (PaidAction.is_archived == False)
    )
    res = session.exec(stmt).first()
    price = res.price
    paid_action_id = res.id
    return PaidActionDataset(price, paid_action_id)


def process_paid_action(
    session: Session,
    user_id: uuid.UUID,
    paid_action_dataset: PaidActionDataset,
    source_name: SourceNames,
    additional_data: dict = None,
):
    """Validation user's current tariff plan,
    get required price for paid action,
    then try to deduct tokens form user balance
    and transfer it to company balance(in one transaction)
    in case of success make 4 traces(in one transaction) to transactions table,
    in case of failure rollback transaction

    IMPORTANT!: consider that this function only execute sql statements into session,
    the responsibility for the commit is assumed by the parent function

    Args:
        session (Session): sqlmodel session
        user_id (uuid.UUID): user id
        paid_action_name (str): paid action name

    Raises:
        e: exception for failure during token transfer
    """
    # TODO check 4.5.d(billing document)
    paid_action_price = paid_action_dataset.price
    paid_action_id = paid_action_dataset.id
    try:
        company_token_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
        company_service_balance_id = os.environ.get("SERVICE_COMPANY_BALANCE_ID")
        assert company_token_balance_id, "Token company balance id is't set"
        assert company_service_balance_id, "Service company balance id is't set"
        company_token_balance_id = int(company_token_balance_id)
        company_service_balance_id = int(company_service_balance_id)
        transfer_currency_from_balance_to_balance(
            session,
            user_id,
            company_token_balance_id,
            paid_action_price,
            "TOKEN",
            TopUpWithdrawTransactionTypes,
            paid_action_id,
            source_name,
            additional_data,
        )
        transfer_currency_from_balance_to_balance(
            session,
            company_service_balance_id,
            user_id,
            1,
            "SERVICE",
            PurchaseSaleTransactionTypes,
            paid_action_id,
            source_name,
            additional_data,
        )
    except SQLAlchemyError as e:
        session.rollback()
        raise e
