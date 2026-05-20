import logging
from uuid import UUID

from sqlmodel import Session

from src.db.lib.billing.invoicing import (
    ServiceDataset,
    create_invoice,
    get_service_model,
)
from src.db.lib.billing.payment_system.enums import PaymentSystems
from src.telegram.config import TELEGRAM_BOT_TOKEN
from src.telegram.utils.convert_usd_to_start_price import convert_usd_to_stars_price
from src.telegram.utils.create_tg_invoice_link import create_tg_invoice_link

logger = logging.getLogger(__name__)


async def process_stars_payment(
    user_id: UUID,
    service_dataset: ServiceDataset,
    session: Session,
) -> str:
    """
    Process stars payment

    Args:
        user_id (UUID): user id
        service_dataset (ServiceDataset): service dataset
        session (Session): session

    Returns:
        str: return invoice link for web app
    """

    service_model = get_service_model(session, service_dataset)
    service_id = service_model.id
    service_price = service_model.price
    service_currency_id = service_model.currency_type_id

    invoice_id = create_invoice(
        session,
        user_id,
        service_id,
        service_dataset.service_type,
        service_price,
        service_currency_id,
        "https://t.me/eemangel_bot",  # No callback url for stars payment
        payment_system_name=PaymentSystems.TELEGRAM_STARS,
    )
    star_price = convert_usd_to_stars_price(service_price, service_id)
    invoice_link = await create_tg_invoice_link(
        bot_token=TELEGRAM_BOT_TOKEN,
        title=service_model.name,
        description=f"Payment for {service_model.name}",
        payload={"invoice_id": str(invoice_id)},
        prices=[{"label": service_model.name, "amount": star_price}],  # convert from usd to stars
    )
    return invoice_link
