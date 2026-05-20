import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy.orm import make_transient
from sqlmodel import Session, create_engine, delete, select, update

from lib.config import config
from lib.auth import SupabaseAuth
from lib.billing.balance_transactions import (
    check_user_have_enough_currency,
    transfer_currency_from_balance_to_balance,
)
from lib.billing.clearing.clearing import (
    instant_tariff_plan_debit,
    process_expired_token_batches_clearing,
    process_tariff_plan_debit,
)
from lib.billing.common.content_billing_models import (
    CurrencyType,
    Invoice,
    PaidAction,
    TariffPlan,
    TokenBatch,
    TokenPack,
    Transaction,
    UserBalance,
    UserPlan,
)
from lib.billing.common.enums import (
    InvoiceStatus,
    PurchaseSaleTransactionTypes,
    ServiceTypes,
    SourceNames,
    TopUpWithdrawTransactionTypes,
    TransactionTypes,
)
from lib.billing.common.exceptions import (
    NoSuchInvoiceError,
    NoSuchServiceError,
    NotEnoughCurrencyError,
    TariffPlanExpired,
)
from lib.billing.invoicing import (
    InvoiceValidator,
    ServiceDataset,
    create_invoice,
    get_service_model,
    pay_the_invoice,
)
from lib.billing.paid_actions import (
    get_paid_action_dataset,
    is_image_paid,
    process_paid_action,
    validate_tariff_plan,
)
from lib.billing.service_processing import TariffPlanProcessor, TokenPackProcessor
from supabase import create_client

load_dotenv()
DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"

dbschema = "content,public"

engine = create_engine(DATABASE_URL, connect_args={"options": "-csearch_path={}".format(dbschema)})


@pytest.fixture(scope="session")
def session():
    with Session(engine) as session:
        yield session
        session.rollback()


auth = SupabaseAuth(
    os.environ.get("API_URL"),
    os.environ.get("SERVICE_ROLE_KEY"),
    os.environ.get("PASSKEY"),
    engine,
)


@pytest.fixture(scope="function", autouse=True)
def db_data_backup(session: Session):
    user_plans = session.exec(select(UserPlan)).all()
    currencies_types = session.exec(select(CurrencyType)).all()
    balances = session.exec(select(UserBalance)).all()
    transactions = session.exec(select(Transaction)).all()
    tariff_plans = session.exec(select(TariffPlan)).all()
    paid_actions = session.exec(select(PaidAction)).all()
    invoices = session.exec(select(Invoice)).all()
    token_batches = session.exec(select(TokenBatch)).all()

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

    session.exec(delete(CurrencyType))
    session.exec(delete(UserBalance))
    session.exec(delete(PaidAction))
    session.exec(delete(Transaction))
    session.exec(delete(TokenBatch))
    session.exec(delete(UserPlan))
    session.exec(delete(TariffPlan))
    session.exec(delete(Invoice))
    session.commit()

    yield session

    session.add_all(currencies_types)
    session.add_all(balances)
    session.add_all(tariff_plans)
    session.add_all(paid_actions)
    session.add_all(user_plans)
    session.add_all(transactions)
    session.add_all(token_batches)
    session.add_all(invoices)
    session.commit()


def test_is_image_paid(session: Session):
    image_id = uuid.uuid4()
    user_id = uuid.uuid4()
    req_transaction = Transaction(
        balance_id_from=11,
        balance_id_to=12,
        transaction_type="test-type",
        user_id=user_id,
        additional_data={
            "tp-id": 12343,
            "image_id": str(image_id),
            "char_id": 1,
        },
    )
    incorrect_transaction = Transaction(
        balance_id_from=11,
        balance_id_to=12,
        transaction_type="test-type",
        user_id=user_id,
        additional_data={
            "tp-id": 12343,
            "image_id": str(image_id) + "1",
            "char_id": 1,
        },
    )
    assert not is_image_paid(session, user_id, image_id)
    session.add(incorrect_transaction)
    session.commit()
    assert not is_image_paid(session, user_id, image_id)
    session.add(req_transaction)
    session.commit()
    assert is_image_paid(session, user_id, image_id)


