from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Protocol, Sequence

from .dto import CacheEntry, TMMatch
from .models import Translation


class EmbeddingService(Protocol):
    def embed(self, text: str) -> List[float]:
        ...


class BaseTranslationMemory(Protocol):
    async def add(
        self,
        key: str,
        language: str,
        source_text: str,
        translated_text: str,
        translated_text_hash: Optional[str] = None,
    ) -> Translation:
        ...

    async def get_by_key(self, key: str, language: str) -> Optional[Translation]:
        ...

    async def get_by_translated_text_hash(self, hash: str) -> Optional[Translation]:
        ...

    async def search_by_embedding(self, embedding: Sequence[float], limit: int = 3) -> List[TMMatch]:
        ...


class BaseGlossary(Protocol):
    def lookup_terms(self, text: str) -> Dict[str, str]:
        ...

    def update_term(self, term: str, translation: str) -> None:
        ...


class BaseCache(Protocol):
    def write(self, entry: CacheEntry) -> None:
        ...

    def read_batch(self, limit: int = 100) -> List[CacheEntry]:
        ...

    def remove(self, entries: Iterable[CacheEntry]) -> None:
        ...


class ChatLLMClient(Protocol):
    def chat(self, messages: Sequence[Dict[str, str]]) -> str:
        ...


__all__ = [
    "EmbeddingService",
    "BaseTranslationMemory",
    "BaseGlossary",
    "BaseCache",
    "ChatLLMClient",
]


