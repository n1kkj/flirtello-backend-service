import logging
import os

import httpx
import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.openai import OpenAIIntegration
from sqlalchemy import create_engine

# from sqlalchemy import event # Раскомментируйте, если будете использовать логирование SQL-запросов
# import traceback # Раскомментируйте, если будете использовать логирование SQL-запросов
# from time import time # Раскомментируйте, если будете использовать логирование SQL-запросов
from src.lib.config import config
from src.translator import Translator, build_translator_from_env

TELEGRAM_LOGGING_LEVEL = os.environ.get("TELEGRAM_LOGGING_LEVEL", "INFO")
logging.basicConfig(
    level=TELEGRAM_LOGGING_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv("src/telegram/.env.telegram")
load_dotenv("src/.env.dev")
load_dotenv("src/.env")

SENTRY_DSN = os.environ.get("SENTRY_DSN", None)
if SENTRY_DSN is None:
    raise Exception("SENTRY_DSN is not set")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if TELEGRAM_BOT_TOKEN == "":
    raise Exception("TELEGRAM_BOT_TOKEN is not set")

DB_URL = os.environ.get("DB_URL")
if DB_URL is None:
    raise Exception("DB_URL is not set")

API_URL = os.environ.get("API_URL")
if API_URL is None:
    raise Exception("API_URL is not set")

SERVICE_ROLE_KEY = os.environ.get("SERVICE_ROLE_KEY")
if SERVICE_ROLE_KEY is None:
    raise Exception("SERVICE_ROLE_KEY is not set")

PASSKEY = os.environ.get("PASSKEY")
if PASSKEY is None:
    raise Exception("PASSKEY is not set")

STORAGE_ROOT = os.environ.get("STORAGE_ROOT")
if STORAGE_ROOT is None:
    raise Exception("STORAGE_ROOT is not set")

DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
if DEEPGRAM_API_KEY is None:
    raise Exception("DEEPGRAM_API_KEY is not set")

SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", None)
if SENTRY_ENVIRONMENT is None:
    raise Exception("SENTRY_ENVIRONMENT is not set")

WEB_APP_FULL_LIST_URL = os.environ.get(
    "TELEGRAM_WEBAPP_URL", os.environ.get("WEB_APP_FULL_LIST_URL", None)
)


if not WEB_APP_FULL_LIST_URL:
    raise Exception("WEB_APP_FULL_LIST_URL or TELEGRAM_WEBAPP_URL is not set or empty")


MKT_COLLECTOR_URL = os.environ.get("MKT_COLLECTOR_URL")
if not MKT_COLLECTOR_URL:
    raise Exception("MKT_COLLECTOR_URL is not set or empty")


MKT_COLLECTOR_API_KEY = os.environ.get("MKT_COLLECTOR_API_KEY")
if not MKT_COLLECTOR_API_KEY:
    raise Exception("MKT_COLLECTOR_API_KEY is not set or empty")


TELEGRAM_STARS_TO_USD_CONVERSION_INDEX = os.environ.get(
    "TELEGRAM_STARS_TO_USD_CONVERSION_INDEX", 50
)
if not TELEGRAM_STARS_TO_USD_CONVERSION_INDEX:
    raise Exception("TELEGRAM_STARS_TO_USD_CONVERSION_INDEX is not set or empty")

TELEGRAM_STARS_TO_USD_CONVERSION_INDEX = int(TELEGRAM_STARS_TO_USD_CONVERSION_INDEX)


# Grafana Cloud Metrics (disabled by default)
GRAFANA_ENABLED = os.getenv("GRAFANA_METRICS_ENABLED", "false").lower() == "true"
if GRAFANA_ENABLED:
    GRAFANA_URL = os.getenv("GRAFANA_PROMETHEUS_URL", "")
    if not GRAFANA_URL:
        raise Exception("GRAFANA_PROMETHEUS_URL must be set when GRAFANA_METRICS_ENABLED=true")
    GRAFANA_USERNAME = os.getenv("GRAFANA_USERNAME", "")
    if not GRAFANA_USERNAME:
        raise Exception("GRAFANA_USERNAME must be set when GRAFANA_METRICS_ENABLED=true")
    GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "")
    if not GRAFANA_PASSWORD:
        raise Exception("GRAFANA_PASSWORD must be set when GRAFANA_METRICS_ENABLED=true")
else:
    GRAFANA_URL = ""
    GRAFANA_USERNAME = ""
    GRAFANA_PASSWORD = ""
GRAFANA_ENVIRONMENT = os.getenv("GRAFANA_ENVIRONMENT", "test")
personal_tokens = {}

client = httpx.AsyncClient()

dbschema = "content,public,auth,extensions"

if SENTRY_ENVIRONMENT != "local":
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment=SENTRY_ENVIRONMENT,
        integrations=[
            OpenAIIntegration(),
        ],
        send_default_pii=True,
    )

engine = create_engine(
    DB_URL,
    echo=False,
    connect_args={"options": "-csearch_path={}".format(dbschema)},
    pool_size=20,  # Увеличено с дефолтных 5 до 20
    max_overflow=30,  # Увеличено с дефолтных 10 до 30 (итого до 50 соединений)
    pool_recycle=3600,  # Переиспользование соединений каждый час
    pool_pre_ping=True,  # Проверка соединений перед использованием
)

# # Пример логирования SQL-запросов (если нужно, раскомментируйте и импорты event, traceback, time)
# @event.listens_for(engine, "before_cursor_execute")
# def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
#     context._query_start_time = time()

# @event.listens_for(engine, "after_cursor_execute")
# def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
#     total = time() - context._query_start_time
#     stack = traceback.extract_stack()
#     caller = None
#     for frame in reversed(stack[:-1]):
#         if any(
#             lib in frame.filename.lower()
#             for lib in ["sqlalchemy", "sqlmodel", "site-packages", "dist-packages", "lib/python"]
#         ):
#             continue
#         caller = frame
#         break
#     location = ""
#     if caller:
#         try:
#             from pathlib import Path
#             workspace_root = Path(__file__).resolve().parent.parent.parent
#             file_path = Path(caller.filename)
#             try:
#                 relative_path = file_path.relative_to(workspace_root)
#                 location = f" [{relative_path}:{caller.lineno}]"
#             except ValueError:
#                 location = f" [{file_path}:{caller.lineno}]"
#         except Exception:
#             location = f" [{caller.filename}:{caller.lineno}]"
#     logger.info(f"[SQL]{location} ({total:.3f}s) {statement}")


production_security = config.production_security
if production_security:
    app = FastAPI(docs_url=None, redoc_url=None)
else:
    app = FastAPI()

try:
    translator: Translator | None = build_translator_from_env()
    logger.info("Translator initialized successfully.")
except Exception as e:
    translator = None
    logger.error(f"Failed to initialize translator: {e}")

app.state.translator = translator

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.cors_allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
