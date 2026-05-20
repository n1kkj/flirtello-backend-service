import logging
import os

from sqlmodel import Session, create_engine

from ...config import config
from ..payment_system.payment_system import Truevo
from .clearing import process_clearing
from .webhook_handlers.truevo_webhook_handler import TruevoWebhookHandler

engine = create_engine(os.environ.get("DB_URL"), isolation_level="SERIALIZABLE")
logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    with Session(engine) as session:
        handler = TruevoWebhookHandler(
            payment_system=Truevo(use_test_server=config.use_payment_system_test_server),
            session=session,
        )
        handler.process_webhooks_continuously()

    with Session(engine) as session:
        process_clearing(session)


if __name__ == "__main__":
    main()


# python3 -m lib.billing.clearing.scheduler
