from decimal import Decimal
from uuid import UUID

from src.telegram.config import TELEGRAM_STARS_TO_USD_CONVERSION_INDEX


def convert_usd_to_stars_price(usd_price: Decimal, service_id: UUID) -> int:
    if service_id == UUID(
        "6d16f992-2c7e-4bfd-aa67-4cb625700fd6"
    ):  # TODO Only for test delete after testing
        return 1
    return int(usd_price * Decimal(TELEGRAM_STARS_TO_USD_CONVERSION_INDEX))
