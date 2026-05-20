import os
import uuid
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import make_transient
from sqlmodel import Session, delete, select

from lib.auth import SupabaseAuth
from lib.billing.clearing.webhook_handlers.schemes import (
    TruevoWebhookCredentialsType,
    TruevoWebhookData,
    TruevoWebhookNotificationTypes,
    WebhookHandlingStatus,
)
from lib.billing.clearing.webhook_handlers.truevo_webhook_handler import (
    TruevoWebhookHandler,
)
from lib.billing.common.content_billing_models import (
    ContentWebhookData,
    CurrencyType,
    TariffPlan,
    TokenPack,
    Transaction,
    UserBalance,
)
from lib.billing.common.enums import PurchaseSaleTransactionTypes, ServiceTypes
from lib.billing.common.exceptions import NoPaymentSystemPlanIDError
from lib.billing.payment_system.enums import PaymentSystems
from lib.billing.payment_system.payment_system import Truevo
from lib.billing.payment_system.schemes import (
    InitialPaymentResponse,
    TransactionStatuses,
    TransactionStatusResponse,
    TransactionSubscription,
    TransactionSubscriptionInstallmentsInfo,
)
from supabase import create_client

load_dotenv()
DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"

dbschema = "content,public"

engine = create_engine(DATABASE_URL, connect_args={"options": "-csearch_path={}".format(dbschema)})

auth = SupabaseAuth(
    os.environ.get("API_URL"),
    os.environ.get("SERVICE_ROLE_KEY"),
    os.environ.get("PASSKEY"),
    engine,
)


@pytest.fixture(scope="function", autouse=True)
def db_data_backup(session: Session):
    content_webhook_data = session.exec(select(ContentWebhookData)).all()
    transactions = session.exec(select(Transaction)).all()
    for obj in content_webhook_data + transactions:
        session.expunge(obj)
        make_transient(obj)

    session.exec(delete(ContentWebhookData))
    session.exec(delete(Transaction))
    session.commit()

    yield session

    session.add_all(content_webhook_data)
    session.add_all(transactions)
    session.commit()


def get_mock_truevo_webhook_data(respCode: int):
    mock_data = MagicMock()
    mock_data.respCode = respCode
    return mock_data


def get_truevo_webhook_data() -> TruevoWebhookData:
    """
    Returns a mock instance of TruevoWebhookData with sample data.
    """
    return TruevoWebhookData(
        webhook_credentials_type=TruevoWebhookCredentialsType.REGULAR.value,
        mId="MID12345",
        url="https://example.com/webhook",
        token={"access_token": "sampletoken"},
        status="approved",
        country="US",
        respMsg="Transaction Successful",
        configId="CONFIG001",
        customer={"id": "cust001", "name": "Jane Doe"},
        language="en",
        merchant="MerchantXYZ",
        provider="ProviderABC",
        respCode=200,
        ipCountry="US",
        txnAmount="150.00",
        webhookId="WH123",
        billingZip="90210",
        customerId="cust001",
        statusCode=200,
        acquirerMid="ACQMID456",
        paymentMode="credit_card",
        retryOption=0,
        currencyCode="USD",
        customerName="Jane Doe",
        txnReference="TXN789",
        bankPaymentId="BANK123",
        customerEmail="jane@example.com",
        billingCountry="US",
        acquirerRespMsg="Approved",
        transactionDate=datetime.now(UTC).isoformat(),
        acquirerRespCode="00",
        deliveryAttempts=1,
        firstAttemptDate=datetime.now(UTC).isoformat(),
        notificationType="payment",  # Make sure this matches your expected values
        paymentModeValue="visa",
        settlementAmount="150.00",
        settlementStatus="completed",
        OriginalTxnStatus="approved",
        settlementCurrency="USD",
        reconciliationStatus="matched",
        OriginalTxnStatusCode=200,
    )


@pytest.fixture(scope="session")
def session():
    with Session(engine) as session:
        yield session
        session.rollback()


