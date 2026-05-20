import json
import threading
from abc import ABC
from datetime import UTC, datetime
from decimal import Decimal
from logging import getLogger
from uuid import UUID, uuid4

import gateway
import requests
from pydantic import AnyUrl, ValidationError
from sqlmodel import Session, select, update

from ...config import config
from ..common.content_billing_models import TariffPlan, UserPlan
from ..common.enums import ServiceTypes
from ..common.exceptions import (
    InvalidResponseSchema,
    NoPaymentSystemPlanIDError,
    NotSuccessPaymentSystemResponseStatusError,
)
from .enums import PaymentSystemCurrencyTypes
from .schemes import (
    DeactivateSubscriptionResponse,
    InitialPaymentPayload,
    InitialPaymentResponse,
    PaymentResponse,
    PlanCreationResponse,
    SubscriptionCreationResponse,
    TransactionStatuses,
    TransactionStatusResponse,
)

logger = getLogger(__name__)


class BasePaymentSystem(ABC):
    pass


class Truevo(BasePaymentSystem):
    def __init__(self, use_test_server: bool):
        logger.debug("Initializing Truevo payment system")
        self._lock = threading.Lock()
        self.user_test_server = use_test_server
        self._setup_truevo_gateway(
            self.user_test_server,
            config.payment_system_api_key_recurrent.get_secret_value(),
            config.payment_system_token_recurrent.get_secret_value(),
            config.cert_folder_name_recurrent,
        )
        self.payment_currency = self._get_gateway_currency(config.payment_system_currency)
        logger.debug(
            f"Truevo payment system initialized with test server: {use_test_server} and currency: {self.payment_currency}"
        )

    def process_subscription(
        self,
        tariff_plan: TariffPlan,
        user_id: UUID,
        user_email: str,
        user_first_name: str,
        success_url: str,
        fail_url: str,
        cancel_url: str,
    ) -> InitialPaymentResponse:
        with self._lock:
            logger.info(f"Processing subscription for user {user_id} with email {user_email}")
            self._setup_truevo_gateway(
                self.user_test_server,
                config.payment_system_api_key_recurrent.get_secret_value(),
                config.payment_system_token_recurrent.get_secret_value(),
                config.cert_folder_name_recurrent,
            )

            subscription_id = self._create_subscription(
                tariff_plan=tariff_plan,
                user_id=user_id,
                user_email=user_email,
            )
            logger.debug(f"Created subscription with ID {subscription_id}")

            initial_payment_response = self._process_initial_payment(
                amount=float(tariff_plan.price),
                subscription_id=subscription_id,
                user_id=user_id,
                user_email=user_email,
                user_first_name=user_first_name,
                success_url=success_url,
                fail_url=fail_url,
                cancel_url=cancel_url,
            )
            initial_payment_response.subscription_id = subscription_id
            logger.debug(f"Initial payment response: {initial_payment_response}")
            return initial_payment_response

    def check_transaction_status(
        self, transaction_id: str, service_type: ServiceTypes
    ) -> TransactionStatusResponse:
        with self._lock:
            if service_type == ServiceTypes.TARIFF_PLAN:
                self._setup_truevo_gateway(
                    self.user_test_server,
                    config.payment_system_api_key_recurrent.get_secret_value(),
                    config.payment_system_token_recurrent.get_secret_value(),
                    config.cert_folder_name_recurrent,
                )
            elif service_type == ServiceTypes.TOKEN_PACK:
                self._setup_truevo_gateway(
                    self.user_test_server,
                    config.payment_system_api_key_regular.get_secret_value(),
                    config.payment_system_token_regular.get_secret_value(),
                    config.cert_folder_name_regular,
                )
            logger.info(f"Checking transaction status for transaction ID {transaction_id}")
            txn = gateway.Txn(uid=transaction_id)
            response = gateway.TransactionStatus(txn).send().json()
            logger.info(f"Transaction status response: {response}")
            if (
                response.get("response")
                and response["response"].get("responseCode")
                and response["response"].get("responseCode") == 101
            ):
                return TransactionStatusResponse(
                    status=TransactionStatuses.NOT_EXIST,
                    customerId=None,
                    respCode=101,
                )
            try:
                transaction_status = TransactionStatusResponse(**response)
                logger.debug(f"Transaction status: {transaction_status}")
            except ValidationError as e:
                raise InvalidResponseSchema(validation_error=e, response=response)
            return transaction_status

    def _create_plan(
        self,
        plan_name: str,
        amount: int,
        frequency: int,
        total_installments: int = 9999,
        period: str = "MONTH",
    ) -> PlanCreationResponse:
        logger.debug(f"Creating plan with name {plan_name}, amount {amount}, frequency {frequency}")
        plan_code = uuid4().hex

        installments = gateway.Installments(
            total_installments=total_installments,
            amount=float(amount),
            period=period,
            types="REGULAR",
            currency_code=gateway.Currency.USD,
            frequency=frequency,
            sequence=1,
        )
        response_dictionary = (
            gateway.CreatePlan(plan_name, plan_code, installements=installments).send().json()
        )
        plan_creation_response = PlanCreationResponse(**response_dictionary)
        logger.debug(f"Plan created successfully with ID {plan_creation_response.planId}")
        return plan_creation_response

    def _create_subscription(
        self,
        tariff_plan: TariffPlan,
        user_id: UUID,
        user_email: str,
    ) -> str:
        logger.info(f"Creating subscription for user {user_id} with email {user_email}")

        if not tariff_plan.payment_system_plan_id:
            raise NoPaymentSystemPlanIDError(tariff_plan.id)

        truevo_plan_id = tariff_plan.payment_system_plan_id
        logger.debug(f"Truevo plan id {truevo_plan_id} for tariff plan {tariff_plan.id}")

        txn = gateway.Txn(uuid4())
        channel = gateway.NotificationSettings(
            channel=gateway.Channel.email,
            value=user_email,
        )
        customer = gateway.Customer(billing=gateway.Address(firstname="Anonymous", lastname="User"))

        response = gateway.CreateSubscription(
            customer_id=user_id.hex,
            plan_id=truevo_plan_id,
            txn=txn,
            start_date=datetime.now(UTC).__str__(),
            quantity=1,
            automaticDebit=True,
            channel=channel,
            description=tariff_plan.name,
            customer=customer,
        ).send()

        if response.status_code != 200:
            raise NotSuccessPaymentSystemResponseStatusError(response.status_code, response.text)
        try:
            subscription = SubscriptionCreationResponse(**response.json())
        except ValidationError as e:
            raise InvalidResponseSchema(validation_error=e, response=response.json())
        logger.info(
            f"Subscription for user: {user_id} and tariff plan: {tariff_plan.id} created with id {subscription.subscriptionId}"
        )
        return subscription.subscriptionId

    def _process_initial_payment(
        self,
        amount: float,
        subscription_id: str,
        user_id: UUID,
        user_first_name: str,
        user_email: str,
        success_url: str,
        fail_url: str,
        cancel_url: str,
    ) -> InitialPaymentResponse:
        logger.info(f"Processing initial payment for subscription {subscription_id}")

        txn = gateway.Txn(None, amount, self.payment_currency)
        url = gateway.Url(
            success_url,
            fail_url,
            cancel_url,
        )
        billing = gateway.Address(firstname=user_first_name, email=user_email)
        customer = gateway.Customer(billing=billing)

        response = gateway.Payment(
            txn,
            user_id.hex,
            gateway.PaymentMethod(),
            url,
            subscription_id=subscription_id,
            customer=customer,
        )
        response.send()
        logger.debug(f"Response status code: {response.response.status_code}")

        if response.response.status_code == 200 and response.response.json().get("payLoad"):
            # Get POST action and value for further customer redirection
            response_payload = response.get_post_data()
        else:
            raise NotSuccessPaymentSystemResponseStatusError(
                response.response.status_code, response.response.text
            )
        try:
            response_model = InitialPaymentResponse(**response_payload)
            payload = InitialPaymentPayload(**json.loads(response_model.value.data))
        except ValidationError as e:
            raise InvalidResponseSchema(validation_error=e, response=response_payload)
        response_model.value.data = payload
        logger.info(f"Initial payment processed successfully: {response_model}")
        return response_model

    def get_payment_page_html(self, payment_response: InitialPaymentResponse) -> str:
        logger.debug(f"Getting payment page HTML for payment response {payment_response}")
        action_url = payment_response.action

        payload = payment_response.value.data.model_dump()

        response = requests.post(action_url, json=payload)
        if response.status_code == 200:
            return response.text
        else:
            raise NotSuccessPaymentSystemResponseStatusError(response.status_code, response.text)

    def process_service_selling(
        self,
        service_price: float,
        service_id: UUID,
        user_id: UUID,
        user_email: str,
        success_url: str,
        fail_url: str,
        cancel_url: str,
    ) -> PaymentResponse:
        with self._lock:
            logger.info(f"Generating payment link for service {service_id}")
            self._setup_truevo_gateway(
                self.user_test_server,
                config.payment_system_api_key_regular.get_secret_value(),
                config.payment_system_token_regular.get_secret_value(),
                config.cert_folder_name_regular,
            )

            txn = gateway.Txn(None, service_price, self.payment_currency)
            url = gateway.Url(
                success_url,
                fail_url,
                cancel_url,
            )
            customer = gateway.Customer(
                billing=gateway.Address(firstname="Anonymous", lastname="User", email=user_email)
            )

            response = gateway.Payment(
                txn,
                user_id.hex,
                gateway.PaymentMethod(),
                url,
                customer=customer,
            )
            response.send()
            logger.debug(f"Response status code: {response.response.status_code}")

            if response.response.status_code == 200 and response.response.json().get("payLoad"):
                # Get POST action and value for further customer redirection
                response_payload = response.get_post_data()
            else:
                raise NotSuccessPaymentSystemResponseStatusError(
                    response.response.status_code, response.response.text
                )
            try:
                response_model = PaymentResponse(**response_payload)
                payload = InitialPaymentPayload(**json.loads(response_model.value.data))
            except ValidationError as e:
                raise InvalidResponseSchema(validation_error=e, response=response_payload)
            response_model.value.data = payload
            logger.info(f"Payment processed successfully: {response_model}")
            return response_model

    def save_truevo_subscription_id(self, session: Session, user_id: UUID, subscription_id: str):
        stmt = (
            update(UserPlan)
            .where(UserPlan.user_id == user_id)
            .values(truevo_subscription_id=subscription_id)
        )
        session.exec(stmt)
        session.commit()

    def save_truevo_token_id(self, session: Session, user_id: UUID, token_id: str):
        stmt = update(UserPlan).where(UserPlan.user_id == user_id).values(truevo_token_id=token_id)
        session.exec(stmt)
        session.commit()

    def _get_gateway_currency(self, currency_type: PaymentSystemCurrencyTypes) -> gateway.Currency:
        return {
            PaymentSystemCurrencyTypes.USD: gateway.Currency.USD,
            PaymentSystemCurrencyTypes.EUR: gateway.Currency.EUR,
        }[currency_type]

    def _setup_truevo_gateway(
        self,
        use_test_server: bool,
        api_key: str,
        token: str,
        cert_path: str,
    ) -> None:
        truevo_api = gateway.configure(
            api_key,
            token,
            f"{cert_path}/{config.public_key_name}",
        )
        if not use_test_server:
            truevo_api.live()

    def deactivate_subscription(self, subscription_id: str) -> None:
        self._setup_truevo_gateway(
            self.user_test_server,
            config.payment_system_api_key_recurrent.get_secret_value(),
            config.payment_system_token_recurrent.get_secret_value(),
            config.cert_folder_name_recurrent,
        )

        response_dictionary = gateway.DeactivateSubscription(subscription_id).send().json()
        try:
            response_model = DeactivateSubscriptionResponse(**response_dictionary)
        except ValidationError as e:
            raise InvalidResponseSchema(validation_error=e, response=response_dictionary)
        logger.info(f"Deactivated subscription {subscription_id} with response {response_model}")
        return response_model
