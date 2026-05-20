import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import threading
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from sqlalchemy.orm import make_transient, sessionmaker
from sqlmodel import Session, create_engine, delete, select, update

from lib.auth import SupabaseAuth
from lib.billing.clearing.clearing import (
    instant_tariff_plan_debit,
    process_clearing,
    process_expired_token_batches_clearing,
    process_tariff_plan_debit,
    stream_user_plans,
)
from lib.billing.common.content_billing_models import (
    Clearing,
    CurrencyType,
    Invoice,
    PaidAction,
    TariffPlan,
    TokenBatch,
    Transaction,
    UserBalance,
    UserPlan,
)
from lib.billing.common.enums import ServiceTypes, SourceNames
from lib.billing.invoicing import ServiceDataset
from lib.billing.service_processing import TariffPlanProcessor
from lib.config import config
from supabase import create_client

load_dotenv()
DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"

dbschema = "content,public"

engine = create_engine(
    DATABASE_URL,
    connect_args={"options": "-csearch_path={}".format(dbschema)},
    isolation_level="SERIALIZABLE",
    pool_size=300,  # Increase the pool size
    max_overflow=20,  # Allow overflow connections
    pool_timeout=30,  # Timeout for getting a connection from the pool
)
concurrency_session = sessionmaker(bind=engine)


@pytest.fixture(scope="session")
def session():
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="function", autouse=True)
def db_data_backup(session: Session):
    # Backup all data
    user_plans = session.exec(select(UserPlan)).all()
    currencies_types = session.exec(select(CurrencyType)).all()
    balances = session.exec(select(UserBalance)).all()
    transactions = session.exec(select(Transaction)).all()
    tariff_plans = session.exec(select(TariffPlan)).all()
    paid_actions = session.exec(select(PaidAction)).all()
    invoices = session.exec(select(Invoice)).all()
    token_batches = session.exec(select(TokenBatch)).all()

    # Make all objects transient
    for obj in (
        currencies_types
        + balances
        + transactions
        + user_plans
        + tariff_plans
        + paid_actions
        + token_batches
        + invoices
    ):
        session.expunge(obj)
        make_transient(obj)

    # Delete in correct order (children first, then parents)
    session.exec(delete(Transaction))
    session.exec(delete(TokenBatch))
    session.exec(delete(UserPlan))
    session.exec(delete(PaidAction))
    session.exec(delete(Invoice))
    session.exec(delete(UserBalance))
    session.exec(delete(TariffPlan))
    session.exec(delete(CurrencyType))
    session.commit()

    yield session

    # Restore in correct order (parents first, then children)
    session.add_all(currencies_types)
    session.commit()

    session.add_all(tariff_plans)
    session.commit()

    session.add_all(balances)
    session.commit()

    session.add_all(paid_actions)
    session.commit()

    session.add_all(user_plans)
    session.commit()

    session.add_all(token_batches)
    session.commit()

    session.add_all(transactions)
    session.commit()

    session.add_all(invoices)
    session.commit()


auth = SupabaseAuth(
    os.environ.get("API_URL"),
    os.environ.get("SERVICE_ROLE_KEY"),
    os.environ.get("PASSKEY"),
    engine,
)


