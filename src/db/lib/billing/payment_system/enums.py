from enum import Enum


class PaymentSystemCurrencyTypes(Enum):
    USD = "USD"
    EUR = "EUR"


class PaymentSystems(Enum):
    FAKE = "fake"
    TRUEVO = "truevo"
    TELEGRAM_STARS = "telegram_stars"
