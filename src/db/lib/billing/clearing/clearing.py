import logging
import os
from datetime import UTC, datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlmodel import Session, insert, select, text, update

from ..balance_transactions import transfer_currency_from_balance_to_balance
from ..common.content_billing_models import (
    Clearing,
    CurrencyType,
    TariffPlan,
    TokenBatch,
    UserBalance,
    UserPlan,
)
from ..common.enums import CurrenciesTypes, SourceNames, TopUpWithdrawTransactionTypes
from ..common.exceptions import UnableProcessClearingWithTrialTariffPlan

logger = logging.getLogger(__name__)


def mark_user_plan_as_paid(session: Session, user_id: UUID):
    stmt = update(UserPlan).where(UserPlan.user_id == user_id).values(is_paid=True)
    session.exec(stmt)


def create_token_batch(session, user_id: UUID, tokens_amount: Decimal, expiration_date: datetime):
    token_batch = TokenBatch(
        user_plans_id=user_id,
        token_amount=tokens_amount,
        expiration_date=expiration_date,
    )
    session.add(token_batch)


def get_user_plans_count(session: Session) -> int:
    stmt = text("SELECT COUNT(*) FROM content.user_plans")
    return session.exec(stmt).one()


def instant_tariff_plan_debit(
    session: Session,
    user_id: UUID,
    is_origin_tariff_plan_trial: bool,
    source_name: SourceNames,
    additional_data: dict = None,
) -> datetime:
    stmt = select(UserPlan).where(UserPlan.user_id == user_id)
    user_plan = session.exec(stmt).first()
    tokens_amount = user_plan.tariff_plan.tokens_per_month
    currency_type_name = "TOKEN"
    service_id = user_plan.tariff_plan.id
    tariff_plan_duration = user_plan.tariff_plan.duration_in_month

    company_trial_token_balance_id = os.environ.get("TRIAL_TOKEN_COMPANY_BALANCE_ID")
    assert company_trial_token_balance_id, "Trial token company balance id is't set"
    company_trial_token_balance_id = int(company_trial_token_balance_id)
    stmt = (
        select(UserBalance)
        .where(
            UserBalance.user_id == user_id,
            UserBalance.balance_type.has(CurrencyType.name == currency_type_name),
        )
        .with_for_update()
    )
    user_token_balance = session.exec(stmt).first()
    if is_origin_tariff_plan_trial and user_token_balance.balance_amount > 0:
        transfer_currency_from_balance_to_balance(
            session=session,
            balance_from=user_id,
            balance_to=company_trial_token_balance_id,
            amount=user_token_balance.balance_amount,
            currency_type=currency_type_name,
            transactions_type=TopUpWithdrawTransactionTypes,
            service_id=None,
            source_name=source_name,
            additional_data=additional_data,
        )

    company_token_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
    assert company_token_balance_id, "Token company balance id is't set"
    company_token_balance_id = int(company_token_balance_id)
    transfer_currency_from_balance_to_balance(
        session=session,
        balance_from=company_token_balance_id,
        balance_to=user_id,
        amount=tokens_amount,
        currency_type=currency_type_name,
        transactions_type=TopUpWithdrawTransactionTypes,
        service_id=service_id,
        source_name=source_name,
        additional_data=additional_data,
    )

    expiration_date = datetime.now(UTC) + relativedelta(months=tariff_plan_duration)
    # TODO is paid
    stmt = update(UserPlan).values(is_paid=False)
    session.exec(stmt)
    create_token_batch(session, user_id, tokens_amount, expiration_date=expiration_date)
    return expiration_date