def test_process_expired_token_batches_clearing(session):
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        token = CurrencyType(id=2, name="TOKEN")

        company_expired_token_balance = UserBalance(
            id=int(os.environ.get("EXPIRED_TOKEN_COMPANY_BALANCE_ID")), currency_type_id=2
        )
        tariff_plan_id = uuid.uuid4()
        tariff_plan = TariffPlan(
            id=tariff_plan_id,
            name="Trial",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=None,
            tariff_info=None,
            currency_type_id=None,
            is_trial=True,
        )
        usd = CurrencyType(id=1, name="USD")
        token = CurrencyType(id=2, name="TOKEN")
        service = CurrencyType(id=3, name="SERVICE")
        company_trial_token_balance = UserBalance(
            id=int(os.environ.get("TRIAL_TOKEN_COMPANY_BALANCE_ID")), currency_type_id=2
        )
        session.add_all(
            [
                tariff_plan,
                usd,
                token,
                service,
                company_trial_token_balance,
                company_expired_token_balance,
            ]
        )

        session.commit()
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        session.exec(
            update(TariffPlan).where(TariffPlan.id == tariff_plan_id).values(is_trial=False)
        )
        session.exec(
            update(UserBalance)
            .where((UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2))
            .values(balance_amount=Decimal("13.2"))
        )
        tb1 = TokenBatch(
            token_amount=2,
            expiration_date=datetime.now(UTC),
            user_plans_id=user_id,
        )
        tb2 = TokenBatch(
            token_amount=12,
            expiration_date=datetime.now(UTC) + relativedelta(days=1),
            user_plans_id=user_id,
        )
        session.add_all([tb1, tb2])
        session.commit()
        user_plan = session.exec(select(UserPlan).where(UserPlan.user_id == user_id)).first()
        assert process_expired_token_batches_clearing(session, user_plan) is None
        session.commit()
        cleared_user_balance = session.exec(
            select(UserBalance).where(
                (UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2)
            )
        ).first()
        assert cleared_user_balance.balance_amount == Decimal(12)
        transactions = session.exec(select(Transaction)).all()
        assert len(transactions) == 4
        assert transactions[3].amount == Decimal("1.2")
        token_batches = session.exec(select(TokenBatch)).all()
        assert len(token_batches) == 1
        session.exec(delete(Transaction))
        tb2.expiration_date = datetime.now(UTC)
        session.add(tb2)
        tb3 = TokenBatch(
            token_amount=13,
            expiration_date=datetime.now(UTC),
            user_plans_id=user_id,
        )
        session.add(tb3)
        session.exec(
            update(UserBalance)
            .where((UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2))
            .values(balance_amount=Decimal("25"))
        )
        session.commit()
        assert process_expired_token_batches_clearing(session, user_plan) is None
        session.commit()
        cleared_user_balance = session.exec(
            select(UserBalance).where(
                (UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2)
            )
        ).first()
        assert cleared_user_balance.balance_amount == Decimal(0)
        transactions = session.exec(select(Transaction)).all()
        assert len(transactions) == 4
        assert transactions[3].amount == Decimal("13")
        token_batches = session.exec(select(TokenBatch)).all()
        assert len(token_batches) == 0
        session.exec(delete(Transaction))
        tb4 = TokenBatch(
            token_amount=13,
            expiration_date=datetime.now(UTC) + relativedelta(days=1),
            user_plans_id=user_id,
        )
        tb5 = TokenBatch(
            token_amount=13,
            expiration_date=datetime.now(UTC) + relativedelta(days=1),
            user_plans_id=user_id,
        )
        session.add(tb4)
        session.add(tb5)
        session.exec(
            update(UserBalance)
            .where((UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2))
            .values(balance_amount=Decimal("26"))
        )
        session.commit()
        assert process_expired_token_batches_clearing(session, user_plan) is None
        session.commit()
        cleared_user_balance = session.exec(
            select(UserBalance).where(
                (UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2)
            )
        ).first()
        assert cleared_user_balance.balance_amount == Decimal(26)
        transactions = session.exec(select(Transaction)).all()
        assert len(transactions) == 0
        token_batches = session.exec(select(TokenBatch)).all()
        assert len(token_batches) == 2

    finally:
        c_u1.auth.sign_out()

        auth.delete_user_by_email("rlstest1@flirtello.com")
        session.exec(delete(Transaction))
        session.exec(delete(UserBalance))
        session.exec(delete(CurrencyType))
        session.exec(delete(TokenBatch))
        session.exec(delete(UserPlan))
        session.commit()


