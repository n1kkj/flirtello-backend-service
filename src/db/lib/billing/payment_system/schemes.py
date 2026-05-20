from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PlanCreationResponse(BaseModel):
    planId: str

    model_config = ConfigDict(extra="ignore")


class SubscriptionCreationResponse(BaseModel):
    subscriptionId: str

    model_config = ConfigDict(extra="ignore")


class InitialPaymentPayload(BaseModel):
    payLoad: str
    apiKey: str
    lang: str

    model_config = ConfigDict(extra="ignore")


class InitialPaymentData(BaseModel):
    data: bytes | InitialPaymentPayload

    model_config = ConfigDict(extra="ignore")


class InitialPaymentResponse(BaseModel):
    action: str
    value: InitialPaymentData
    subscription_id: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class PaymentResponse(BaseModel):
    action: str
    value: InitialPaymentData

    model_config = ConfigDict(extra="ignore")


class TransactionStatuses(Enum):
    SUCCESS = "Successful"
    FAIL = "Failed"
    PENDING = "Pending"
    NOT_EXIST = "Not exist"


class TransactionCardDetails(BaseModel):
    tokenId: str


class TransactionSubscriptionInstallmentsInfo(BaseModel):
    paidInstallments: int


class TransactionSubscription(BaseModel):
    planCode: str
    installments: TransactionSubscriptionInstallmentsInfo


class TransactionStatusResponse(BaseModel):
    status: Optional[TransactionStatuses]
    customerId: Optional[str]
    respCode: Optional[int]
    subscription: Optional[TransactionSubscription] = None
    card: Optional[TransactionCardDetails] = None

    model_config = ConfigDict(extra="ignore")


class DeactivateSubscriptionResponse_model(BaseModel):
    responseCode: int
    description: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class DeactivateSubscriptionResponse(BaseModel):
    response: DeactivateSubscriptionResponse_model
    model_config = ConfigDict(extra="ignore")
