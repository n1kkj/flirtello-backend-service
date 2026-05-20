import os
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlmodel import Session

from lib.billing.common.content_billing_models import TariffPlan, TokenPack
from lib.billing.common.enums import ServiceTypes
from lib.billing.common.exceptions import NoPaymentSystemPlanIDError
from lib.billing.payment_system.payment_system import Truevo
from lib.billing.payment_system.schemes import (
    InitialPaymentResponse,
    TransactionStatuses,
)

load_dotenv()
DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"

dbschema = "content,public"

engine = create_engine(DATABASE_URL, connect_args={"options": "-csearch_path={}".format(dbschema)})


@pytest.fixture(scope="session")
def session():
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="session")
def truevo():
    return Truevo(use_test_server=True)


def test_invalid_tariff_plan_submission(truevo: "Truevo"):
    tariff_plan = TariffPlan(
        name="Test tariff plan",
        tokens_per_month=Decimal(100),
        duration_in_month=3,
        currency_type_id=1,
        price=Decimal(1000),
    )
    user_id = uuid4()
    user_email = "example@gmail.com"
    with pytest.raises(NoPaymentSystemPlanIDError):
        truevo._create_subscription(tariff_plan, user_id, user_email)


def test_valid_tariff_plan_submission(truevo: "Truevo"):
    plan_id = truevo._create_plan("Test tariff plan", 1000, 3).planId
    tariff_plan = TariffPlan(
        name="Test tariff plan",
        tokens_per_month=Decimal(100),
        duration_in_month=3,
        currency_type_id=1,
        price=Decimal(1000),
        payment_system_plan_id=plan_id,
    )
    user_id = uuid4()
    user_email = "example@gmail.com"

    subscription_id = truevo._create_subscription(tariff_plan, user_id, user_email)
    assert UUID(subscription_id)


def test_initial_payment(truevo: "Truevo"):
    plan_id = truevo._create_plan("Test tariff plan", 10.11, 3).planId
    tariff_plan = TariffPlan(
        name="Test tariff plan",
        tokens_per_month=Decimal(100),
        duration_in_month=3,
        currency_type_id=1,
        price=10.11,
        payment_system_plan_id=plan_id,
    )
    user_id = uuid4()
    user_email = "example@gmail.com"
    subscription_id = truevo._create_subscription(tariff_plan, user_id, user_email)
    success_url = "https://example.com/success"
    fail_url = "https://example.com/success&fail"
    cancel_url = "https://example.com/success&cancel"
    initial_payment_response = truevo._process_initial_payment(
        10.11,
        subscription_id,
        user_id,
        "Tester",
        user_email,
        success_url,
        fail_url,
        cancel_url,
    )
    expected_response = InitialPaymentResponse(
        action=initial_payment_response.action,
        value=initial_payment_response.value,
    )
    assert initial_payment_response == expected_response


def test_existing_transaction_status(truevo: "Truevo"):
    # HARDCODED(only at test setup)
    txn_reference = "905f13da-bcf5-4d57-bce3-2ee840235dfa"
    status = truevo.check_transaction_status(txn_reference, ServiceTypes.TOKEN_PACK)
    assert status.status == TransactionStatuses.SUCCESS
    # HARDCODED(only at test setup)
    assert status.customerId == "bf42f8e7ec92435b8503320ffa0123fc"


def test_not_existing_transaction_status(truevo: "Truevo"):
    txn_reference = "not_existing_transaction"
    status = truevo.check_transaction_status(txn_reference, ServiceTypes.TARIFF_PLAN)
    assert status.status == TransactionStatuses.NOT_EXIST
    assert status.customerId is None


def test_process_subscription(truevo: "Truevo"):
    duration_in_month = 3
    month_price = Decimal(11)
    plan_id = truevo._create_plan("Test tariff plan", month_price, duration_in_month).planId
    tariff_plan = TariffPlan(
        name="Test tariff plan",
        tokens_per_month=Decimal(100),
        duration_in_month=duration_in_month,
        currency_type_id=1,
        price=month_price,
        payment_system_plan_id=plan_id,
    )
    user_id = uuid4()
    user_email = "example@gmail.com"
    success_url = "https://example.com/success"
    fail_url = "https://example.com/success&fail"
    cancel_url = "https://example.com/success&cancel"

    initial_payment_response = truevo.process_subscription(
        tariff_plan,
        user_id,
        user_email,
        "Tester",
        success_url,
        fail_url,
        cancel_url,
    )
    expected_response = InitialPaymentResponse(
        action=initial_payment_response.action,
        value=initial_payment_response.value,
        subscription_id=initial_payment_response.subscription_id,
    )
    assert initial_payment_response == expected_response
    assert truevo.get_payment_page_html(initial_payment_response)


@pytest.mark.skip(reason="Transaction don't exist until user don't open payment link")
def test_transaction_status(truevo: "Truevo"):
    duration_in_month = 3
    month_price = 1000
    plan_id = truevo._create_plan("Test tariff plan", month_price, duration_in_month).planId
    tariff_plan = TariffPlan(
        name="Test tariff plan",
        tokens_per_month=Decimal(100),
        duration_in_month=duration_in_month,
        currency_type_id=1,
        month_price=month_price,
        payment_system_plan_id=plan_id,
    )
    user_id = uuid4()
    user_email = "example@gmail.com"
    success_url = "https://example.com/success"
    fail_url = "https://example.com/success&fail"
    cancel_url = "https://example.com/success&cancel"

    initial_payment_response = truevo.process_subscription(
        tariff_plan,
        user_id,
        user_email,
        "Tester",
        success_url,
        fail_url,
        cancel_url,
    )
    txn_reference = initial_payment_response.txnReference
    status = truevo.check_transaction_status(txn_reference)
    assert status.status == TransactionStatuses.PENDING


def test_service_selling(truevo: "Truevo"):
    price = 1000
    token_pack_id = uuid4()
    user_id = uuid4()
    user_email = "example@gmail.com"
    success_url = "https://example.com/success"
    fail_url = "https://example.com/success&fail"
    cancel_url = "https://example.com/success&cancel"

    payment_response = truevo.process_service_selling(
        float(price), token_pack_id, user_id, user_email, success_url, fail_url, cancel_url
    )
    assert payment_response


def test_deactivate_subscription(truevo: "Truevo"):
    duration_in_month = 3
    month_price = 1000
    plan_id = truevo._create_plan("Test tariff plan", month_price, duration_in_month).planId
    tariff_plan = TariffPlan(
        name="Test tariff plan",
        tokens_per_month=Decimal(100),
        duration_in_month=duration_in_month,
        currency_type_id=1,
        price=month_price,
        payment_system_plan_id=plan_id,
    )
    user_id = uuid4()
    user_email = "example@gmail.com"
    success_url = "https://example.com/success"
    fail_url = "https://example.com/success&fail"
    cancel_url = "https://example.com/success&cancel"

    initial_payment_response = truevo.process_subscription(
        tariff_plan,
        user_id,
        user_email,
        "Tester",
        success_url,
        fail_url,
        cancel_url,
    )
    subscription_id = initial_payment_response.subscription_id
    response = truevo.deactivate_subscription(subscription_id)

