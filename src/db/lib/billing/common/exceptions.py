from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError

from .enums import ServiceTypes


class BillingError(Exception):
    @property
    def message(self):
        return "An error occurred during billing execution"


class NotEnoughCurrencyError(BillingError):
    def __init__(self, user_currency_amount: Decimal, required_currency_amount: Decimal) -> None:
        self.user_currency_amount = user_currency_amount
        self.required_currency_amount = required_currency_amount

    @property
    def message(self):
        return f"Not enough currency. You have {self.user_currency_amount}, but action required {self.required_currency_amount}"


class TariffPlanExpired(BillingError):
    def __init__(
        self,
        expired_at: datetime,
        tariff_plan_name: str,
    ) -> None:
        self.expired_at = expired_at
        self.tariff_plan_name = tariff_plan_name

    @property
    def message(self):
        return f"Your tariff plan {self.tariff_plan_name} expired at {self.expired_at.year}.{self.expired_at.month}.{self.expired_at.day} in {self.expired_at.hour}:{self.expired_at.minute}"


class NoSuchServiceError(BillingError):
    def __init__(self, service_id: UUID, service_type: ServiceTypes) -> None:
        self.service_id = service_id
        self.service_type = service_type

    @property
    def message(self):
        return (
            f"No service with service id = {self.service_id} and service type = {self.service_type}"
        )


class NoSuchInvoiceError(BillingError):
    def __init__(self, invoice_id: int) -> None:
        self.invoice_id = invoice_id

    @property
    def message(self):
        return f"No invoice with invoice id = {self.invoice_id}"


class UnableProcessClearingWithTrialTariffPlan(BillingError):
    @property
    def message(self):
        return f"Can't process clearing for user with trial tariff plan"


class PaymentSystemError(BillingError):
    @property
    def message(self):
        return "An error occurred during payment system execution"


class NoPaymentSystemPlanIDError(PaymentSystemError):
    def __init__(self, tariff_plan_id: UUID) -> None:
        self.tariff_plan_id = tariff_plan_id

    @property
    def message(self):
        return f"Can't process purchasing without payment system plan id for tariff plan {self.tariff_plan_id}"


class NotSuccessPaymentSystemResponseStatusError(PaymentSystemError):
    def __init__(self, status_code: int, api_message: str) -> None:
        self.status_code = status_code
        self.api_message = api_message

    @property
    def message(self):
        return f"Unsuccess status {self.status_code} while trying to interact with payment system, error text: {self.api_message}"


class InvalidResponseSchema(PaymentSystemError):
    def __init__(self, validation_error: ValidationError, response: dict) -> None:
        self.validation_error = validation_error
        self.response = response

    @property
    def message(self):
        return f"Validation error: {self.validation_error}, for response: {self.response}"
