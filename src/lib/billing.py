from enum import Enum
from uuid import UUID

from sqlmodel import Session, insert, select, update

from src.db.lib.billing.common.content_billing_models import (
    TariffPlan,
    Transaction,
    UserPlan,
)
from src.db.lib.billing.common.enums import PaidActions
from src.db.lib.billing.payment_system.enums import PaymentSystems
from src.db.lib.config import config as db_config
from src.db.lib.images import IMAGE_TYPES


# TODO maybe cache
def get_user_current_tariff_plan(session: Session, user_id: UUID) -> TariffPlan:
    stmt = select(UserPlan).where(UserPlan.user_id == user_id)
    res = session.exec(stmt).first()
    return res.tariff_plan


def map_bff_image_type_to_paid_action_name(image_type: str) -> str:
    image_mapper = {
        IMAGE_TYPES[0]: PaidActions.PHOTO.value.SAFE_PHOTO.value,
        IMAGE_TYPES[1]: PaidActions.PHOTO.value.QUEST_PHOTO.value,
        IMAGE_TYPES[2]: PaidActions.PHOTO.value.NUDE_PHOTO.value,
        IMAGE_TYPES[3]: PaidActions.PHOTO.value.EXPLICIT_PHOTO.value,
    }

    return image_mapper[image_type]


def map_bff_unblur_image_type_to_paid_action_name(image_type: str) -> str:
    unblur_image_mapper = {
        IMAGE_TYPES[0]: PaidActions.UNBLUR.value.UNBLUR_SAFE_PHOTO.value,
        IMAGE_TYPES[1]: PaidActions.UNBLUR.value.UNBLUR_QUEST_PHOTO.value,
        IMAGE_TYPES[2]: PaidActions.UNBLUR.value.UNBLUR_NUDE_PHOTO.value,
        IMAGE_TYPES[3]: PaidActions.UNBLUR.value.UNBLUR_EXPLICIT_PHOTO.value,
        "profile": PaidActions.UNBLUR.value.UNBLUR_PROFILE_PHOTO.value,
        "defect": PaidActions.UNBLUR.value.UNBLUR_DEFECT_PHOTO.value,
    }
    return unblur_image_mapper[image_type]


def map_current_payment_system_to_billing_balance(current_payment_system: PaymentSystems) -> int:
    payment_system_mapper = {
        PaymentSystems.FAKE: db_config.payment_system_balance_id,
        PaymentSystems.TRUEVO: db_config.truevo_payment_system_balance_id,
    }
    return payment_system_mapper[current_payment_system]


def check_if_user_has_purchases(session: Session, user_id: UUID) -> bool:
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .where(Transaction.balance_id_from == db_config.eur_company_balance_id)
    )
    res = session.exec(stmt).first()
    return bool(res)
