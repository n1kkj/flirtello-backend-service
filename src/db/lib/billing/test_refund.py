import datetime
import os
import uuid

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import make_transient
from sqlmodel import Session, delete, select

from lib.auth import SupabaseAuth
from lib.billing.common.content_billing_models import (
    CurrencyType,
    TariffPlan,
    TokenPack,
    Transaction,
    UserBalance,
    UserPlan,
)
from lib.billing.common.enums import PurchaseSaleTransactionTypes
from lib.billing.refund import (
    find_billing_transaction_from_payment_system_transaction_id,
    get_service,
    process_refund,
    refund_tariff_plan,
)
from lib.config import config
from supabase import create_client

load_dotenv()
DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"

dbschema = "content,public"

engine = create_engine(DATABASE_URL, connect_args={"options": "-csearch_path={}".format(dbschema)})


@pytest.fixture(scope="function", autouse=True)
def db_data_backup(session: Session):
    transactions = session.exec(select(Transaction)).all()
    for obj in transactions:
        session.expunge(obj)
        make_transient(obj)

    session.exec(delete(Transaction))
    session.commit()

    yield session

    session.add_all(transactions)
    session.commit()


@pytest.fixture(scope="session")
def session():
    with Session(engine) as session:
        yield session


auth = SupabaseAuth(
    os.environ.get("API_URL"),
    os.environ.get("SERVICE_ROLE_KEY"),
    os.environ.get("PASSKEY"),
    engine,
)


def test_refund_tariff_plan(session: Session):
    try:

        stmt = select(TariffPlan).where(TariffPlan.is_trial == True, TariffPlan.is_archived == False)
        trial_tariff_plan = session.exec(stmt).first()
        user_id = uuid.uuid4()
        user_plan = UserPlan(user_id=user_id, tariff_plan_id=trial_tariff_plan.id)
        session.add(user_plan)
        session.flush()
        refund_tariff_plan(session=session, user_id=user_id)
        session.refresh(user_plan)
        assert user_plan.expired_at is None
        assert user_plan.tariff_plan_id == trial_tariff_plan.id
    finally:
        session.rollback()


def test_get_service(session: Session):
    try:
        tariff_plan = TariffPlan(
            id=uuid.uuid4(),
            is_trial=True,
            is_archived=False,
            price=100,
            name="Trial",
        )
        token_pack = TokenPack(
            id=uuid.uuid4(),
            is_archived=False,
            price=100,
            amount=100,
            name="Token Pack",
        )
        session.add(tariff_plan)
        session.add(token_pack)
        session.flush()
        assert get_service(session=session, service_id=tariff_plan.id) == tariff_plan
        assert get_service(session=session, service_id=token_pack.id) == token_pack
        assert get_service(session=session, service_id=uuid.uuid4()) is None
    finally:
        session.rollback()


def test_find_billing_transaction_from_payment_system_transaction_id(session: Session):
    try:
        billing_transaction = Transaction(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            balance_id_from=123,
            balance_id_to=456,
            source_name=None,
            amount=100,
            transaction_type=PurchaseSaleTransactionTypes.FIRST_TYPE.value,
            additional_data={"payment_system_transaction_id": "123"},
            created_at=datetime.datetime.now(),
        )
        session.add(billing_transaction)
        session.flush()
        assert (
            find_billing_transaction_from_payment_system_transaction_id(
                session=session, payment_system_transaction_id="123"
            )
            == billing_transaction
        )
        assert (
            find_billing_transaction_from_payment_system_transaction_id(
                session=session, payment_system_transaction_id="456"
            )
            is None
        )
    finally:
        session.rollback()