def test_process_tariff_plan_debit(session):
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")

        tariff_plan_id = uuid.uuid4()
        tariff_plan_trial_id = uuid.uuid4()
        tariff_plan = TariffPlan(
            id=tariff_plan_id,
            name="Trial21",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=2,
            tariff_info=None,
            currency_type_id=1,
            is_trial=False,
        )
        tariff_plan_trial = TariffPlan(
            id=tariff_plan_trial_id,
            name="Trial",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=None,
            tariff_info=None,
            currency_type_id=None,
            is_trial=True,
        )
        eur = CurrencyType(id=1, name="EUR")
        token = CurrencyType(id=2, name="TOKEN")
        service = CurrencyType(id=3, name="SERVICE")
        company_trial_token_balance = UserBalance(
            id=int(os.environ.get("TRIAL_TOKEN_COMPANY_BALANCE_ID")), currency_type_id=2
        )
        company_eur_balance = UserBalance(
            id=int(os.environ.get("EUR_COMPANY_BALANCE_ID")), currency_type_id=1
        )
        company_payment_system_balance = UserBalance(
            id=int(os.environ.get("PAYMENT_SYSTEM_BALANCE_ID")), currency_type_id=1
        )
        company_token_balance = UserBalance(
            id=int(os.environ.get("TOKEN_COMPANY_BALANCE_ID")), currency_type_id=2
        )
        company_service_balance = UserBalance(
            id=int(os.environ.get("SERVICE_COMPANY_BALANCE_ID")), currency_type_id=3
        )
        session.add_all(
            [
                tariff_plan,
                tariff_plan_trial,
                eur,
                token,
                service,
                company_trial_token_balance,
                company_eur_balance,
                company_payment_system_balance,
                company_token_balance,
                company_service_balance,
            ]
        )
        session.commit()
        sd = ServiceDataset(service_type=ServiceTypes.TARIFF_PLAN, service_id=tariff_plan_id)
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        tp = TariffPlanProcessor(session, user_id, sd, SourceNames.WEB_SITE)
        tp.sell_service(payment_system_balance_id=config.payment_system_balance_id)
        session.commit()

        is_tp_trial = tp.apply_service()

        session.commit()
        assert is_tp_trial

        instant_tariff_plan_debit(session, user_id, is_tp_trial, SourceNames.WEB_SITE)
        session.commit()

        up = session.exec(select(UserPlan).where(UserPlan.user_id == user_id)).first()
        process_tariff_plan_debit(session, up)
        session.commit()
        updated_up = session.exec(select(UserPlan).where(UserPlan.user_id == user_id)).first()
        updated_ub = session.exec(
            select(UserBalance).where(
                (UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2)
            )
        ).first()
        # assert updated_up.next_top_up is None
        assert updated_ub.balance_amount == Decimal(1234)

        # Ensure that debit is passed
        up = session.exec(select(UserPlan).where(UserPlan.user_id == user_id)).first()
        up.is_paid = True
        session.commit()
        process_tariff_plan_debit(session, up)
        session.commit()
        updated_up = session.exec(select(UserPlan).where(UserPlan.user_id == user_id)).first()
        updated_ub = session.exec(
            select(UserBalance).where(
                (UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2)
            )
        ).first()
        # assert updated_up.next_top_up is None
        assert updated_ub.balance_amount == Decimal(1234) * 2

    finally:
        c_u1.auth.sign_out()

        auth.delete_user_by_email("rlstest1@flirtello.com")
        session.exec(delete(Transaction))
        session.exec(delete(TariffPlan))
        session.exec(delete(UserBalance))
        session.exec(delete(CurrencyType))
        session.exec(delete(TokenBatch))
        session.exec(delete(UserPlan))
        session.commit()


