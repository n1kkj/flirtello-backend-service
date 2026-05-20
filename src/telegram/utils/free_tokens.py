from __future__ import annotations

import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.db.lib.billing.common.content_billing_models import (
    CurrencyType,
    TokenBatch,
    UserBalance,
)
from src.db.lib.billing.common.enums import CurrenciesTypes


async def get_user_current_token_balance(session: AsyncSession, user_id: UUID) -> Decimal:
    result = await session.execute(
        select(UserBalance).where(
            (UserBalance.user_id == user_id)
            & (UserBalance.balance_type.has(CurrencyType.name == CurrenciesTypes.TOKEN.value))
        )
    )
    user_balance = result.scalars().first()
    return user_balance.balance_amount if user_balance else Decimal(0)


async def should_give_free_tokens(session: AsyncSession, user_id: UUID) -> bool:
    user_current_token_balance = await get_user_current_token_balance(session, user_id)
    return user_current_token_balance < 3


async def give_user_free_tokens(session: AsyncSession, user_id: UUID, amount: Decimal):
    try:
        result = await session.execute(
            select(UserBalance)
            .where(
                (UserBalance.user_id == user_id)
                & (UserBalance.balance_type.has(CurrencyType.name == CurrenciesTypes.TOKEN.value))
            )
            .with_for_update()
        )
        user_balance = result.scalars().first()

        if user_balance:
            token_batch = TokenBatch(
                token_amount=amount,
                expiration_date=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=10),
                user_plans_id=user_id,
            )
            user_balance.balance_amount += amount
            session.add(user_balance)
            session.add(token_batch)
        # Note: What to do if user_balance is None? Should we create one?
        # The original logic didn't handle this. For now, we'll just commit what we have.

    except Exception as e:
        await session.rollback()
        raise e
    else:
        await session.commit()
