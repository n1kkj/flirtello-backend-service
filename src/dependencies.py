import os
from typing import Annotated, Any, Callable, Coroutine

from fastapi import Depends
from fastapi.security import HTTPBearer
from sqlmodel import Session, create_engine

from src.db.lib.auth import SupabaseAuth
from src.db.lib.billing.payment_system.payment_system import Truevo
from src.db.lib.config import config as db_config
from src.db.lib.gift_codes.repository import GiftCodeRepository
from src.db.lib.mailing.sendgrid_mailer import SendGridMailer
from src.lib.config import config
from src.lib.verifier import TokenData, TokenVerifier

http_bearer = HTTPBearer()
verifier = TokenVerifier(config.supabase_url, config.supabase_anon_key)
engine = create_engine(config.database_url)


def get_auth() -> SupabaseAuth:
    return SupabaseAuth(
        config.supabase_url, os.environ.get("SERVICE_ROLE_KEY"), os.environ.get("PASSKEY"), engine
    )


async def get_current_user(token: Annotated[str, Depends(http_bearer)]):
    return await verifier.get_current_user(token)


async def get_session():
    with Session(engine) as session:
        yield session


def get_payment_system():
    use_test_server = config.use_payment_system_test_server
    return Truevo(use_test_server)


def get_mailer():
    api_key = db_config.sendgrid_api_key.get_secret_value()
    return SendGridMailer(api_key)


def get_gift_code_activator(session: Session = Depends(get_session)):
    return GiftCodeRepository(session)


# Фабрика для создания отладочной зависимости с заданным user_id
def get_debug_user(user_id: str) -> Callable[[], Coroutine[Any, Any, TokenData]]:
    async def _get_user() -> TokenData:
        return TokenData(user_id=user_id)

    return _get_user
