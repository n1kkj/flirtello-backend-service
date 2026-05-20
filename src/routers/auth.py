import hashlib
import hmac
import json
import logging
from typing import Dict
from urllib.parse import parse_qs, parse_qsl, unquote

import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.lib.auth import SupabaseAuth
from src.dependencies import get_auth, get_current_user
from src.lib.config import config
from src.schemas.auth import TelegramAuthRequest, TelegramAuthResponse, TelegramUser
from src.telegram.dependecies import get_async_session
from src.telegram.utils.get_user_chat_setting import get_user_language

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def validate_telegram_init_data(init_data: str, bot_token: str) -> bool:
    try:
        vals = {k: unquote(v) for k, v in [s.split("=", 1) for s in init_data.split("&")]}
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(vals.items()) if k != "hash")
        secret_key = hmac.new("WebAppData".encode(), bot_token.encode(), hashlib.sha256).digest()
        h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256)

        return h.hexdigest() == vals["hash"]

    except Exception as e:
        logger.error(f"Error validating Telegram init data: {e}", exc_info=True)
        sentry_sdk.capture_exception(e)
        return False


def parse_telegram_init_data(init_data: str) -> Dict:
    """
    Parse Telegram Web App init data into a dictionary.

    Args:
        init_data: URL-encoded init data string from Telegram

    Returns:
        Dict containing user data and other Telegram Web App information
    """
    # Parse the URL-encoded string into a dictionary
    parsed = parse_qs(init_data)

    # Get the user data which is URL-encoded JSON
    user_data = parsed.get("user", [None])[0]
    if not user_data:
        raise ValueError("No user data found in init_data")

    # Decode the JSON string
    user_dict = json.loads(unquote(user_data))

    # Extract additional fields if needed
    result = {
        "user": user_dict,
        "auth_date": parsed.get("auth_date", [None])[0],
        "hash": parsed.get("hash", [None])[0],
        "query_id": parsed.get("query_id", [None])[0],
    }

    return result


@router.get("/language")
async def get_user_language_endpoint(
    async_session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
) -> dict:
    """Легкий endpoint для получения языка пользователя при каждой загрузке приложения"""
    try:
        from uuid import UUID
        user_id = UUID(current_user.user_id)
        language = await get_user_language(async_session, user_id)
        return {"language": language or "en"}
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return {"language": "en"}


@router.post("/telegram/webapp", response_model=TelegramAuthResponse)
async def auth_via_telegram(
    data: TelegramAuthRequest,
    auth: SupabaseAuth = Depends(get_auth),
    async_session: AsyncSession = Depends(get_async_session),
) -> TelegramAuthResponse:
    if not validate_telegram_init_data(data.init_data, config.telegram_bot_token):
        raise HTTPException(status_code=400, detail="Invalid Telegram signature")

    # Parse the Telegram data
    telegram_data = parse_telegram_init_data(data.init_data)
    user_info = telegram_data["user"]

    # Get Telegram user ID
    tg_id = str(user_info.get("id"))
    if not tg_id:
        raise HTTPException(status_code=400, detail="Telegram user ID not found")

    # Log authentication attempt
    logger.info(f"Telegram Web App auth attempt for user {tg_id}")

    # The login function now handles user creation internally.
    first_name = user_info.get("first_name", "")
    last_name = user_info.get("last_name", "")
    display_name = f"{first_name} {last_name}".strip()
    client = auth.login_with_telegram_and_get_client(tg_id, display_name)

    session = client.auth.get_session()

    if not session:
        raise HTTPException(status_code=401, detail="Could not authenticate user")

    # Получаем язык пользователя из БД используя готовую функцию
    user_language = 'en'  # default
    try:
        chat_user = auth.find_user_by_tg_id(tg_id)
        if chat_user:
            # Используем функцию get_user_language с AsyncSession
            saved_language = await get_user_language(async_session, chat_user.id)
            if saved_language:
                user_language = saved_language
    except Exception as e:
        logger.error(f"Error getting user language for tg_id {tg_id}: {e}")

    # Create response using our Pydantic model
    return TelegramAuthResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        token_type="bearer",
        user_info=TelegramUser(**user_info),
        language=user_language,
    )
