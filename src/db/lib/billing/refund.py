"""
1. Match payment system transaction id with transaction id at billing
2. Match service id and get tariff plan or token pack
3. If token pack: 
    transactions: 
        - deduct tokens from user balance to company balance
        - move usd from company balance to payment system balance
        - move usd from payment system balance to user balance
4. If tariff plan: 
    transactions: 
        - deduct 1 service unit from user service balance
        - deduct tokens from user balance to company balance
        - move usd from company balance to payment system balance
        - move usd from payment system balance to user balance
    transfer user to trial tariff plan and set expired_at to None
"""

import os
import uuid
from logging import getLogger
from typing import Optional

from sqlmodel import Session, select, update

from ..config import config
from .balance_transactions import transfer_currency_from_balance_to_balance
from .common.content_billing_models import TariffPlan, TokenPack, Transaction, UserPlan
from .common.enums import PurchaseSaleTransactionTypes, TopUpWithdrawTransactionTypes

logger = getLogger(__name__)


def process_refund(
    session: Session,
    user_id: uuid.UUID,
    payment_system_transaction_id: str,
    payment_system_balance_id: int,
):
    billing_transaction = find_billing_transaction_from_payment_system_transaction_id(
        session, payment_system_transaction_id
    )
    logger.info(f"Billing transaction: {billing_transaction}")
    if billing_transaction is None:
        raise ValueError("Billing transaction not found")
    service = get_service(session, billing_transaction.service_id)
    logger.info(f"Service: {service}")
    make_initial_debits(
        session=session,
        user_id=user_id,
        service=service,
        payment_system_balance_id=payment_system_balance_id,
        additional_data={
            "payment_system_transaction_id": payment_system_transaction_id,
            "refund": True,
        },
    )
    logger.info(f"Initial debits completed")
    if isinstance(service, TariffPlan):
        make_tariff_plan_refund_debits(
            session=session,
            user_id=user_id,
            service=service,
            additional_data={
                "payment_system_transaction_id": payment_system_transaction_id,
                "refund": True,
            },
        )
        refund_tariff_plan(session=session, user_id=user_id)
    elif isinstance(service, TokenPack):
        make_token_pack_refund_debits(
            session=session,
            user_id=user_id,
            service=service,
            additional_data={
                "payment_system_transaction_id": payment_system_transaction_id,
                "refund": True,
            },
        )
    else:
        raise ValueError("Service not found")


def find_billing_transaction_from_payment_system_transaction_id(
    session: Session, payment_system_transaction_id: str
) -> Optional[Transaction]:
    stmt = select(Transaction).where(
        Transaction.additional_data["payment_system_transaction_id"].astext
        == payment_system_transaction_id
    )
    return session.exec(stmt).first()


def get_service(session: Session, service_id: uuid.UUID) -> Optional[TariffPlan | TokenPack]:
    stmt = select(TariffPlan).where(TariffPlan.id == service_id)
    tariff_plan = session.exec(stmt).first()
    if tariff_plan:
        return tariff_plan
    stmt = select(TokenPack).where(TokenPack.id == service_id)
    token_pack = session.exec(stmt).first()
    return token_pack


def make_initial_debits(
    session: Session,
    payment_system_balance_id: int,
    user_id: uuid.UUID,
    service: TariffPlan | TokenPack,
    additional_data: dict = None,
):
    # TODO not flexible if currency have changed ex. from eur to usd, maybe select this balance id...
    eur_company_balance_id = os.environ.get("EUR_COMPANY_BALANCE_ID")
    assert eur_company_balance_id, "Eur company balance id is't set"
    eur_company_balance_id = int(eur_company_balance_id)

    transfer_currency_from_balance_to_balance(
        session=session,
        balance_from=eur_company_balance_id,
        balance_to=user_id,
        amount=service.price,
        currency_type=service.currency_type.name,
        transactions_type=TopUpWithdrawTransactionTypes,
        service_id=service.id,
        source_name=None,
        additional_data=additional_data,
    )
    transfer_currency_from_balance_to_balance(
        session=session,
        balance_from=user_id,
        balance_to=payment_system_balance_id,
        amount=service.price,
        currency_type=service.currency_type.name,
        transactions_type=TopUpWithdrawTransactionTypes,
        service_id=service.id,
        source_name=None,
        additional_data=additional_data,
    )


def make_tariff_plan_refund_debits(
    session: Session,
    user_id: uuid.UUID,
    service: TariffPlan,
    additional_data: dict = None,
):
    company_service_balance_id = os.environ.get("SERVICE_COMPANY_BALANCE_ID")
    assert company_service_balance_id, "Service company balance id is't set"
    company_service_balance_id = int(company_service_balance_id)
    transfer_currency_from_balance_to_balance(
        session=session,
        balance_from=user_id,
        balance_to=company_service_balance_id,
        amount=1,
        currency_type="SERVICE",
        transactions_type=PurchaseSaleTransactionTypes,
        service_id=service.id,
        source_name=None,
        additional_data=additional_data,
    )
    company_token_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
    assert company_token_balance_id, "Token company balance id is't set"
    company_token_balance_id = int(company_token_balance_id)
    transfer_currency_from_balance_to_balance(
        session=session,
        balance_from=user_id,
        balance_to=company_token_balance_id,
        amount=service.tokens_per_month,
        currency_type="TOKEN",
        transactions_type=TopUpWithdrawTransactionTypes,
        service_id=service.id,
        source_name=None,
        additional_data=additional_data,
    )


def make_token_pack_refund_debits(
    session: Session,
    user_id: uuid.UUID,
    service: TokenPack,
    additional_data: dict = None,
):
    company_token_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
    assert company_token_balance_id, "Token company balance id is't set"
    company_token_balance_id = int(company_token_balance_id)
    transfer_currency_from_balance_to_balance(
        session=session,
        balance_from=user_id,
        balance_to=company_token_balance_id,
        amount=service.amount,
        currency_type="TOKEN",
        transactions_type=TopUpWithdrawTransactionTypes,
        service_id=service.id,
        source_name=None,
        additional_data=additional_data,
    )


def refund_tariff_plan(session: Session, user_id: uuid.UUID):
    stmt = select(TariffPlan).where(TariffPlan.is_trial == True, TariffPlan.is_archived == False)
    trial_tariff_plan = session.exec(stmt).first()
    if trial_tariff_plan is None:
        raise ValueError("Trial tariff plan not found")
    stmt = (
        update(UserPlan)
        .where(UserPlan.user_id == user_id)
        .values(tariff_plan_id=trial_tariff_plan.id, expired_at=None)
    )
    session.exec(stmt)