def create_truevo_mock(
    paid_installments: int,
    customer_id: str,
    plan_code: str,
    status: TransactionStatuses,
):
    mock_truevo = MagicMock(spec=Truevo)

    # Create the response object
    mock_response = TransactionStatusResponse(
        status=status,
        customerId=customer_id,
        respCode=200,
        subscription=TransactionSubscription(
            planCode=plan_code,
            installments=TransactionSubscriptionInstallmentsInfo(paidInstallments=paid_installments),
        ),
    )

    # Configure the mock to return our response
    mock_truevo.check_transaction_status.return_value = mock_response

    return mock_truevo


@pytest.fixture(scope="session")
def truevo_webhook_handler(session: Session):
    return TruevoWebhookHandler(
        payment_system=Truevo(use_test_server=True),
        session=session,
    )


def test_payment_system_type_checking(truevo_webhook_handler: TruevoWebhookHandler):
    webhook_content_data_truevo_payment_system = ContentWebhookData(
        payment_system_name=PaymentSystems.TRUEVO.value,
        is_handled=False,
        created_at=datetime.now(UTC),
    )
    webhook_content_data_other_payment_system = ContentWebhookData(
        payment_system_name=PaymentSystems.FAKE.value,
        is_handled=False,
        created_at=datetime.now(UTC),
    )
    assert truevo_webhook_handler._check_payment_system_type(
        webhook_content_data_truevo_payment_system
    )
    assert not truevo_webhook_handler._check_payment_system_type(
        webhook_content_data_other_payment_system
    )


def test_get_service_type_based_on_credentials(truevo_webhook_handler):
    assert (
        truevo_webhook_handler._get_service_type_based_on_credentials(
            TruevoWebhookCredentialsType.RECURRENT
        )
        == ServiceTypes.TARIFF_PLAN
    )
    assert (
        truevo_webhook_handler._get_service_type_based_on_credentials(
            TruevoWebhookCredentialsType.REGULAR
        )
        == ServiceTypes.TOKEN_PACK
    )


def test_check_transaction_response_code(truevo_webhook_handler):
    webhook_data_200 = get_mock_truevo_webhook_data(200)
    webhook_data_1032 = get_mock_truevo_webhook_data(1032)
    webhook_data_101 = get_mock_truevo_webhook_data(101)

    assert truevo_webhook_handler._check_transaction_response_code(webhook_data_200)
    assert not truevo_webhook_handler._check_transaction_response_code(webhook_data_101)
    assert truevo_webhook_handler._check_transaction_response_code(webhook_data_1032)


def test_is_webhook_notification_type_acceptable(truevo_webhook_handler):
    assert truevo_webhook_handler._is_webhook_notification_type_acceptable(
        TruevoWebhookNotificationTypes.PAYMENT.value
    )
    assert truevo_webhook_handler._is_webhook_notification_type_acceptable(
        TruevoWebhookNotificationTypes.REFUND.value
    )
    assert not truevo_webhook_handler._is_webhook_notification_type_acceptable("FAKE")


def test_is_first_subscription_installment(truevo_webhook_handler):
    mock_transaction_status_response = TransactionStatusResponse(
        subscription=TransactionSubscription(
            planCode="123", installments=TransactionSubscriptionInstallmentsInfo(paidInstallments=1)
        ),
        status=TransactionStatuses.SUCCESS,
        respCode=200,
        customerId="123",
    )
    assert truevo_webhook_handler._is_first_subscription_installment(
        mock_transaction_status_response
    )
    mock_transaction_status_response = TransactionStatusResponse(
        subscription=TransactionSubscription(
            planCode="123", installments=TransactionSubscriptionInstallmentsInfo(paidInstallments=2)
        ),
        status=TransactionStatuses.SUCCESS,
        respCode=200,
        customerId="123",
    )
    assert not truevo_webhook_handler._is_first_subscription_installment(
        mock_transaction_status_response
    )