def test_stream_user_plans(session):
    try:
        eur = CurrencyType(id=1, name="EUR")

        tariff_plan_id = uuid.uuid4()
        tariff_plan = TariffPlan(
            id=tariff_plan_id,
            name="Test",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=2,
            tariff_info=None,
            currency_type_id=1,
            is_trial=True,
        )
        session.add(tariff_plan)
        session.add(eur)
        # Create valid user plans
        for _ in range(100):
            user_id = uuid.uuid4()
            expiration_date = datetime.now(UTC)
            up = UserPlan(
                user_id=user_id,
                expired_at=expiration_date,
                tariff_plan_id=tariff_plan_id,
                next_top_up=datetime.now(UTC),
                is_paid=True,
            )
            session.add(up)
            session.flush()

        for _ in range(100):
            user_id = uuid.uuid4()
            expiration_date = datetime.now(UTC) + relativedelta(months=1)
            up = UserPlan(
                user_id=user_id,
                expired_at=expiration_date,
                tariff_plan_id=tariff_plan_id,
                is_paid=True,
            )
            session.add(up)
            session.flush()

        for _ in range(100):
            user_id = uuid.uuid4()
            expiration_date = datetime.now(UTC)
            up = UserPlan(
                user_id=user_id,
                expired_at=expiration_date,
                tariff_plan_id=tariff_plan_id,
                next_top_up=datetime.now(UTC),
                is_paid=False,
            )
            session.add(up)
            session.flush()

        expected_user_plans_count = 100
        res_count = 0
        for _ in stream_user_plans(session=session):
            res_count += 1

        assert expected_user_plans_count == res_count

        tariff_plan_id = uuid.uuid4()
        tariff_plan = TariffPlan(
            id=tariff_plan_id,
            name="Test",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=2,
            tariff_info=None,
            currency_type_id=1,
            is_trial=False,
        )
        session.add(tariff_plan)
        # Create valid user plans
        for _ in range(100):
            user_id = uuid.uuid4()
            expiration_date = datetime.now(UTC)
            up = UserPlan(
                user_id=user_id,
                expired_at=expiration_date,
                tariff_plan_id=tariff_plan_id,
                next_top_up=datetime.now(UTC),
                is_paid=True,
            )
            session.add(up)
            session.flush()

        for _ in range(100):
            user_id = uuid.uuid4()
            expiration_date = datetime.now(UTC)
            up = UserPlan(
                user_id=user_id,
                expired_at=expiration_date,
                tariff_plan_id=tariff_plan_id,
                next_top_up=datetime.now(UTC) + relativedelta(months=1),
                is_paid=True,
            )
            session.add(up)
            session.flush()

        for _ in range(100):
            user_id = uuid.uuid4()
            expiration_date = datetime.now(UTC)
            up = UserPlan(
                user_id=user_id,
                expired_at=expiration_date,
                tariff_plan_id=tariff_plan_id,
                next_top_up=datetime.now(UTC),
                is_paid=False,
            )
            session.add(up)
            session.flush()

        expected_user_plans_count = 300
        res_count = 0
        for _ in stream_user_plans(session=session):
            res_count += 1

        assert expected_user_plans_count == res_count
    finally:
        session.rollback()


def test_process_clearing(session):
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")

        tariff_plan_id = uuid.uuid4()
        tariff_plan_trial_id = uuid.uuid4()
        tariff_plan = TariffPlan(
            id=tariff_plan_id,
            name="Trial21",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=2,
            tariff_info=None,
            currency_type_id=1,
            is_trial=False,
        )
        tariff_plan_trial = TariffPlan(
            id=tariff_plan_trial_id,
            name="Trial",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=None,
            tariff_info=None,
            currency_type_id=None,
            is_trial=True,
        )
        usd = CurrencyType(id=1, name="USD")
        token = CurrencyType(id=2, name="TOKEN")
        service = CurrencyType(id=3, name="SERVICE")
        company_expired_token_balance = UserBalance(
            id=int(os.environ.get("EXPIRED_TOKEN_COMPANY_BALANCE_ID")), currency_type_id=2
        )
        company_trial_token_balance = UserBalance(
            id=int(os.environ.get("TRIAL_TOKEN_COMPANY_BALANCE_ID")), currency_type_id=2
        )
        company_eur_balance = UserBalance(
            id=int(os.environ.get("EUR_COMPANY_BALANCE_ID")), currency_type_id=1
        )
        company_token_balance = UserBalance(
            id=int(os.environ.get("TOKEN_COMPANY_BALANCE_ID")), currency_type_id=2
        )
        company_service_balance = UserBalance(
            id=int(os.environ.get("SERVICE_COMPANY_BALANCE_ID")), currency_type_id=3
        )
        session.add_all(
            [
                tariff_plan,
                tariff_plan_trial,
                usd,
                token,
                service,
                company_trial_token_balance,
                company_eur_balance,
                company_token_balance,
                company_service_balance,
                company_expired_token_balance,
            ]
        )

        session.commit()
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )

        session.exec(
            update(TariffPlan).where(TariffPlan.id == tariff_plan_id).values(is_trial=False)
        )
        session.exec(
            update(UserBalance)
            .where((UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2))
            .values(balance_amount=Decimal("13.2"))
        )
        tb1 = TokenBatch(
            token_amount=2,
            expiration_date=datetime.now(UTC),
            user_plans_id=user_id,
        )
        tb2 = TokenBatch(
            token_amount=12,
            expiration_date=datetime.now(UTC) + relativedelta(days=1),
            user_plans_id=user_id,
        )
        session.add_all([tb1, tb2])
        session.exec(
            update(UserPlan)
            .where(UserPlan.user_id == user_id)
            .values(
                expired_at=datetime.now(UTC) + relativedelta(months=1),
                tariff_plan_id=tariff_plan_id,
                next_top_up=datetime.now(UTC),
                is_paid=True,
            )
        )
        session.commit()
        assert process_clearing(session) is None

        cleared_user_balance = session.exec(
            select(UserBalance).where(
                (UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2)
            )
        ).first()
        assert cleared_user_balance.balance_amount == Decimal(1246)
        transactions = session.exec(select(Transaction)).all()
        assert len(transactions) == 6
        assert transactions[3].amount == Decimal("1.2")
        token_batches = session.exec(select(TokenBatch)).all()
        assert len(token_batches) == 2

    finally:
        c_u1.auth.sign_out()

        auth.delete_user_by_email("rlstest1@flirtello.com")
        session.exec(delete(Transaction))
        session.exec(delete(TariffPlan))
        session.exec(delete(Clearing))
        session.exec(delete(UserBalance))
        session.exec(delete(CurrencyType))
        session.exec(delete(TokenBatch))
        session.exec(delete(UserPlan))
        session.commit()