def test_process_refund_tariff_plan(session: Session):
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        session.commit()
        user_token_balance_before = session.exec(select(UserBalance).where(UserBalance.user_id == user_id).where(UserBalance.currency_type_id == 1)).first().balance_amount
        company_token_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
        assert company_token_balance_id, "Token company balance id is't set"
        company_token_balance_id = int(company_token_balance_id)
        company_token_balance_amount_before = session.get(
            UserBalance, company_token_balance_id
        ).balance_amount

        eur_company_balance_id = os.environ.get("EUR_COMPANY_BALANCE_ID")
        assert eur_company_balance_id, "Eur company balance id is't set"
        eur_company_balance_id = int(eur_company_balance_id)
        eur_company_balance_amount_before = session.get(
            UserBalance, eur_company_balance_id
        ).balance_amount

        company_service_balance_id = os.environ.get("SERVICE_COMPANY_BALANCE_ID")
        assert company_service_balance_id, "Service company balance id is't set"
        company_service_balance_id = int(company_service_balance_id)
        company_service_balance_amount_before = session.get(
            UserBalance, company_service_balance_id
        ).balance_amount

        payment_system_transaction_id = "TXN07TEST"
        tariff_plan = TariffPlan(
            id=uuid.uuid4(),
            is_trial=False,
            is_archived=False,
            price=12,
            name="Test Tariff Plan",
            currency_type_id=3,
            tokens_per_month=100,
        )
        billing_transaction = Transaction(
            id=uuid.uuid4(),
            user_id=user_id,
            service_id=tariff_plan.id,
            balance_id_from=123,
            balance_id_to=456,
            source_name=None,
            amount=100,
            transaction_type=PurchaseSaleTransactionTypes.FIRST_TYPE.value,
            additional_data={"payment_system_transaction_id": payment_system_transaction_id},
            created_at=datetime.datetime.now(),
        )
        session.add(billing_transaction)
        session.add(tariff_plan)
        session.flush()
        process_refund(
            session=session,
            user_id=user_id,
            payment_system_transaction_id=payment_system_transaction_id,
            payment_system_balance_id=config.payment_system_balance_id,
        )
        session.commit()
        user_token_balance_after = session.exec(select(UserBalance).where(UserBalance.user_id == user_id).where(UserBalance.currency_type_id == 1)).first().balance_amount
        assert user_token_balance_before == user_token_balance_after + 100
        company_token_balance_amount_after = session.get(
            UserBalance, company_token_balance_id
        ).balance_amount
        assert company_token_balance_amount_after == company_token_balance_amount_before + 100
        eur_company_balance_amount_after = session.get(
            UserBalance, eur_company_balance_id
        ).balance_amount
        assert eur_company_balance_amount_after == eur_company_balance_amount_before - 12
        service_company_balance_amount_after = session.get(
            UserBalance, company_service_balance_id
        ).balance_amount
        assert service_company_balance_amount_after == company_service_balance_amount_before + 1
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        transactions = session.exec(stmt).all()
        assert len(transactions) == 11
    finally:
        session.rollback()
        c_u1.auth.sign_out()
        auth.delete_user_by_email("rlstest1@flirtello.com")


def test_process_refund_token_pack(session: Session):
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        company_token_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
        assert company_token_balance_id, "Token company balance id is't set"
        company_token_balance_id = int(company_token_balance_id)
        company_token_balance_amount_before = session.get(
            UserBalance, company_token_balance_id
        ).balance_amount

        eur_company_balance_id = os.environ.get("EUR_COMPANY_BALANCE_ID")
        assert eur_company_balance_id, "Eur company balance id is't set"
        eur_company_balance_id = int(eur_company_balance_id)
        eur_company_balance_amount_before = session.get(
            UserBalance, eur_company_balance_id
        ).balance_amount

        payment_system_transaction_id = "TXN07TEST"
        token_pack = TokenPack(
            id=uuid.uuid4(),
            is_archived=False,
            price=12,
            amount=100,
            name="Test Token Pack",
            currency_type_id=3,
        )
        billing_transaction = Transaction(
            id=uuid.uuid4(),
            user_id=user_id,
            service_id=token_pack.id,
            balance_id_from=123,
            balance_id_to=456,
            source_name=None,
            amount=100,
            transaction_type=PurchaseSaleTransactionTypes.FIRST_TYPE.value,
            additional_data={"payment_system_transaction_id": payment_system_transaction_id},
            created_at=datetime.datetime.now(),
        )
        session.add(billing_transaction)
        session.add(token_pack)
        session.flush()
        process_refund(
            session=session,
            user_id=user_id,
            payment_system_transaction_id=payment_system_transaction_id,
            payment_system_balance_id=config.payment_system_balance_id,
        )
        session.commit()
        company_token_balance_amount_after = session.get(
            UserBalance, company_token_balance_id
        ).balance_amount
        assert company_token_balance_amount_after == company_token_balance_amount_before + 100
        eur_company_balance_amount_after = session.get(
            UserBalance, eur_company_balance_id
        ).balance_amount
        assert eur_company_balance_amount_after == eur_company_balance_amount_before - 12
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        transactions = session.exec(stmt).all()
        assert len(transactions) == 9
    finally:
        session.rollback()
        c_u1.auth.sign_out()
        auth.delete_user_by_email("rlstest1@flirtello.com")