def test_process_webhook_data_pre_checks(truevo_webhook_handler):
    webhook_notification_type_payment = TruevoWebhookNotificationTypes.PAYMENT.value
    webhook_notification_type_refund = TruevoWebhookNotificationTypes.REFUND.value
    webhook_notification_type_not_acceptable = "FAKE"
    truevo_webhook_data = get_truevo_webhook_data()

    mock_content_webhook_data = ContentWebhookData(
        id=uuid4(),
        payment_system_name=PaymentSystems.TRUEVO,
        is_handled=False,
        data={},
        created_at=datetime.now(UTC),
    )
    mock_transaction_status_response = TransactionStatusResponse(
        customerId="123",
        subscription=TransactionSubscription(
            planCode="123",
            installments=TransactionSubscriptionInstallmentsInfo(paidInstallments=1),
        ),
        status=TransactionStatuses.SUCCESS,
        respCode=200,
    )

    mock_transaction_status_response.subscription.installments.paidInstallments = 2
    mock_content_webhook_data.data = truevo_webhook_data
    # Test correct/wrong notification type
    assert truevo_webhook_handler._process_webhook_data_pre_checks(
        webhook_notification_type_payment,
        mock_content_webhook_data,
        mock_transaction_status_response,
    )
    assert not truevo_webhook_handler._process_webhook_data_pre_checks(
        webhook_notification_type_not_acceptable,
        mock_content_webhook_data,
        mock_transaction_status_response,
    )
    # Test refund + 2 installments
    assert truevo_webhook_handler._process_webhook_data_pre_checks(
        webhook_notification_type_refund,
        mock_content_webhook_data,
        mock_transaction_status_response,
    )
    # Test refund + 1 installment
    mock_transaction_status_response.subscription.installments.paidInstallments = 1
    assert truevo_webhook_handler._process_webhook_data_pre_checks(
        webhook_notification_type_refund,
        mock_content_webhook_data,
        mock_transaction_status_response,
    )
    # Test payment + 1 installments
    mock_transaction_status_response.subscription.installments.paidInstallments = 1
    assert not truevo_webhook_handler._process_webhook_data_pre_checks(
        webhook_notification_type_payment,
        mock_content_webhook_data,
        mock_transaction_status_response,
    )
    # Test payment + 2 installments + wrong subscription at transaction status
    mock_transaction_status_response.subscription = None
    assert not truevo_webhook_handler._process_webhook_data_pre_checks(
        webhook_notification_type_payment,
        mock_content_webhook_data,
        mock_transaction_status_response,
    )


def test_stream_webhook_data(truevo_webhook_handler):
    try:
        content_webhook_data_list = []
        content_webhook_data_list_received = []
        for i in range(10):
            content_webhook_data = ContentWebhookData(
                id=uuid4(),
                payment_system_name=PaymentSystems.TRUEVO.value,
                is_handled=False,
                data={},
                created_at=datetime.now(UTC),
            )
            content_webhook_data_list.append(content_webhook_data)
            truevo_webhook_handler.session.add(content_webhook_data)
            truevo_webhook_handler.session.flush()
        for content_webhook_data in truevo_webhook_handler.stream_webhook_data():
            assert content_webhook_data in content_webhook_data_list
            content_webhook_data_list_received.append(content_webhook_data)
        assert len(content_webhook_data_list) == len(content_webhook_data_list_received)
        for content_webhook_data in content_webhook_data_list_received[:5]:
            truevo_webhook_handler._mark_webhook_as_handled(content_webhook_data)
            truevo_webhook_handler.session.flush()
        content_webhook_data_list_received = []
        for content_webhook_data in truevo_webhook_handler.stream_webhook_data():
            content_webhook_data_list_received.append(content_webhook_data)
        assert len(content_webhook_data_list_received) == 5
        assert not content_webhook_data_list_received[0].is_handled

    finally:
        truevo_webhook_handler.session.rollback()


