import os

from dotenv import load_dotenv

from src.lib.billing import PaymentSystems


class Config:
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    log_level: str
    database_url: str
    database_url_async: str
    storage_root: str
    sentry_dsn: str
    sentry_environment: str
    production_security: bool
    cors_allowed_origin: str
    amplitude_key: str
    yandex_metric_key: str
    api_key: str
    use_payment_system_test_server: bool
    roleplay_api_url: str
    telegram_bot_token: str
    translator_llm_url: str
    preloader_delay_seconds: int

    def __init__(self):
        if os.environ.get("API_URL", "") == "":
            load_dotenv("src/.env.dev")
            load_dotenv(".env.dev")
            load_dotenv("sec/.env")
            load_dotenv(".env")

        self.supabase_url = os.environ.get("API_URL", "")
        self.supabase_anon_key = os.environ.get("ANON_KEY", "")
        self.supabase_service_role_key = os.environ.get(
            "SERVICE_ROLE_KEY", ""
        )  # can be not set, used in tests
        self.sentry_dsn = os.environ.get("SENTRY_DSN", "")
        self.sentry_environment = os.environ.get("SENTRY_ENVIRONMENT", "local")
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.database_url = os.environ.get("DB_URL", "")
        self.database_url_async = os.environ.get("ASYNC_DB_URL", "")
        self.storage_root = os.environ.get("STORAGE_ROOT", "")
        self.production_security = os.environ.get("PRODUCTION_SECURITY", "")
        self.cors_allowed_origin = os.environ.get("CORS_ALLOWED_ORIGIN", "")
        self.amplitude_key = os.environ.get("AMPLITUDE_KEY", "")
        self.yandex_metric_key = os.environ.get("YANDEX_METRIC_KEY", "")
        self.api_key = os.environ.get("API_KEY", "")
        self.use_payment_system_test_server = os.environ.get("USE_PAYMENT_SYSTEM_TEST_SERVER", "")
        self.roleplay_api_url = os.environ.get("ROLEPLAY_API_URL", "")
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.translator_llm_url = os.environ.get("TRANSLATOR_LLM_URL", "")
        self.preloader_delay_seconds = int(os.environ.get("PRELOADER_DELAY_SECONDS", 3))
        if not self.supabase_url:
            raise ValueError("Supabase URL must be set")
        if not self.sentry_dsn:
            raise ValueError("Sentry DSN must be set")
        if not self.supabase_anon_key:
            raise ValueError("Supabase Anon Key must be set")
        if not self.database_url:
            raise ValueError("Database URL must be set")
        if not self.database_url_async:
            raise ValueError("ASYNC_DB_URL must be set")
        if not self.storage_root:
            raise ValueError("Storage Root must be set")
        if not self.production_security:
            raise ValueError("Production security status must be set")
        if self.production_security == "False":
            self.production_security = False
        elif self.production_security == "True":
            self.production_security = True
        else:
            raise ValueError("Production security status type must be bool")
        if not self.cors_allowed_origin:
            raise ValueError("CORS allowed origin must be set")
        if not self.amplitude_key:
            raise ValueError("Amplitude key must be set")
        if not self.yandex_metric_key:
            raise ValueError("Yandex metric key must be set")
        if not self.api_key:
            raise ValueError("API key must be set")
        if self.use_payment_system_test_server == "False":
            self.use_payment_system_test_server = False
        elif self.use_payment_system_test_server == "True":
            self.use_payment_system_test_server = True
        else:
            raise ValueError("Use payment_system_test_server type must be bool")
        if not self.roleplay_api_url:
            raise ValueError("Roleplay API URL must be set")
        if not self.telegram_bot_token:
            raise ValueError("Telegram bot token must be set")
        if not self.translator_llm_url:
            raise ValueError("Translator LLM URL must be set")

    def __str__(self):
        return f"Config(supabase_url={self.supabase_url})"


load_dotenv("src/.env.dev")
config = Config()
