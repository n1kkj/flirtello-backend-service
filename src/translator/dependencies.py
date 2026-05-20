from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.telegram.dependencies import get_async_session
from src.translator.sql_tm import SQLTranslationMemory

from .interfaces import BaseTranslationMemory


def get_translation_memory(
    session: AsyncSession = Depends(get_async_session),
) -> BaseTranslationMemory:
    return SQLTranslationMemory(session)
