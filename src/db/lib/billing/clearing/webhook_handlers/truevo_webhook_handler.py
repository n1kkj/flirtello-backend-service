import logging
import time
from typing import Type
from uuid import UUID

from pydantic_core import ValidationError
from sqlmodel import Session, select

from ....config import config
from ...common.content_billing_models import ContentWebhookData, Transaction
from ...common.enums import ServiceTypes, SourceNames
from ...invoicing import ServiceDataset
from ...payment_system.enums import PaymentSystems
from ...payment_system.payment_system import Truevo
from ...payment_system.schemes import TransactionStatusResponse
from ...refund import process_refund
from ...service_processing import TariffPlanProcessor
from ..clearing import mark_user_plan_as_paid
from .schemes import (
    TruevoWebhookCredentialsType,
    TruevoWebhookData,
    TruevoWebhookNotificationTypes,
    WebhookHandlingStatus,
)

logger = logging.getLogger(__name__)


class TruevoWebhookHandler:
    def __init__(
        self,
        payment_system: Truevo,
        session: Session,
    ):
        logger.info("Initializing TruevoWebhookHandler")
        self.payment_system = payment_system
        self.session = session

    def handle_webhook(self, webhook: ContentWebhookData) -> WebhookHandlingStatus:
        logger.info(f"Processing webhook: {webhook}")
        if not self._check_payment_system_type(webhook):
            logger.info(
                f"Invalid payment system type for webhook data ID: {webhook.id} {webhook.payment_system_name}. Skipping"
            )
            self._mark_webhook_as_handled(webhook)
            webhook.status = WebhookHandlingStatus.SKIPPED.value
            return WebhookHandlingStatus.SKIPPED
        webhook_data_model = TruevoWebhookData(**webhook.data)
        truevo_transaction_id = webhook_data_model.txnReference
        service_type = self._get_service_type_based_on_credentials(
            webhook_data_model.webhook_credentials_type
        )
        logger.debug(
            f"Checking transaction status for ID: {truevo_transaction_id}, service type: {service_type}"
        )

        transaction_status_model = self.payment_system.check_transaction_status(
            transaction_id=truevo_transaction_id,
            service_type=service_type,
        )
        webhook_with_parsed_data = webhook.model_copy(update={"data": webhook_data_model})
        if not self._process_webhook_data_pre_checks(
            webhook_notification_type=webhook_data_model.notificationType,
            payment_system_transaction_status=transaction_status_model,
            webhook_data=webhook_with_parsed_data,
        ):
            logger.info(f"Pre-checks failed for webhook ID: {webhook.id}")
            self._mark_webhook_as_handled(webhook)
            webhook.status = WebhookHandlingStatus.SKIPPED.value
            return WebhookHandlingStatus.SKIPPED

        if webhook_data_model.notificationType == TruevoWebhookNotificationTypes.PAYMENT.value:
            logger.info(f"Processing payment notification for webhook ID: {webhook.id}")
            service_type = ServiceTypes.TARIFF_PLAN
            service_dataset = ServiceDataset(
                service_id=UUID(transaction_status_model.subscription.planCode),
                service_type=service_type,
            )
            service_processor = TariffPlanProcessor(
                session=self.session,
                user_id=UUID(webhook_data_model.customerId),
                service_dataset=service_dataset,
                source_name=SourceNames.WEB_SITE,
            )
            service_processor.sell_service(
                payment_system_balance_id=config.truevo_payment_system_balance_id,
                additional_data={"payment_system_transaction_id": truevo_transaction_id},
            )
            mark_user_plan_as_paid(self.session, UUID(webhook_data_model.customerId))
            self._mark_webhook_as_handled(webhook)
            logger.info(
                f"Successfully processed payment webhook for transaction ID: {truevo_transaction_id}"
            )
            webhook.status = WebhookHandlingStatus.SUCCESS.value
            return WebhookHandlingStatus.SUCCESS

        elif webhook_data_model.notificationType == TruevoWebhookNotificationTypes.REFUND.value:
            logger.info(
                f"Processing refund notification for transaction ID: {truevo_transaction_id}"
            )
            process_refund(
                session=self.session,
                user_id=UUID(webhook_data_model.customerId),
                payment_system_transaction_id=truevo_transaction_id,
                payment_system_balance_id=config.truevo_payment_system_balance_id,
            )
            self._mark_webhook_as_handled(webhook)
            logger.info(
                f"Successfully processed refund webhook for transaction ID: {truevo_transaction_id}"
            )
            webhook.status = WebhookHandlingStatus.SUCCESS.value
            return WebhookHandlingStatus.SUCCESS

    def process_webhooks_continuously(self):
        logger.info("Processing webhooks continuously")
        for webhook in self.stream_webhook_data():
            try:
                self.handle_webhook(webhook)
                self.session.commit()
            except Exception as e:
                self.session.rollback()
                raise e

    def stream_webhook_data(self, chunk_size=2**22):
        stmt = (
            select(ContentWebhookData)
            .where(ContentWebhookData.is_handled == False)
            .with_for_update()
        )
        result = self.session.exec(stmt).yield_per(chunk_size)
        for row in result:
            yield row

    def _mark_webhook_as_handled(self, webhook: ContentWebhookData):
        webhook.is_handled = True

    def _process_webhook_data_pre_checks(
        self,
        webhook_notification_type: str,
        webhook_data: ContentWebhookData,
        payment_system_transaction_status: TransactionStatusResponse,
    ) -> bool:
        logger.debug(f"Running pre-checks for webhook ID: {webhook_data.id}")

        if not self._is_webhook_notification_type_acceptable(webhook_notification_type):
            logger.info(
                f"Unacceptable notification type: {webhook_notification_type} for webhook ID: {webhook_data.id}. Skipping"
            )
            return False

        if not self._check_transaction_response_code(webhook_data.data):
            logger.info(f"Invalid response code for webhook ID: {webhook_data.id}. Skipping")
            return False

        if webhook_notification_type == TruevoWebhookNotificationTypes.PAYMENT.value:
            if not payment_system_transaction_status.subscription:
                logger.info(
                    f"Received payment for token pack or another service, skipping: {webhook_data.id}. Skipping"
                )
                return False
            if self._is_first_subscription_installment(payment_system_transaction_status):
                logger.info(f"First subscription installment, skipping: {webhook_data.id}. Skipping")
                return False

        logger.debug(f"All pre-checks passed for webhook ID: {webhook_data.id}")
        return True

    def _is_first_subscription_installment(
        self,
        payment_system_transaction_status: TransactionStatusResponse,
    ) -> bool:
        if payment_system_transaction_status.subscription.installments.paidInstallments == 1:
            return True

    def _is_webhook_notification_type_acceptable(self, notification_type: str) -> bool:
        try:
            # Try to create enum member from the string value
            TruevoWebhookNotificationTypes(notification_type)
            return True
        except ValueError:
            # Return False if the notification type is not valid
            return False

    def _check_transaction_response_code(
        self,
        webhook_data: TruevoWebhookData,
    ) -> bool:
        # 200 and 1032 are success payment/refund response codes accordingly
        if webhook_data.respCode == 200 or webhook_data.respCode == 1032:
            logger.info(f"Acceptable webhook response code: {webhook_data.respCode}")
            return True

        return False

    def _get_service_type_based_on_credentials(
        self,
        webhook_credentials_type: TruevoWebhookCredentialsType,
    ) -> ServiceTypes:
        if webhook_credentials_type == TruevoWebhookCredentialsType.RECURRENT:
            return ServiceTypes.TARIFF_PLAN
        return ServiceTypes.TOKEN_PACK

    def _check_payment_system_type(self, webhook: ContentWebhookData) -> bool:
        if webhook.payment_system_name == PaymentSystems.TRUEVO.value:
            return True
        return False
