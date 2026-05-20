import traceback
from typing import Any

import sentry_sdk
import uvicorn
from fastapi import BackgroundTasks, HTTPException, Request
from sqlmodel import Session

from src.db.lib.auth import SupabaseAuth
from src.db.lib.billing.common.exceptions import BillingError
from src.db.lib.billing.invoicing import ServiceDataset
from src.lib.config import config
from src.routers.auth import validate_telegram_init_data
from src.telegram.context import RequestContext
from src.telegram.use_cases.process_payment import process_stars_payment

# Импортируем функции из keyboards.py
# Импортируем функции из api module
# Импортируем функции из chat_logic.py
from .config import (
    API_URL,
    PASSKEY,
    SERVICE_ROLE_KEY,
    TELEGRAM_BOT_TOKEN,
    app,
    engine,
    logger,
    personal_tokens,
)

# Импортируем главный обработчик из dispatcher.py
from .dispatcher import process_telegram_update


@app.on_event("startup")
async def startup_event():
    app.state.auth_handler = SupabaseAuth(
        supabase_url=API_URL,
        supabase_key=SERVICE_ROLE_KEY,
        passkey=PASSKEY,
        engine=engine,
    )


@app.get("/")
async def root():
    return {"message": "Hello World"}


class ProcessPaymentRequest(ServiceDataset):
    init_data: str


@app.post("/process_payment")
async def process_payment(
    user_tg_id: int,
    service_dataset: ProcessPaymentRequest,
):
    # Validate Telegram authentication
    if not validate_telegram_init_data(service_dataset.init_data, config.telegram_bot_token):
        sentry_sdk.capture_message(
            f"Invalid Telegram signature for user {user_tg_id}, {service_dataset.init_data}"
        )
        raise HTTPException(status_code=400, detail="Invalid Telegram signature")

    auth_handler = SupabaseAuth(
        supabase_url=API_URL,
        supabase_key=SERVICE_ROLE_KEY,
        passkey=PASSKEY,
        engine=engine,
    )
    user = auth_handler.find_user_by_tg_id(user_tg_id)
    if not user:
        return {"status": "error", "message": "User not found"}

    with Session(engine) as session:
        try:
            invoice_link = await process_stars_payment(user.id, service_dataset, session)
            return {"status": "ok", "invoice_link": invoice_link}
        except BillingError as e:
            sentry_sdk.capture_exception(e)
            return {"status": "error", "message": e.message}

@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}

@app.post("/webhook/")
async def webhook(
    req: Request,
    background_tasks: BackgroundTasks,
    char_id: int = -1,
):
    try:
        data: dict[str, Any] = await req.json()
        logger.info(f"Webhook input data: {data}")

        # --- START: Logic to determine chat_id and bot_token ---
        chat_id_str = None
        if "message" in data and isinstance(data["message"], dict):
            chat_id_str = data["message"].get("chat", {}).get("id")
        elif "callback_query" in data and isinstance(data["callback_query"], dict):
            chat_id_str = data["callback_query"].get("message", {}).get("chat", {}).get("id")
        
        token_to_use = (
            personal_tokens.get(char_id)
            if char_id != -1 and char_id in personal_tokens
            else TELEGRAM_BOT_TOKEN
        )
        # --- END: Logic to determine chat_id and bot_token ---

        # Создаем объект контекста для этого запроса
        context = RequestContext.build(
            translator=req.app.state.translator,
            telegram_chat_id=str(chat_id_str) if chat_id_str else None,
            bot_token=token_to_use,
            auth_client=req.app.state.auth_handler,
        )
        logger.info(f"Request context created: {context.request_id}")

        # Используем process_telegram_update из handlers.py
        background_tasks.add_task(process_telegram_update, data, char_id, context, background_tasks)
        return {"status": "ok", "message": "Update accepted"}

    except Exception as e:
        # sentry_sdk.capture_exception(e) # sentry_sdk теперь вызывается внутри process_telegram_update при ошибке
        logger.error(
            f"Error processing webhook: {e} \n{traceback.format_exc()}"
        )  # traceback нужен здесь
        return {"status": "error", "message": "Internal server error"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=48123)