def test_validate_tariff_plan(session: Session):
    currency_type = CurrencyType(id=9340, name="USD")
    tariff_plan = TariffPlan(
        name="Test tariff plan",
        tokens_per_month=Decimal(100),
        duration_in_month=3,
        currency_type_id=9340,
        month_price=Decimal(1000),
    )
    trial_tariff_plan = TariffPlan(
        name="Trial test tariff plan",
        tokens_per_month=Decimal(100),
        duration_in_month=3,
        currency_type_id=9340,
        month_price=Decimal(1000),
        is_trial=True,
    )
    user_id_active = uuid.uuid4()
    user_id_expired = uuid.uuid4()
    user_id_trial = uuid.uuid4()
    expired_date = datetime.now(UTC) - timedelta(days=1)
    active_date = datetime.now(UTC) + timedelta(days=1)
    user_stats_expired_tariff_plan = UserPlan(
        user_id=user_id_expired, expired_at=expired_date, tariff_plan_id=tariff_plan.id
    )
    user_stats_active_tariff_plan = UserPlan(
        user_id=user_id_active, expired_at=active_date, tariff_plan_id=tariff_plan.id
    )
    user_stats_trial_tariff_plan = UserPlan(user_id=user_id_trial, tariff_plan_id=tariff_plan.id)

    try:
        session.add_all(
            [
                currency_type,
                tariff_plan,
                trial_tariff_plan,
                user_stats_expired_tariff_plan,
                user_stats_active_tariff_plan,
                user_stats_trial_tariff_plan,
            ]
        )

        session.commit()
        with pytest.raises(TariffPlanExpired):
            validate_tariff_plan(session, user_id_expired)

        assert validate_tariff_plan(session, user_id_active) is None
        assert validate_tariff_plan(session, user_id_trial) is None
    finally:
        # Clean up
        session.delete(user_stats_expired_tariff_plan)
        session.delete(user_stats_active_tariff_plan)
        session.delete(user_stats_trial_tariff_plan)
        session.delete(trial_tariff_plan)
        session.delete(tariff_plan)
        session.commit()
        session.delete(currency_type)
        session.commit()


def test_get_paid_action_dataset(session: Session):
    paid_action_name = "TEST_ACTION"
    action_id = uuid.uuid4()
    price = Decimal("10.00")

    paid_action = PaidAction(id=action_id, name=paid_action_name, price=price)
    try:
        session.add(paid_action)
        session.commit()
        result = get_paid_action_dataset(session, paid_action_name)

        assert result.id == action_id
        assert result.price == price
    finally:
        # Clean up
        session.delete(paid_action)
        session.commit()


def test_check_user_have_enough_currency(session):
    try:
        user_id = uuid.uuid4()
        user_balance_amount = Decimal("20.00")
        required_currency_amount = Decimal("10.00")
        currency_type = CurrencyType(name="TOKEN")
        session.add(currency_type)
        session.commit()

        user_balance = UserBalance(
            user_id=user_id, balance_amount=user_balance_amount, currency_type_id=currency_type.id
        )
        session.add(user_balance)
        session.commit()
        with pytest.raises(NotEnoughCurrencyError):
            check_user_have_enough_currency(
                session, user_id, required_currency_amount + Decimal(20), "TOKEN"
            )
        assert (
            check_user_have_enough_currency(session, user_id, required_currency_amount, "TOKEN")
            is None
        )

    finally:
        # Clean up
        session.delete(user_balance)
        session.delete(currency_type)
        session.commit()


def test_transfer_currency_from_balance_to_balance(session):
    try:
        user_id = uuid.uuid4()
        company_balance_id = 1234
        paid_action_name = "test_action"
        action_id = uuid.uuid4()
        price = Decimal("10.00")
        currency_type = CurrencyType(id=1, name="TOKEN")

        paid_action = PaidAction(id=action_id, name=paid_action_name, price=price)
        user_balance = UserBalance(user_id=user_id, balance_amount=Decimal(0), currency_type_id=1)
        company_balance = UserBalance(
            id=company_balance_id, user_id=None, balance_amount=Decimal(0), currency_type_id=1
        )
        session.add_all([currency_type, paid_action, user_balance, company_balance])
        session.commit()
        transfer_currency_from_balance_to_balance(
            session,
            user_id,
            company_balance_id,
            price,
            "TOKEN",
            TopUpWithdrawTransactionTypes,
            action_id,
            SourceNames.WEB_SITE,
        )
        session.commit()
        user_balance_amount = (
            session.exec(select(UserBalance).where(UserBalance.user_id == user_id))
            .first()
            .balance_amount
        )
        company_balance_amount = (
            session.exec(select(UserBalance).where(UserBalance.id == company_balance_id))
            .first()
            .balance_amount
        )
        assert user_balance_amount == -price
        assert company_balance_amount == price
        transactions = session.exec(select(UserBalance)).all()
        assert len(transactions) == 2

    finally:
        session.delete(user_balance)
        session.delete(company_balance)
        session.delete(paid_action)
        session.delete(currency_type)
        session.exec(delete(Transaction))
        session.commit()


