from typing import List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .dto import TMMatch
from .interfaces import BaseTranslationMemory
from .models import Translation


class SQLTranslationMemory(BaseTranslationMemory):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(
        self,
        key: str,
        language: str,
        source_text: str,
        translated_text: str,
        translated_text_hash: Optional[str] = None,
    ) -> Translation:
        translation = Translation(
            key=key,
            language=language,
            source_text=source_text,
            translated_text=translated_text,
            translated_text_hash=translated_text_hash,
        )
        self._session.add(translation)
        await self._session.commit()
        await self._session.refresh(translation)
        return translation

    async def get_by_key(self, key: str, language: str) -> Optional[Translation]:
        statement = select(Translation).where(Translation.key == key, Translation.language == language)
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def get_by_translated_text_hash(self, hash: str) -> Optional[Translation]:
        statement = select(Translation).where(Translation.translated_text_hash == hash)
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def search_by_embedding(self, embedding: Sequence[float], limit: int = 3) -> List[TMMatch]:
        raise NotImplementedError("search_by_embedding is not supported by SQLTranslationMemory")
