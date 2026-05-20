from __future__ import annotations

from typing import List

from .dto import CacheEntry
from .interfaces import BaseCache, BaseGlossary, BaseTranslationMemory, EmbeddingService
from .utils import basic_filter, maybe_update_glossary


class CurationWorker:
    def __init__(
        self,
        *,
        tm: BaseTranslationMemory,
        glossary: BaseGlossary,
        cache: BaseCache,
        embedder: EmbeddingService,
    ) -> None:
        self._tm = tm
        self._glossary = glossary
        self._cache = cache
        self._embedder = embedder

    def process_cache_once(self, batch_size: int = 100) -> int:
        entries = self._cache.read_batch(batch_size)
        if not entries:
            return 0

        accepted: List[CacheEntry] = []
        for e in entries:
            if basic_filter(e.source_text, e.translated_text):
                self._tm.add(
                    e.source_text,
                    e.translated_text,
                    self._embedder.embed(e.source_text),
                )
                maybe_update_glossary(self._glossary, e.source_text, e.translated_text)
                accepted.append(e)

        self._cache.remove(entries)
        return len(accepted)


__all__ = ["CurationWorker"]


