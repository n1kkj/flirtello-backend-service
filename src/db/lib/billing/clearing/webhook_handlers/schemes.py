from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TruevoWebhookNotificationTypes(Enum):
    PAYMENT = "payment"
    REFUND = "refund"


class TruevoWebhookCredentialsType(Enum):
    RECURRENT = "recurrent"
    REGULAR = "regular"


class WebhookHandlingStatus(Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"


class TruevoWebhookData(BaseModel):
    webhook_credentials_type: TruevoWebhookCredentialsType
    mId: str
    url: str
    token: dict
    status: str
    country: str
    respMsg: str
    configId: str
    customer: dict
    language: str
    merchant: str
    provider: str
    respCode: int
    ipCountry: str
    txnAmount: str
    webhookId: str
    billingZip: str
    customerId: str
    statusCode: int
    acquirerMid: str
    paymentMode: str
    retryOption: int
    currencyCode: str
    customerName: str
    txnReference: str
    bankPaymentId: str
    customerEmail: str
    billingCountry: str
    acquirerRespMsg: str
    transactionDate: str
    acquirerRespCode: str
    deliveryAttempts: int
    firstAttemptDate: str
    notificationType: str
    paymentModeValue: str
    settlementAmount: str
    settlementStatus: str
    OriginalTxnStatus: str
    settlementCurrency: str
    reconciliationStatus: str
    OriginalTxnStatusCode: int

    model_config = ConfigDict(extra="ignore")