def process_expired_token_batches_clearing(
    session: Session,
    user_plan: UserPlan,
    additional_data: dict = None,
    clearing_id: int | None = None,
):
    user_id = user_plan.user_id
    token_batches = user_plan.token_batches
    batches_summary_tokens_amount = Decimal(sum([amount.token_amount for amount in token_batches]))

    logger.info(
        f"Processing expired token batches for user {user_id}, total batches amount: {batches_summary_tokens_amount}"
    )

    stmt = (
        select(UserBalance)
        .where(
            UserBalance.user_id == user_id,
            UserBalance.balance_type.has(CurrencyType.name == CurrenciesTypes.TOKEN.value),
        )
        .with_for_update()
    )
    user_tokens_amount = session.exec(stmt).first().balance_amount

    for batch in token_batches:
        # Check if the batch was expired
        if batch.expiration_date <= datetime.now(UTC):
            left_butch_tokens_amount = 0
            # Check if the user have the rest of expired batch at balance
            if batches_summary_tokens_amount - batch.token_amount <= user_tokens_amount:
                left_butch_tokens_amount = batch.token_amount - (
                    batches_summary_tokens_amount - user_tokens_amount
                )

                user_tokens_amount -= left_butch_tokens_amount
                batches_summary_tokens_amount -= batch.token_amount

                logger.info(
                    f"Expired batch found for user {user_id}: remaining tokens {left_butch_tokens_amount}, "
                    f"expiration date: {batch.expiration_date}"
                )

            # Transfer rest of token batch to expired tokens company balance
            company_expired_token_balance_id = os.environ.get("EXPIRED_TOKEN_COMPANY_BALANCE_ID")
            assert company_expired_token_balance_id, "Expired token company balance id is't set"
            company_expired_token_balance_id = int(company_expired_token_balance_id)
            transfer_currency_from_balance_to_balance(
                session,
                user_id,
                company_expired_token_balance_id,
                left_butch_tokens_amount,
                "TOKEN",
                TopUpWithdrawTransactionTypes,
                None,
                None,
                additional_data,
                clearing_id=clearing_id,
            )

            session.delete(batch)


def process_tariff_plan_debit(
    session: Session,
    user_plan: UserPlan,
    additional_data: dict = None,
    clearing_id: int | None = None,
):
    is_paid = user_plan.is_paid
    if not is_paid:
        return

    tokens_amount = user_plan.tariff_plan.tokens_per_month
    currency_type_name = "TOKEN"
    service_id = user_plan.tariff_plan.id
    tariff_plan_expiration_date = user_plan.expired_at
    user_id = user_plan.user_id

    logger.info(
        f"Processing tariff plan debit for user {user_id}: tokens amount {tokens_amount}, "
        f"current expiration date: {tariff_plan_expiration_date}"
    )

    company_token_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
    assert company_token_balance_id, "Token company balance id is't set"
    company_token_balance_id = int(company_token_balance_id)
    transfer_currency_from_balance_to_balance(
        session=session,
        balance_from=company_token_balance_id,
        balance_to=user_id,
        amount=tokens_amount,
        currency_type=currency_type_name,
        transactions_type=TopUpWithdrawTransactionTypes,
        service_id=service_id,
        source_name=None,
        additional_data=additional_data,
        clearing_id=clearing_id,
    )

    new_expiration_date = tariff_plan_expiration_date + relativedelta(
        months=user_plan.tariff_plan.duration_in_month
    )

    # TODO IMPORTANT! is_paid need to be false after debiting
    # TODO try get money from payment system if success set is_paid to True otherwise False
    stmt = update(UserPlan).values(expired_at=new_expiration_date, is_paid=False)
    session.exec(stmt)
    logger.info(
        f"Tariff plan debit processed for user {user_id}: new expiration date {new_expiration_date}"
    )
    create_token_batch(session, user_id, tokens_amount, expiration_date=new_expiration_date)
    logger.info(
        f"Token batch created for user {user_id}: tokens amount {tokens_amount}, "
        f"expiration date: {new_expiration_date}"
    )


def stream_user_plans(session: Session, chunk_size=2**22):
    # TODO may be filter up if up have token batches instead check is_trial
    stmt = (
        select(UserPlan)
        .where(
            ((UserPlan.expired_at <= datetime.now(UTC)) & (UserPlan.is_paid == True))
            | (UserPlan.token_batches.any(TokenBatch.expiration_date <= datetime.now(UTC)))
        )
        .with_for_update()
    )
    result = session.exec(stmt).yield_per(chunk_size)
    for user_plan in result:
        yield user_plan


def process_clearing(session: Session):
    logger.info("Starting clearing process")
    with session.begin():
        stmt = insert(Clearing).values(created_at=datetime.now(UTC)).returning(Clearing.id)
        clearing_id: int = session.exec(stmt).scalar_one()

        processed_plans = 0
        for user_plan in stream_user_plans(session):
            process_expired_token_batches_clearing(session, user_plan, clearing_id=clearing_id)
            process_tariff_plan_debit(session, user_plan, clearing_id=clearing_id)
            processed_plans += 1

            if processed_plans % 10 == 0:  # Log progress every 100 plans
                logger.info(f"Processed {processed_plans} user plans in current clearing batch")

        logger.info(f"Clearing process completed. Total plans processed: {processed_plans}")
