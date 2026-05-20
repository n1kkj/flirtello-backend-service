import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Session, create_engine

from src.lib.config import config

engine = create_engine(
    config.database_url,
    pool_size=20,  # Увеличено с дефолтных 5 до 20
    max_overflow=30,  # Увеличено с дефолтных 10 до 30 (итого до 50 соединений)
    pool_recycle=3600,  # Переиспользование соединений каждый час
    pool_pre_ping=True,  # Проверка соединений перед использованием
)
async_engine = create_async_engine(
    config.database_url_async,
    pool_pre_ping=True,
    pool_size=20,  # Увеличено с дефолтных 5 до 20
    max_overflow=30,  # Увеличено с дефолтных 10 до 30 (итого до 50 соединений)
    pool_recycle=3600,  # Переиспользование соединений каждый час
    pool_timeout=30,  # Таймаут ожидания соединения
    connect_args={
        "statement_cache_size": 0,  # Отключаем кэширование prepared statements
        "prepared_statement_cache_size": 0,  # Отключаем кэш prepared statements в asyncpg
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
    },
)


def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


async def get_async_session() -> AsyncSession:
    async with AsyncSession(async_engine) as session:
        yield session