def test_process_paid_action(session: Session):
    user_id = uuid.uuid4()
    paid_action_name = "test_action"
    action_id = uuid.uuid4()
    price = Decimal("10.00")
    currency_type = CurrencyType(id=1, name="TOKEN")
    currency_type_service = CurrencyType(id=2, name="SERVICE")

    tariff_plan = TariffPlan(
        name="Test tariff plan",
        tokens_per_month=Decimal(100),
        duration_in_month=3,
        currency_type_id=1,
        month_price=Decimal(1000),
    )

    active_date = datetime.now(UTC) + timedelta(days=1)
    user_stats = UserPlan(user_id=user_id, expired_at=active_date, tariff_plan_id=tariff_plan.id)
    paid_action = PaidAction(id=action_id, name=paid_action_name, price=price)
    user_balance = UserBalance(user_id=user_id, balance_amount=Decimal("20.00"), currency_type_id=1)
    user_service_balance = UserBalance(user_id=user_id, currency_type_id=2)
    company_service_balance_id = os.environ.get("SERVICE_COMPANY_BALANCE_ID")
    company_service_balance_id = int(company_service_balance_id)
    company_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
    company_balance_id = int(os.environ.get("TOKEN_COMPANY_BALANCE_ID"))
    company_balance = UserBalance(
        id=company_balance_id, balance_amount=Decimal("0"), currency_type_id=1
    )
    company_service_balance = UserBalance(
        id=company_service_balance_id, balance_amount=Decimal("0"), currency_type_id=2
    )
    try:
        session.add_all(
            [
                user_stats,
                tariff_plan,
                user_balance,
                user_service_balance,
                company_balance,
                company_service_balance,
                currency_type,
                currency_type_service,
                paid_action,
            ]
        )
        session.commit()
        paid_action_dataset = get_paid_action_dataset(session, paid_action_name)
        process_paid_action(session, user_id, paid_action_dataset, SourceNames.WEB_SITE)
        session.commit()

        updated_user_balance = (
            session.exec(
                select(UserBalance).where(
                    (UserBalance.user_id == user_id)
                    & (UserBalance.balance_type.has(CurrencyType.name == "TOKEN"))
                )
            )
            .first()
            .balance_amount
        )
        updated_company_balance = (
            session.exec(
                select(UserBalance).where(
                    (UserBalance.id == company_balance_id)
                    & (UserBalance.balance_type.has(CurrencyType.name == "TOKEN"))
                )
            )
            .first()
            .balance_amount
        )
        updated_user_service_balance = (
            session.exec(
                select(UserBalance).where(
                    (UserBalance.user_id == user_id)
                    & (UserBalance.balance_type.has(CurrencyType.name == "SERVICE"))
                )
            )
            .first()
            .balance_amount
        )
        updated_company_service_balance = (
            session.exec(
                select(UserBalance).where(
                    (UserBalance.id == company_service_balance_id)
                    & (UserBalance.balance_type.has(CurrencyType.name == "SERVICE"))
                )
            )
            .first()
            .balance_amount
        )
        assert updated_user_service_balance == Decimal(1)
        assert updated_company_service_balance == Decimal(-1)
        assert updated_user_balance == Decimal("10.00")
        assert updated_company_balance == Decimal("10.00")
        # Check transactions tracing
        transactions = session.exec(select(Transaction)).all()
        assert len(transactions) == 4
        assert transactions[0].transaction_type == TopUpWithdrawTransactionTypes.FIRST_TYPE.value
        assert transactions[1].transaction_type == TopUpWithdrawTransactionTypes.SECOND_TYPE.value
        assert transactions[2].transaction_type == PurchaseSaleTransactionTypes.FIRST_TYPE.value
        assert transactions[3].transaction_type == PurchaseSaleTransactionTypes.SECOND_TYPE.value
    finally:
        # Clean up
        session.exec(delete(Transaction))
        session.delete(user_stats)
        session.delete(tariff_plan)
        session.commit()
        session.delete(user_balance)
        session.delete(user_service_balance)
        session.delete(company_balance)
        session.delete(company_service_balance)
        session.delete(currency_type)
        session.delete(currency_type_service)
        session.delete(paid_action)
        session.commit()


