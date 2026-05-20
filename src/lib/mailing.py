from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session

from src.db.lib.billing.common.content_billing_models import TariffPlan, TokenPack
from src.db.lib.billing.common.enums import ServiceTypes
from src.db.lib.config import config as db_config


@dataclass
class MailingDTO:
    subject: str
    dynamic_template_id: str
    dynamic_template_data: dict[str, str]


def get_mailing_dto(
    session: Session,
    service_type: ServiceTypes,
    service_id: UUID,
    invoice_id: int,
    total_price: float,
    tariff_plan_expiration_date: Optional[str] = None,
) -> MailingDTO:
    if service_type == ServiceTypes.TARIFF_PLAN:
        service_entity = session.get(TariffPlan, service_id)
        service_name = f"Tariff plan - {service_entity.name}"
        subject = "Your subscription is activated!"
        earned_tokens = service_entity.tokens_per_month
        duration = f"{service_entity.duration_in_month} month"
        dynamic_template_data = {
            "payment_id": f"{invoice_id}",
            "amount_paid": f"{total_price}",
            "date_paid": f"{date.today()}",
            "paid_name": service_name,
            "earned_tokens": f"{earned_tokens}",
            "tariff_plan_until": f"{tariff_plan_expiration_date}",
            "duration": duration + "s" if service_entity.duration_in_month > 1 else duration,
        }
        dynamic_template_id = db_config.sendgrid_tariff_plan_dynamic_template_id
    elif service_type == ServiceTypes.TOKEN_PACK:
        service_entity = session.get(TokenPack, service_id)
        subject = "Your tokens are credited!"
        service_name = f"Token pack"
        earned_tokens = service_entity.amount
        dynamic_template_data = {
            "payment_id": f"{invoice_id}",
            "amount_paid": f"{total_price}",
            "date_paid": f"{date.today()}",
            "paid_name": service_name,
            "earned_tokens": f"{earned_tokens}",
        }
        dynamic_template_id = db_config.sendgrid_token_pack_dynamic_template_id
    return MailingDTO(
        subject=subject,
        dynamic_template_id=dynamic_template_id,
        dynamic_template_data=dynamic_template_data,
    )
