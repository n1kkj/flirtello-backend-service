from enum import Enum


class PaymentStatus(Enum):
    SUCCESS = "success"
    FAIL = "fail"
    CANCELED = "canceled"
