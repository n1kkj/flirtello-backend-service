import os
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from src.db.lib.billing.balance_transactions import (
    transfer_currency_from_balance_to_balance,
)
from src.db.lib.billing.common.content_billing_models import (
    CurrencyType,
    TariffPlan,
    Transaction,
    UserBalance,
    UserPlan,
)
from src.db.lib.billing.common.enums import SourceNames, TopUpWithdrawTransactionTypes
from src.db.lib.content_models import Banner
from src.lib.verifier import TokenData

from ..dependencies import get_current_user, get_session

router = APIRouter(prefix="/dev", tags=["DEV"])


@router.post(
    "/create_user_billing_dependencies/{user_id}",
    deprecated=True,
    description="Для того чтобы биллинг работал, у каждого юзера должны быть соответствующие записи в биллинг таблицах в бд, этот ендпоинт как раз таки для этого - позволяет произвести первоначальную настройку биллинга для конкретного юзера. Пример запроса: /dev/create_user_billing_dependencies/746ddf53-958d-467f-832b-d3f9a2cfed2f",
)
async def create_user_billing_dependencies(
    user_id: UUID,
    session: Session = Depends(get_session),
):
    try:
        user_stats = session.exec(select(UserPlan).where(UserPlan.user_id == user_id)).first()
        if not user_stats:
            tariff_plan_id = session.exec(
                select(TariffPlan).where(TariffPlan.name == "test-trial")
            ).first()
            assert tariff_plan_id
            user_stats = UserPlan(
                user_id=user_id,
                tariff_plan_id=tariff_plan_id.id,
                expired_at=None,
            )

            token_currency_type_id = session.exec(
                select(CurrencyType).where(CurrencyType.name == "TOKEN")
            ).first()
            service_currency_type_id = session.exec(
                select(CurrencyType).where(CurrencyType.name == "SERVICE")
            ).first()
            usd_currency_type_id = session.exec(
                select(CurrencyType).where(CurrencyType.name == "USD")
            ).first()
            assert token_currency_type_id
            assert service_currency_type_id
            assert usd_currency_type_id
            user_token_balance = UserBalance(
                user_id=user_id, currency_type_id=token_currency_type_id.id
            )
            user_service_balance = UserBalance(
                user_id=user_id, currency_type_id=service_currency_type_id.id
            )
            user_usd_balance = UserBalance(user_id=user_id, currency_type_id=usd_currency_type_id.id)

            session.add_all([user_stats, user_token_balance, user_service_balance, user_usd_balance])
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    return {"status": "success"}


@router.patch(
    "/transfer_trial_tokens_to_user/{user_id}",
    description="Этот метод позволит пополнить баланс пользователя на определенное кол-во токенов. Можно вводить любое число: как целое, так и дробное, как положительное, так и отрицательное. Примеры запросов: 'dev/transfer_trial_tokens_to_user/746ddf53-958d-467f-832b-d3f9a2cfed2f?amount=12.3', 'dev/transfer_trial_tokens_to_user/746ddf53-958d-467f-832b-d3f9a2cfed2f?amount=-2.3' ",
)
async def transfer_trial_tokens_to_user(
    user_id: UUID,
    amount: Decimal,
    session: Session = Depends(get_session),
):
    company_trial_token_balance_id = os.environ.get("TRIAL_TOKEN_COMPANY_BALANCE_ID")
    assert company_trial_token_balance_id, "Trial token company balance id is't set"
    company_trial_token_balance_id = int(company_trial_token_balance_id)
    if amount >= 0:
        transfer_currency_from_balance_to_balance(
            session,
            company_trial_token_balance_id,
            user_id,
            amount,
            "TOKEN",
            TopUpWithdrawTransactionTypes,
            None,
            SourceNames.WEB_SITE,
        )
    else:
        transfer_currency_from_balance_to_balance(
            session,
            user_id,
            company_trial_token_balance_id,
            -amount,
            "TOKEN",
            TopUpWithdrawTransactionTypes,
            None,
            SourceNames.WEB_SITE,
        )
    session.commit()
