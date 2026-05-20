import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()


import sentry_sdk
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.openai import OpenAIIntegration
from sqlmodel import Session, func, select

from .db.lib.content_models import Banner
from .dependencies import get_session
from .lib.config import config
from .routers.auth import router as auth_router
from .routers.characters import router as characters_router
from .routers.chat import router as chat_router
from .routers.dev import router as dev_router
from .routers.images import router as images_router
from .routers.invoicing import router as invoicing_router
from .routers.landings import router as landings_router
from .routers.media import router as media_router
from .routers.service import router as service_router

logging.basicConfig(
    level=config.log_level,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
production_security = config.production_security
if production_security:
    app = FastAPI(docs_url=None, redoc_url=None)
else:
    app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.cors_allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if config.sentry_environment != "local":
    sentry_sdk.init(
        dsn=config.sentry_dsn,
        environment=config.sentry_environment,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        integrations=[
            OpenAIIntegration(),
        ],
        send_default_pii=True,
    )


@app.get("/dev/get_banner")
async def get_random_banner(
    session: Session = Depends(get_session),
) -> Banner | None:
    stmt = select(Banner).where(Banner.is_active).order_by(func.random())
    banner = session.exec(stmt).first()
    return banner


@app.get("/")
async def root():
    return {"msg": "Hello World"}


@app.get("/trigger_sentry")
def trigger():
    return 1 / 0


app.include_router(chat_router)
app.include_router(images_router)
app.include_router(invoicing_router)
app.include_router(service_router)
app.include_router(landings_router)
app.include_router(characters_router)
app.include_router(media_router)
app.include_router(auth_router)
if not production_security:
    app.include_router(dev_router)
