import logging
import os
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select, update

from src.telegram.dependecies import engine as sync_engine

from .common.content_billing_models import CurrencyType, UserBalance
from .common.enums import SourceNames, TopUpWithdrawTransactionTypes, TransactionTypes
from .common.exceptions import NotEnoughCurrencyError
from .transactions_tracing import trace_transactions

logger = logging.getLogger(__name__)


def transfer_currency_from_balance_to_balance(
    session: Session,
    balance_from: int | uuid.UUID,
    balance_to: int | uuid.UUID,
    amount: Decimal,
    currency_type: str,
    transactions_type: TransactionTypes,
    service_id: uuid.UUID | None,
    source_name: SourceNames | None,
    additional_data: dict = None,
    clearing_id: int | None = None,
):
    """Withdrawal transactions firstly, top-up secondly. Balance from is always get withdrawals, balance to always get top-up

    Args:
        session (Session): _description_
        balance_from (int | uuid.UUID): _description_
        balance_to (int | uuid.UUID): _description_
        amount (Decimal): _description_
        currency_type (str): # TODO why not enum
        transactions_type (TransactionTypes): _description_
        service_id (uuid.UUID | None): _description_
        source_name (SourceNames): _description_
        additional_data (dict, optional): _description_. Defaults to None.
    """

    from_condition_attr = get_condition_attr(balance_from)
    to_condition_attr = get_condition_attr(balance_to)
    if isinstance(balance_from, uuid.UUID):
        user_id = balance_from
    else:
        user_id = balance_to

    debiting_transaction = (
        update(UserBalance)
        .where(
            (from_condition_attr == balance_from)
            & (UserBalance.balance_type.has(CurrencyType.name == currency_type))
        )
        .values(balance_amount=UserBalance.balance_amount - amount)
        .returning(UserBalance.id)
    )
    replenishment_transaction = (
        update(UserBalance)
        .where(
            (to_condition_attr == balance_to)
            & (UserBalance.balance_type.has(CurrencyType.name == currency_type))
        )
        .values(balance_amount=UserBalance.balance_amount + amount)
        .returning(UserBalance.id)
    )
    balance_from_id = session.exec(debiting_transaction).scalar_one()
    balance_to_id = session.exec(replenishment_transaction).scalar_one()
    trace_transactions(
        session,
        user_id,
        balance_from_id,
        balance_to_id,
        transaction_type=transactions_type,
        amount=amount,
        source_name=source_name,
        service_id=service_id,
        additional_data=additional_data,
        clearing_id=clearing_id,
    )


def check_user_have_enough_currency(
    session: Session,
    user_id: uuid.UUID,
    amount: Decimal,
    currency_type: str,
) -> None:

    user_balance = session.exec(
        select(UserBalance)
        .where(
            (UserBalance.user_id == user_id)
            & (UserBalance.balance_type.has(CurrencyType.name == currency_type))
        )
    ).first()
    user_currency_amount = user_balance.balance_amount
    if user_currency_amount < amount:
        session.rollback()
        raise NotEnoughCurrencyError(user_currency_amount, amount)


def get_condition_attr(balance_identifier: int | uuid.UUID) -> int | uuid.UUID | None:
    if isinstance(balance_identifier, int):
        return UserBalance.id
    elif isinstance(balance_identifier, uuid.UUID):
        return UserBalance.user_id
    raise ValueError("Invalid balance identifier type")