def test_handle_webhook_payment(truevo_webhook_handler):
    content_webhook_data = ContentWebhookData(
        id=uuid4(),
        payment_system_name=PaymentSystems.TRUEVO.value,
        is_handled=False,
        data={},
        created_at=datetime.now(UTC),
    )
    # Test invalid payment system type
    content_webhook_data.payment_system_name = PaymentSystems.FAKE.value
    assert (
        truevo_webhook_handler.handle_webhook(content_webhook_data) == WebhookHandlingStatus.SKIPPED
    )
    # Test invalid webhook event type
    content_webhook_data.data = get_truevo_webhook_data().model_dump()
    content_webhook_data.data["notificationType"] = "FAKE"
    assert (
        truevo_webhook_handler.handle_webhook(content_webhook_data) == WebhookHandlingStatus.SKIPPED
    )
    try:
        # Test successful payment
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        # Clean up user creation transaction
        truevo_webhook_handler.session.exec(
            delete(Transaction).where(Transaction.user_id == user_id)
        )

        tariff_plan_id = uuid4()
        tariff_plan = TariffPlan(
            id=tariff_plan_id,
            name="test_plan",
            price=Decimal("10.3"),
            tokens_per_month=Decimal(12321),
            duration_in_month=1,
            currency_type_id=3,
        )

        truevo_webhook_handler.session.add(tariff_plan)
        truevo_webhook_handler.session.flush()
        truevo_payment_system_mock = create_truevo_mock(
            paid_installments=2,
            customer_id=user_id.hex,
            plan_code=tariff_plan_id.hex,
            status=TransactionStatuses.SUCCESS,
        )
        truevo_webhook_handler.payment_system = truevo_payment_system_mock
        transaction_reference = uuid4()
        content_webhook_data.data["txnReference"] = transaction_reference.hex
        content_webhook_data.data["notificationType"] = TruevoWebhookNotificationTypes.PAYMENT.value
        content_webhook_data.data["customerId"] = user_id.hex
        content_webhook_data.payment_system_name = PaymentSystems.TRUEVO.value
        assert (
            truevo_webhook_handler.handle_webhook(content_webhook_data)
            == WebhookHandlingStatus.SUCCESS
        )
        truevo_webhook_handler.session.commit()

        transaction = truevo_webhook_handler.session.exec(
            select(Transaction).order_by(Transaction.created_at.asc())
        ).all()

        assert len(transaction) == 6
        assert transaction[0].user_id == user_id
        assert transaction[0].service_id == tariff_plan_id
        assert abs(transaction[0].amount) == Decimal("10.3")
        assert (
            transaction[0].additional_data["payment_system_transaction_id"]
            == transaction_reference.hex
        )
    finally:
        c_u1.auth.sign_out()
        auth.delete_user_by_email("rlstest1@flirtello.com")
        truevo_webhook_handler.session.rollback()


def test_handle_webhook_refund_tariff_plan(truevo_webhook_handler, session: Session):
    content_webhook_data = ContentWebhookData(
        id=uuid4(),
        payment_system_name=PaymentSystems.TRUEVO.value,
        is_handled=False,
        data={},
        created_at=datetime.now(UTC),
    )
    # Test invalid payment system type
    content_webhook_data.payment_system_name = PaymentSystems.FAKE.value
    assert (
        truevo_webhook_handler.handle_webhook(content_webhook_data) == WebhookHandlingStatus.SKIPPED
    )
    # Test invalid webhook event type
    content_webhook_data.data = get_truevo_webhook_data().model_dump()
    content_webhook_data.data["notificationType"] = "FAKE"
    assert (
        truevo_webhook_handler.handle_webhook(content_webhook_data) == WebhookHandlingStatus.SKIPPED
    )
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        # Clean up user creation transaction
        truevo_webhook_handler.session.exec(
            delete(Transaction).where(Transaction.user_id == user_id)
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
            created_at=datetime.now(UTC),
        )
        session.add(billing_transaction)
        session.add(tariff_plan)
        session.flush()

        truevo_webhook_handler.session.add(billing_transaction)
        truevo_webhook_handler.session.add(tariff_plan)
        truevo_webhook_handler.session.flush()

        truevo_payment_system_mock = create_truevo_mock(
            paid_installments=1,
            customer_id=user_id.hex,
            plan_code=tariff_plan.id.hex,
            status=TransactionStatuses.SUCCESS,
        )
        truevo_webhook_handler.payment_system = truevo_payment_system_mock
        content_webhook_data.payment_system_name = PaymentSystems.TRUEVO.value
        content_webhook_data.data["customerId"] = user_id.hex
        content_webhook_data.data["txnReference"] = payment_system_transaction_id
        content_webhook_data.data["notificationType"] = TruevoWebhookNotificationTypes.REFUND.value
        assert (
            truevo_webhook_handler.handle_webhook(content_webhook_data)
            == WebhookHandlingStatus.SUCCESS
        )
        truevo_webhook_handler.session.commit()
        eur_company_balance_amount_after = session.get(
            UserBalance, eur_company_balance_id
        ).balance_amount
        assert abs(eur_company_balance_amount_after - eur_company_balance_amount_before) == 12
        company_token_balance_amount_after = session.get(
            UserBalance, company_token_balance_id
        ).balance_amount
        assert abs(company_token_balance_amount_after - company_token_balance_amount_before) == 100
        transaction = session.exec(select(Transaction)).all()
        assert len(transaction) == 9
    finally:
        c_u1.auth.sign_out()
        auth.delete_user_by_email("rlstest1@flirtello.com")
        truevo_webhook_handler.session.rollback()


