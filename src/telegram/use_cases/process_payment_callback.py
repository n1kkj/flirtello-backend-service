from uuid import UUID

import sentry_sdk
from sqlmodel import Session

from src.db.lib.billing.common.enums import ServiceTypes, SourceNames
from src.db.lib.billing.common.exceptions import BillingError, NoSuchInvoiceError
from src.db.lib.billing.invoicing import InvoiceValidator, ServiceDataset
from src.db.lib.billing.service_processing import TokenPackProcessor
from src.db.lib.config import config as db_config
from src.telegram.config import TELEGRAM_STARS_TO_USD_CONVERSION_INDEX
from src.telegram.lib.i18n import get_gettext_for_language


async def process_payment_callback(
    invoice_id: str,
    telegram_payment_status: str,
    user_id: UUID,
    session: Session,
    lang_code: str = "en",
) -> str:
    """
    Process payment callback
    Returns message to send to user
    """
    _ = get_gettext_for_language(lang_code)
    if telegram_payment_status != "success":
        return _("Oops, something went wrong with your payment, darling! 💔 Let's try that again, shall we? 😘")
    try:
        invoice_validator = InvoiceValidator(session, invoice_id)

        if invoice_validator.is_invoice_paid():
            sentry_sdk.capture_message(f"Invoice {invoice_id} already paid", level="error")
            return _("Oh sweetie, looks like you've already paid for this one! 💝 Let's start fresh with a new purchase, shall we? 😉")
        service_type = invoice_validator.invoice.service_type
        service_id = invoice_validator.invoice.service_id
        service_dataset = ServiceDataset(service_type=service_type, service_id=service_id)

        if service_type == ServiceTypes.TOKEN_PACK:
            service_processor = TokenPackProcessor(
                session, user_id, service_dataset, SourceNames.TELEGRAM
            )
            payment_system_balance_id = db_config.telegram_stars_payment_system_balance_id
            service_processor.sell_service(
                payment_system_balance_id=payment_system_balance_id,
                additional_data={
                    "payment_system_transaction_id": invoice_id,
                    "telegram_stars_to_usd_conversion_index": TELEGRAM_STARS_TO_USD_CONVERSION_INDEX,
                },
            )
            service_processor.apply_service()
            session.commit()
            return _("Thank you, gorgeous! 💖 Your payment was successful. Now let's have some fun together! 😘")
        elif service_type == ServiceTypes.TARIFF_PLAN:
            return _("Oh honey, we're not selling tariff plans right now... but I've got something even better for you! 💋")
    except NoSuchInvoiceError:
        sentry_sdk.capture_message(f"Invoice {invoice_id} not found", level="error")
        return _("Oops! I can't find your payment details, darling. 💔 Let's start over and make it perfect this time! 😘")
    except BillingError as e:
        sentry_sdk.capture_exception(e)
        return _("Something's not quite right, sweetie! 🌹 {error_message} Let's try again? 💕").format(error_message=e.message)