@pytest.mark.skip()
def test_clearing_concurrency(session):
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")

        tariff_plan_id = uuid.uuid4()
        tariff_plan_trial_id = uuid.uuid4()
        tariff_plan = TariffPlan(
            id=tariff_plan_id,
            name="Trial21",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=2,
            tariff_info=None,
            currency_type_id=1,
            is_trial=False,
        )
        tariff_plan_trial = TariffPlan(
            id=tariff_plan_trial_id,
            name="Trial",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=None,
            tariff_info=None,
            currency_type_id=None,
            is_trial=True,
        )
        eur = CurrencyType(id=1, name="EUR")
        token = CurrencyType(id=2, name="TOKEN")
        service = CurrencyType(id=3, name="SERVICE")
        company_trial_token_balance = UserBalance(
            id=int(os.environ.get("TRIAL_TOKEN_COMPANY_BALANCE_ID")), currency_type_id=2
        )
        company_eur_balance = UserBalance(
            id=int(os.environ.get("EUR_COMPANY_BALANCE_ID")), currency_type_id=1
        )
        company_payment_system_balance = UserBalance(
            id=int(os.environ.get("PAYMENT_SYSTEM_BALANCE_ID")), currency_type_id=1
        )
        company_token_balance = UserBalance(
            id=int(os.environ.get("TOKEN_COMPANY_BALANCE_ID")), currency_type_id=2
        )
        company_service_balance = UserBalance(
            id=int(os.environ.get("SERVICE_COMPANY_BALANCE_ID")), currency_type_id=3
        )
        session.add_all(
            [
                tariff_plan,
                tariff_plan_trial,
                eur,
                token,
                service,
                company_trial_token_balance,
                company_eur_balance,
                company_payment_system_balance,
                company_token_balance,
                company_service_balance,
            ]
        )
        session.commit()
        sd = ServiceDataset(service_type=ServiceTypes.TARIFF_PLAN, service_id=tariff_plan_id)
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        tp = TariffPlanProcessor(session, user_id, sd, SourceNames.WEB_SITE)
        tp.sell_service(payment_system_balance_id=config.payment_system_balance_id)
        session.commit()

        is_tp_trial = tp.apply_service()
        stmt = update(UserPlan).where(UserPlan.user_id == user_id).values(is_paid=True)
        session.exec(stmt)
        session.commit()

        threads = []
        for _ in range(30):
            thread = threading.Thread(target=process_clearing, args=(engine,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify the results

        cleared_user_balance = session.exec(
            select(UserBalance).where(
                (UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 2)
            )
        ).first()
        assert cleared_user_balance.balance_amount == Decimal(5 + 1234)
        cleared_user_plan = session.get(UserPlan, user_id)
    finally:
        c_u1.auth.sign_out()

        auth.delete_user_by_email("rlstest1@flirtello.com")
        session.exec(delete(Transaction))
        session.exec(delete(TariffPlan))
        session.exec(delete(UserBalance))
        session.exec(delete(CurrencyType))
        session.exec(delete(TokenBatch))
        session.exec(delete(UserPlan))
        session.commit()