def test_user_plans_rls(session):
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        auth.delete_user_by_email("rlstest2@flirtello.com")
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
        session.add_all([tariff_plan, usd, token, service, company_trial_token_balance])
        session.commit()

        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        u1 = c_u1.auth.sign_up({"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}).user
        c_u2 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        u2 = c_u2.auth.sign_up({"email": "rlstest2@flirtello.com", "password": "qweqwe123123"}).user

        all_balances = session.exec(select(UserBalance)).all()
        assert len(all_balances) == 7

        result1 = c_u1.table("user_balances").select("*").execute()
        assert len(result1.data) == 1
        result2 = c_u2.table("user_balances").select("*").execute()
        assert len(result2.data) == 1

        all_user_plans = session.exec(select(UserPlan)).all()
        assert len(all_user_plans) == 2

        result1 = c_u1.table("user_plans").select("*").execute()
        assert len(result1.data) == 1
        result2 = c_u2.table("user_plans").select("*").execute()
        assert len(result2.data) == 1

    finally:
        c_u1.auth.sign_out()
        c_u2.auth.sign_out()

        auth.delete_user_by_email("rlstest1@flirtello.com")
        auth.delete_user_by_email("rlstest2@flirtello.com")
        session.exec(delete(Transaction))
        session.delete(tariff_plan)
        session.delete(company_trial_token_balance)
        session.delete(token)
        session.delete(usd)
        session.delete(service)
        session.commit()


def test_invoicing(session):
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        service_id = uuid.uuid4()
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = c_u1.auth.sign_up(
            {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
        ).user.id
        currency_type = CurrencyType(id=1, name="USD")
        session.add(currency_type)
        session.commit()
        invoice_id = create_invoice(
            session,
            user_id,
            service_id,
            ServiceTypes.TARIFF_PLAN,
            Decimal(1),
            1,
            "test/url",
        )
        expected_invoice = session.exec(select(Invoice).where(Invoice.id == invoice_id)).first()
        assert expected_invoice.status == InvoiceStatus.UNPAID
        pay_the_invoice(session, invoice_id)
        assert expected_invoice.status == InvoiceStatus.PAID
    finally:
        c_u1.auth.sign_out()

        auth.delete_user_by_email("rlstest1@flirtello.com")
        session.delete(currency_type)
        session.exec(delete(Transaction))
        session.exec(delete(Invoice).where(Invoice.id == invoice_id))
        session.commit()


def test_get_service_model(session):
    try:
        tariff_plan_id = uuid.uuid4()
        tariff_plan_trial_id = uuid.uuid4()
        tariff_plan = TariffPlan(
            id=tariff_plan_id,
            name="Trial",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=None,
            tariff_info=None,
            currency_type_id=None,
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
        session.add(tariff_plan)
        session.add(tariff_plan_trial)
        session.commit()
        sd = ServiceDataset(service_type=ServiceTypes.TARIFF_PLAN, service_id=tariff_plan_id)
        sd2 = ServiceDataset(service_type=ServiceTypes.TARIFF_PLAN, service_id=tariff_plan_trial_id)
        sd1 = ServiceDataset(service_type=ServiceTypes.TOKEN_PACK, service_id=tariff_plan_id)
        service = get_service_model(session, sd)
        assert service.id == tariff_plan_id
        with pytest.raises(NoSuchServiceError):
            service = get_service_model(session, sd1)

        with pytest.raises(NoSuchServiceError):
            service = get_service_model(session, sd2)

    finally:

        session.delete(tariff_plan)
        session.delete(tariff_plan_trial)
        session.commit()


def test_check_is_invoice_exist(session):
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        service_id = uuid.uuid4()
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = c_u1.auth.sign_up(
            {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
        ).user.id
        currency_type = CurrencyType(id=1, name="USD")
        session.add(currency_type)
        session.commit()
        invoice_id = create_invoice(
            session,
            user_id,
            service_id,
            ServiceTypes.TARIFF_PLAN,
            Decimal(1),
            1,
            "test/url",
        )
        iv = InvoiceValidator(session, invoice_id)
        with pytest.raises(NoSuchInvoiceError):
            InvoiceValidator(session, invoice_id=invoice_id + 1)

    finally:
        c_u1.auth.sign_out()
        auth.delete_user_by_email("rlstest1@flirtello.com")
        session.delete(currency_type)
        session.exec(delete(Transaction))

        session.exec(delete(Invoice).where(Invoice.id == invoice_id))
        session.commit()


def test_tariff_plan_processor(session):
    try:
        tariff_plan_id = uuid.uuid4()
        tariff_plan = TariffPlan(
            id=tariff_plan_id,
            name="Trial",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=3,
            tariff_info=None,
            currency_type_id=1,
            is_trial=False,
        )
        tariff_plan_trial_id = uuid.uuid4()
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
                tariff_plan_trial,
                tariff_plan,
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
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        tp = TariffPlanProcessor(session, user_id, sd, SourceNames.WEB_SITE)
        tp.sell_service(payment_system_balance_id=config.payment_system_balance_id)
        session.commit()
        transactions = session.exec(select(Transaction)).all()
        assert len(transactions) == 8
        is_tp_trial = tp.apply_service()
        assert is_tp_trial
        current_date = datetime.now(UTC).date()
        expected_date = (datetime.now(UTC) + relativedelta(months=3)).date()
        session.commit()
        updated_user_plan = session.exec(select(UserPlan).where(UserPlan.user_id == user_id)).first()
        assert expected_date == updated_user_plan.expired_at.date()
        instant_tariff_plan_debit(session, user_id, is_tp_trial, SourceNames.WEB_SITE)
        session.commit()
        transactions = session.exec(select(Transaction)).all()
        assert len(transactions) == 12

        # assert transactions[0].transaction_type == TopUpWithdrawTransactionTypes.FIRST_TYPE.value
        # assert transactions[1].transaction_type == TopUpWithdrawTransactionTypes.SECOND_TYPE.value
        # assert transactions[2].transaction_type == PurchaseSaleTransactionTypes.FIRST_TYPE.value
        # assert transactions[3].transaction_type == PurchaseSaleTransactionTypes.SECOND_TYPE.value

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


def test_token_pack_processor(session):
    try:
        token_pack_id = uuid.uuid4()
        token_pack = TokenPack(
            id=token_pack_id,
            name="Super",
            amount=Decimal(1234),
            price=Decimal(123),
            currency_type_id=1,
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
                token_pack,
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
        sd = ServiceDataset(service_type=ServiceTypes.TOKEN_PACK, service_id=token_pack_id)
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        tp = TokenPackProcessor(session, user_id, sd, SourceNames.WEB_SITE)
        tp.sell_service(payment_system_balance_id=config.payment_system_balance_id)
        session.commit()
        transactions = session.exec(select(Transaction)).all()
        assert len(transactions) == 8
        assert tp.apply_service() is None

        expected_date = (datetime.now(UTC) + relativedelta(years=1)).date()
        session.commit()
        updated_user_plan = session.exec(select(UserPlan).where(UserPlan.user_id == user_id)).first()
        assert len(updated_user_plan.token_batches) == 1
        assert updated_user_plan.token_batches[0].expiration_date.date() == expected_date

        # assert transactions[0].transaction_type == TopUpWithdrawTransactionTypes.FIRST_TYPE.value
        # assert transactions[1].transaction_type == TopUpWithdrawTransactionTypes.SECOND_TYPE.value
        # assert transactions[2].transaction_type == PurchaseSaleTransactionTypes.FIRST_TYPE.value
        # assert transactions[3].transaction_type == PurchaseSaleTransactionTypes.SECOND_TYPE.value

    finally:
        c_u1.auth.sign_out()

        auth.delete_user_by_email("rlstest1@flirtello.com")
        session.exec(delete(Transaction))
        session.exec(delete(TokenPack))
        session.exec(delete(UserBalance))
        session.exec(delete(CurrencyType))
        session.exec(delete(TokenBatch))
        session.exec(delete(UserPlan))
        session.commit()


def test_billing_views_content_filtering(session):
    try:
        tariff_plan_id = uuid.uuid4()
        tariff_plan = TariffPlan(
            id=tariff_plan_id,
            name="Trial",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=3,
            tariff_info=None,
            currency_type_id=1,
            is_trial=False,
        )
        tariff_plan_trial_id = uuid.uuid4()
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
        tariff_plan_archived_id = uuid.uuid4()
        tariff_plan_archived = TariffPlan(
            id=tariff_plan_archived_id,
            name="Trial",
            tokens_per_month=Decimal(1234),
            price=Decimal(123),
            duration_in_month=None,
            tariff_info=None,
            currency_type_id=None,
            is_trial=False,
            is_archived=True,
        )
        token_pack_id = uuid.uuid4()
        token_pack = TokenPack(
            id=token_pack_id,
            name="Super",
            amount=Decimal(1234),
            price=Decimal(123),
            currency_type_id=1,
        )
        token_pack_id_archived = uuid.uuid4()
        token_pack_archived = TokenPack(
            id=token_pack_id_archived,
            name="Super",
            amount=Decimal(1234),
            price=Decimal(123),
            currency_type_id=1,
            is_archived=True,
        )
        eur = CurrencyType(id=1, name="EUR")
        token = CurrencyType(id=2, name="TOKEN")
        service = CurrencyType(id=3, name="SERVICE")
        company_trial_token_balance = UserBalance(
            id=int(os.environ.get("TRIAL_TOKEN_COMPANY_BALANCE_ID")),
            currency_type_id=2,
            is_official=True,
        )
        company_eur_balance = UserBalance(
            id=int(os.environ.get("EUR_COMPANY_BALANCE_ID")), currency_type_id=1, is_official=True
        )
        company_payment_system_balance = UserBalance(
            id=int(os.environ.get("PAYMENT_SYSTEM_BALANCE_ID")), currency_type_id=1, is_official=True
        )
        company_token_balance = UserBalance(
            id=int(os.environ.get("TOKEN_COMPANY_BALANCE_ID")), currency_type_id=2, is_official=True
        )
        company_service_balance = UserBalance(
            id=int(os.environ.get("SERVICE_COMPANY_BALANCE_ID")),
            currency_type_id=3,
            is_official=True,
        )
        paid_action_public = PaidAction(name="test", price=Decimal(23), is_public=True)
        paid_action_private = PaidAction(name="test", price=Decimal(23), is_public=False)
        paid_action_archived = PaidAction(
            name="test", price=Decimal(23), is_archived=True, is_public=True
        )
        session.add_all(
            [
                token_pack,
                eur,
                token,
                service,
                company_trial_token_balance,
                company_eur_balance,
                company_payment_system_balance,
                company_token_balance,
                company_service_balance,
                paid_action_public,
                paid_action_archived,
                paid_action_private,
                tariff_plan_archived,
                tariff_plan_trial,
                tariff_plan,
                token_pack_archived,
            ]
        )
        session.commit()
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        # Check balances
        all_user_balances = session.exec(select(UserBalance)).all()
        assert len(all_user_balances) == 3 + 5

        result1 = c_u1.table("user_balances").select("*").execute()
        assert len(result1.data) == 1

        # Check paid actions
        all_paid_actions = session.exec(select(PaidAction)).all()
        assert len(all_paid_actions) == 3

        result1 = c_u1.table("paid_actions").select("*").execute()
        assert len(result1.data) == 1
        
        # Check tariff plans
        all_tp = session.exec(select(TariffPlan)).all()
        assert len(all_tp) == 3

        result1 = c_u1.table("tariff_plans").select("*").execute()
        assert len(result1.data) == 1
        
        # Check token packs
        all_tp = session.exec(select(TokenPack)).all()
        assert len(all_tp) == 2

        result1 = c_u1.table("token_packs").select("*").execute()
        assert len(result1.data) == 1
    finally:
        c_u1.auth.sign_out()

        auth.delete_user_by_email("rlstest1@flirtello.com")
        session.exec(delete(Transaction))
        session.exec(delete(TokenPack))
        session.exec(delete(TariffPlan))
        session.exec(delete(UserBalance))
        session.exec(delete(CurrencyType))
        session.exec(delete(TokenBatch))
        session.exec(delete(UserPlan))
        session.exec(delete(PaidAction))
        session.commit()