def test_handle_webhook_refund_token_pack(truevo_webhook_handler, session: Session):
    content_webhook_data = ContentWebhookData(
        id=uuid4(),
        payment_system_name=PaymentSystems.TRUEVO.value,
        is_handled=False,
        data={},
        created_at=datetime.now(UTC),
    )
    # Test invalid payment system type
    content_webhook_data.payment_system_name = PaymentSystems.FAKE.value
    assert (
        truevo_webhook_handler.handle_webhook(content_webhook_data) == WebhookHandlingStatus.SKIPPED
    )
    # Test invalid webhook event type
    content_webhook_data.data = get_truevo_webhook_data().model_dump()
    content_webhook_data.data["notificationType"] = "FAKE"
    assert (
        truevo_webhook_handler.handle_webhook(content_webhook_data) == WebhookHandlingStatus.SKIPPED
    )
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = uuid.UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        # Clean up user creation transaction
        truevo_webhook_handler.session.exec(
            delete(Transaction).where(Transaction.user_id == user_id)
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
            name="Test Token Pack",
            currency_type_id=3,
            amount=100,
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
            created_at=datetime.now(UTC),
        )

        truevo_webhook_handler.session.add(billing_transaction)
        truevo_webhook_handler.session.add(token_pack)
        truevo_webhook_handler.session.flush()

        truevo_payment_system_mock = create_truevo_mock(
            paid_installments=1,
            customer_id=user_id.hex,
            plan_code=token_pack.id.hex,
            status=TransactionStatuses.SUCCESS,
        )
        truevo_webhook_handler.payment_system = truevo_payment_system_mock
        content_webhook_data.payment_system_name = PaymentSystems.TRUEVO.value
        content_webhook_data.data["customerId"] = user_id.hex
        content_webhook_data.data["txnReference"] = payment_system_transaction_id
        content_webhook_data.data["notificationType"] = TruevoWebhookNotificationTypes.REFUND.value
        assert (
            truevo_webhook_handler.handle_webhook(content_webhook_data)
            == WebhookHandlingStatus.SUCCESS
        )
        truevo_webhook_handler.session.commit()
        eur_company_balance_amount_after = session.get(
            UserBalance, eur_company_balance_id
        ).balance_amount
        assert abs(eur_company_balance_amount_after - eur_company_balance_amount_before) == 12
        company_token_balance_amount_after = session.get(
            UserBalance, company_token_balance_id
        ).balance_amount
        assert abs(company_token_balance_amount_after - company_token_balance_amount_before) == 100
        transaction = session.exec(select(Transaction)).all()
        assert len(transaction) == 7
    finally:
        c_u1.auth.sign_out()
        auth.delete_user_by_email("rlstest1@flirtello.com")
        truevo_webhook_handler.session.rollback()
