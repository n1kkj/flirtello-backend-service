from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlmodel import Session, insert

from .common.content_billing_models import Transaction
from .common.enums import SourceNames, TransactionTypes


def trace_transactions(
    session: Session,
    user_id: UUID,
    balance_id_from: int,
    balance_id_to: int,
    transaction_type: TransactionTypes,
    service_id: UUID,
    amount: Decimal,
    source_name: SourceNames,
    additional_data: dict = None,
    clearing_id: int | None = None,
):
    first_transaction_id = uuid4()
    second_transaction_id = uuid4()
    first_trace = insert(Transaction).values(
        id=first_transaction_id,
        user_id=user_id,
        balance_id_from=balance_id_from,
        balance_id_to=balance_id_to,
        transaction_type=transaction_type.FIRST_TYPE.value,
        service_id=service_id,
        amount=-amount,
        source_name=source_name,
        additional_data=additional_data,
        correlation_id=second_transaction_id,
        created_at=datetime.now(UTC),
        clearing_id=clearing_id,
    )
    second_trace = insert(Transaction).values(
        id=second_transaction_id,
        user_id=user_id,
        balance_id_from=balance_id_to,
        balance_id_to=balance_id_from,
        transaction_type=transaction_type.SECOND_TYPE.value,
        service_id=service_id,
        amount=amount,
        source_name=source_name,
        additional_data=additional_data,
        correlation_id=first_transaction_id,
        created_at=datetime.now(UTC),
        clearing_id=clearing_id,
    )
    session.exec(first_trace)
    session.exec(second_trace)
    session.flush()
