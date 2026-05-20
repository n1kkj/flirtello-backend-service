from enum import Enum


class PhotoTypes(Enum):
    SAFE_PHOTO = "SAFE_PHOTO"
    QUEST_PHOTO = "QUEST_PHOTO"
    NUDE_PHOTO = "NUDE_PHOTO"
    EXPLICIT_PHOTO = "EXPLICIT_PHOTO"


class UnblurTypes(Enum):
    UNBLUR_SAFE_PHOTO = "UNBLUR_SAFE_PHOTO"
    UNBLUR_QUEST_PHOTO = "UNBLUR_QUEST_PHOTO"
    UNBLUR_NUDE_PHOTO = "UNBLUR_NUDE_PHOTO"
    UNBLUR_EXPLICIT_PHOTO = "UNBLUR_EXPLICIT_PHOTO"
    UNBLUR_PROFILE_PHOTO = "UNBLUR_PROFILE_PHOTO"
    UNBLUR_DEFECT_PHOTO = "UNBLUR_DEFECT_PHOTO"


class PaidActions(Enum):
    MESSAGE = "MESSAGE"
    PHOTO = PhotoTypes
    UNBLUR = UnblurTypes
    SPEECH_TO_TEXT = "SPEECH_TO_TEXT"
    TEXT_TO_SPEECH = "TEXT_TO_SPEECH"


class TransactionTypes(Enum):
    pass


class PurchaseSaleTransactionTypes(TransactionTypes):
    FIRST_TYPE = "SALE"
    SECOND_TYPE = "PURCHASE"


class TopUpWithdrawTransactionTypes(TransactionTypes):
    FIRST_TYPE = "BALANCE_WITHDRAW"
    SECOND_TYPE = "BALANCE_TOP_UP"


class SourceNames(Enum):
    WEB_SITE = "WEB_SITE"
    TELEGRAM = "TELEGRAM"
    TELEGRAM_VOICE_MESSAGE = "TELEGRAM_VOICE_MESSAGE"


class CurrenciesTypes(Enum):
    TOKEN = "TOKEN"
    SERVICE = "SERVICE"
    USD = "USD"


class InvoiceStatus(Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"


class ServiceTypes(Enum):
    TARIFF_PLAN = "TARIFF_PLAN"
    TOKEN_PACK = "TOKEN_PACK"