async def async_get_transactions_by_balance_id(
    session: AsyncSession,
    balance_id: int,
    user_id: uuid.UUID,
    limit: int = 20,
) -> list:
    """
    Получает последние транзакции для указанного баланса с фильтрацией пар.
    
    Согласно семантической модели, транзакции создаются парами через trace_transactions.
    Каждая транзакция имеет correlation_id, указывающий на ID парной транзакции.
    Эта функция фильтрует пары и возвращает только одну транзакцию из каждой пары,
    выбирая правильную транзакцию с точки зрения пользователя.
    
    Args:
        session: Async database session
        balance_id: ID баланса пользователя
        user_id: ID пользователя (для проверки service_id на gift_code)
        limit: Количество транзакций для запроса из БД (после фильтрации пар останется примерно половина)
        
    Returns:
        Список отфильтрованных транзакций, отсортированных по дате (новые первыми)
    """
    from .common.content_billing_models import Transaction
    
    # Получаем транзакции, где баланс участвует (либо от него, либо к нему)
    result = await session.execute(
        select(Transaction)
        .where(
            (Transaction.user_id == user_id)
            & (
                (Transaction.balance_id_from == balance_id)
                | (Transaction.balance_id_to == balance_id)
            )
        )
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    
    raw_transactions = result.scalars().all()
    
    if not raw_transactions:
        return []
    
    # Фильтруем пары транзакций
    return await _filter_transaction_pairs(
        session=session,
        transactions=list(raw_transactions),
        balance_id=balance_id,
        user_id=user_id,
    )


async def _filter_transaction_pairs(
    session: AsyncSession,
    transactions: list,
    balance_id: int,
    user_id: uuid.UUID,
) -> list:
    """
    Фильтрует пары транзакций, оставляя только одну транзакцию из каждой пары.
    
    Выбирает правильную транзакцию с точки зрения пользователя:
    - Для списаний (платные действия): транзакция FROM_USER
    - Для пополнений (покупка токенов, промокоды, корректировки): транзакция TO_USER
    
    Args:
        session: Async database session
        transactions: Список транзакций для фильтрации
        balance_id: ID баланса пользователя
        user_id: ID пользователя (для проверки service_id)
        
    Returns:
        Список отфильтрованных транзакций
    """
    # Создаем множество всех ID транзакций для быстрой проверки
    all_tx_ids = {tx.id for tx in transactions}
    
    # Множество для отслеживания уже обработанных пар транзакций
    processed_pairs = set()
    
    filtered_transactions = []
    
    for tx in transactions:
        # Пропускаем транзакции с нулевой суммой
        if tx.amount == 0:
            continue
        
        # Определяем направление с точки зрения пользователя
        is_topup = tx.balance_id_to == balance_id
        is_withdraw = tx.balance_id_from == balance_id
        
        # Показываем только транзакции, где баланс участвует
        if not (is_topup or is_withdraw):
            continue
        
        # Обрабатываем пары транзакций
        if tx.correlation_id and tx.correlation_id in all_tx_ids:
            # Это транзакция из пары
            pair_id = tuple(sorted([str(tx.id), str(tx.correlation_id)]))
            
            # Если эта пара уже обработана, пропускаем
            if pair_id in processed_pairs:
                continue
            
            # Находим парную транзакцию
            pair_tx = next((t for t in transactions if t.id == tx.correlation_id), None)
            
            if pair_tx:
                # Определяем направление транзакций
                tx_is_from_user = tx.balance_id_from == balance_id
                tx_is_to_user = tx.balance_id_to == balance_id
                pair_is_from_user = pair_tx.balance_id_from == balance_id
                pair_is_to_user = pair_tx.balance_id_to == balance_id
                
                # Определяем тип операции для выбора правильной транзакции из пары
                tx_additional_data = tx.additional_data if isinstance(tx.additional_data, dict) else {}
                pair_additional_data = pair_tx.additional_data if isinstance(pair_tx.additional_data, dict) else {}
                
                # Проверяем корректировку баланса
                is_balance_correction = (
                    tx_additional_data.get("reason") == "test_balance_correction" or
                    pair_additional_data.get("reason") == "test_balance_correction"
                )
                
                # Проверяем, является ли service_id gift_code
                is_gift_code = False
                if tx.service_id is not None and tx.service_id == pair_tx.service_id:
                    try:
                        from src.db.lib.gift_codes.common.models import GiftCode
                        gift_code_result = await session.execute(
                            select(GiftCode).where(GiftCode.id == tx.service_id)
                        )
                        if gift_code_result.scalars().first():
                            is_gift_code = True
                    except Exception:
                        pass
                
                has_service_id = tx.service_id is not None and tx.service_id == pair_tx.service_id
                
                # Выбираем правильную транзакцию из пары
                if is_balance_correction:
                    # Корректировка баланса - показываем TO_USER (пополнение)
                    if tx_is_to_user:
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(tx)
                    elif pair_is_to_user:
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(pair_tx)
                    else:
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(tx)
                elif is_gift_code:
                    # Активация промокода - всегда пополнение, показываем TO_USER
                    if tx_is_to_user:
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(tx)
                    elif pair_is_to_user:
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(pair_tx)
                    else:
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(tx)
                elif has_service_id:
                    # Платное действие или покупка - определяем по направлению
                    if "WITHDRAW" in tx.transaction_type and tx_is_from_user:
                        # Списание (платное действие) - показываем FROM_USER
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(tx)
                    elif "WITHDRAW" in pair_tx.transaction_type and pair_is_from_user:
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(pair_tx)
                    elif "TOP_UP" in tx.transaction_type and tx_is_to_user:
                        # Пополнение (покупка) - показываем TO_USER
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(tx)
                    elif "TOP_UP" in pair_tx.transaction_type and pair_is_to_user:
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(pair_tx)
                    else:
                        # По умолчанию для платных действий показываем FROM_USER
                        if tx_is_from_user:
                            processed_pairs.add(pair_id)
                            filtered_transactions.append(tx)
                        elif pair_is_from_user:
                            processed_pairs.add(pair_id)
                            filtered_transactions.append(pair_tx)
                        else:
                            processed_pairs.add(pair_id)
                            filtered_transactions.append(tx)
                else:
                    # По умолчанию: показываем транзакцию FROM_USER (списание)
                    if tx_is_from_user:
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(tx)
                    elif pair_is_from_user:
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(pair_tx)
                    else:
                        # Если обе TO_USER (пополнение), показываем первую
                        processed_pairs.add(pair_id)
                        filtered_transactions.append(tx)
        else:
            # Транзакция без пары или correlation_id указывает на транзакцию вне выборки
            filtered_transactions.append(tx)
    
    # Сортируем по дате (новые первыми)
    filtered_transactions.sort(key=lambda tx: tx.created_at, reverse=True)
    
    return filtered_transactions


async def async_get_user_recent_transactions(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 10,
) -> list:
    """
    Получает последние транзакции пользователя (пополнения и списания токенов).
    
    Устаревшая функция. Используйте async_get_transactions_by_balance_id вместо неё.
    
    Args:
        session: Async database session
        user_id: ID пользователя
        limit: Количество транзакций для возврата (по умолчанию 10)
        
    Returns:
        Список транзакций, отсортированных по дате (новые первыми)
    """
    # Получаем ID баланса пользователя для токенов
    result = await session.execute(
        select(UserBalance)
        .where(
            (UserBalance.user_id == user_id)
            & (UserBalance.balance_type.has(CurrencyType.name == "TOKEN"))
        )
    )
    user_balance = result.scalars().first()
    
    if not user_balance:
        return []
    
    user_balance_id = user_balance.id
    
    # Используем новую функцию с фильтрацией пар
    return await async_get_transactions_by_balance_id(
        session=session,
        balance_id=user_balance_id,
        user_id=user_id,
        limit=limit * 2,  # Увеличиваем лимит, так как после фильтрации пар останется примерно половина
    )


async def async_get_user_balance(
    session: AsyncSession,
    user_id: uuid.UUID,
    currency_type: str,
) -> Decimal:
    """
    Асинхронно получает баланс пользователя.
    
    Args:
        session: Async database session
        user_id: ID пользователя
        currency_type: Тип валюты (например, "TOKEN")
        
    Returns:
        Баланс пользователя (0 если баланс не найден)
    """
    result = await session.execute(
        select(UserBalance)
        .where(
            (UserBalance.user_id == user_id)
            & (UserBalance.balance_type.has(CurrencyType.name == currency_type))
        )
    )
    user_balance = result.scalars().first()
    
    return user_balance.balance_amount if user_balance else Decimal(0)


async def set_user_balance_via_correction(
    session: AsyncSession,
    user_id: uuid.UUID,
    target_amount: Decimal,
) -> Decimal:
    """
    Устанавливает баланс пользователя через корректирующую транзакцию.
    
    Логика:
    1. Получить текущий баланс пользователя
    2. Вычислить разницу (target_amount - current_amount)
    3. Создать корректирующую транзакцию на эту разницу
    4. Использовать transfer_currency_from_balance_to_balance() для изменения баланса
    
    Args:
        session: Database session
        user_id: ID пользователя
        target_amount: Целевой баланс (не разница!)
        
    Returns:
        Разницу (корректировку), которая была применена
        
    Raises:
        Exception: Если компания-баланс не настроен
    """
    # 1. Получить текущий баланс
    result = await session.execute(
        select(UserBalance)
        .where(
            (UserBalance.user_id == user_id)
            & (UserBalance.balance_type.has(CurrencyType.name == "TOKEN"))
        )
    )
    user_balance = result.scalars().first()
    
    if not user_balance:
        # Если баланса нет - создать его с нулем, затем пополнить
        token_type_result = await session.execute(
            select(CurrencyType).where(CurrencyType.name == "TOKEN")
        )
        token_type = token_type_result.scalars().first()
        
        if not token_type:
            raise Exception("TOKEN currency type not found in database")
        
        user_balance = UserBalance(
            user_id=user_id,
            balance_type_id=token_type.id,
            balance_amount=Decimal(0)
        )
        session.add(user_balance)
        await session.flush()  # Чтобы баланс появился в БД
        current_amount = Decimal(0)
    else:
        current_amount = user_balance.balance_amount
    
    # 2. Вычислить корректировку
    correction = target_amount - current_amount
    
    if correction == 0:
        logger.info(f"No correction needed for user {user_id}, balance already at {target_amount}")
        return Decimal(0)
    
    # 3. Получить ID компании-баланса
    company_token_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
    if not company_token_balance_id:
        raise Exception("TOKEN_COMPANY_BALANCE_ID environment variable not set")
    company_token_balance_id = int(company_token_balance_id)
    
    # 4. Создать корректирующую транзакцию
    additional_data = {
        "reason": "test_balance_correction",
        "previous_balance": str(current_amount),
        "target_balance": str(target_amount),
        "correction": str(correction),
    }
    
    # Получаем ID баланса пользователя (нужен для trace_transactions)
    user_balance_id = user_balance.id
    
    # Асинхронные операции с балансом
    if correction > 0:
        # Пополнение: компания → пользователь
        await session.execute(
            update(UserBalance)
            .where(
                (UserBalance.id == company_token_balance_id)
                & (UserBalance.balance_type.has(CurrencyType.name == "TOKEN"))
            )
            .values(balance_amount=UserBalance.balance_amount - correction)
        )
        await session.execute(
            update(UserBalance)
            .where(
                (UserBalance.user_id == user_id)
                & (UserBalance.balance_type.has(CurrencyType.name == "TOKEN"))
            )
            .values(balance_amount=UserBalance.balance_amount + correction)
        )
        
        # Трассировка транзакций (используем синхронную SQLModel Session)
        # Создаем синхронную сессию из синхронного engine для работы с trace_transactions
        sync_session = Session(sync_engine)
        try:
            trace_transactions(
                sync_session,
                user_id=user_id,
                balance_id_from=company_token_balance_id,
                balance_id_to=user_balance_id,
                transaction_type=TopUpWithdrawTransactionTypes,
                service_id=None,
                amount=correction,
                source_name=SourceNames.TELEGRAM,
                additional_data=additional_data,
                clearing_id=None,
            )
            sync_session.commit()
        finally:
            sync_session.close()
        
        logger.info(f"✅ Balance correction for user {user_id}: +{correction} tokens (from {current_amount} to {target_amount})")
    else:
        # Списание: пользователь → компания (correction отрицательное)
        abs_correction = abs(correction)
        await session.execute(
            update(UserBalance)
            .where(
                (UserBalance.user_id == user_id)
                & (UserBalance.balance_type.has(CurrencyType.name == "TOKEN"))
            )
            .values(balance_amount=UserBalance.balance_amount - abs_correction)
        )
        await session.execute(
            update(UserBalance)
            .where(
                (UserBalance.id == company_token_balance_id)
                & (UserBalance.balance_type.has(CurrencyType.name == "TOKEN"))
            )
            .values(balance_amount=UserBalance.balance_amount + abs_correction)
        )
        
        # Трассировка транзакций (используем синхронную SQLModel Session)
        # Создаем синхронную сессию из синхронного engine для работы с trace_transactions
        sync_session = Session(sync_engine)
        try:
            trace_transactions(
                sync_session,
                user_id=user_id,
                balance_id_from=user_balance_id,
                balance_id_to=company_token_balance_id,
                transaction_type=TopUpWithdrawTransactionTypes,
                service_id=None,
                amount=abs_correction,
                source_name=SourceNames.TELEGRAM,
                additional_data=additional_data,
                clearing_id=None,
            )
            sync_session.commit()
        finally:
            sync_session.close()
        
        logger.info(f"✅ Balance correction for user {user_id}: {correction} tokens (from {current_amount} to {target_amount})")
    
    await session.commit()
    return correction
