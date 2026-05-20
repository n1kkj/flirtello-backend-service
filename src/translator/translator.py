from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Sequence

from cachetools import TTLCache

from .dto import TMMatch, TranslationRequest, TranslationResult
from .in_memory import (
    DummyLLMClient,
    InMemoryCache,
    InMemoryEmbeddingService,
    InMemoryGlossary,
    InMemoryTranslationMemory,
)
from .interfaces import (
    BaseCache,
    BaseGlossary,
    BaseTranslationMemory,
    ChatLLMClient,
    EmbeddingService,
)


class Translator:
    def __init__(
        self,
        *,
        tm: BaseTranslationMemory,
        glossary: BaseGlossary,
        cache: BaseCache,
        embedder: EmbeddingService,
        llm: ChatLLMClient,
        tm_search_limit: int = 3,
    ) -> None:
        self._tm = tm
        self._glossary = glossary
        self._cache = cache
        self._embedder = embedder
        self._llm = llm
        self._tm_search_limit = max(0, tm_search_limit)
        self._local_cache: TTLCache[str, str] = TTLCache(maxsize=1024, ttl=60)

    @classmethod
    def default(cls) -> "Translator":
        return cls(
            tm=InMemoryTranslationMemory(),
            glossary=InMemoryGlossary(),
            cache=InMemoryCache(),
            embedder=InMemoryEmbeddingService(),
            llm=DummyLLMClient(),
        )

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        # 0. Проверить, нужен ли перевод вообще
        if (request.source_lang and request.target_lang and 
            request.source_lang.lower() == request.target_lang.lower()):
            # Если исходный и целевой языки одинаковые - возвращаем оригинальный текст
            return TranslationResult(
                translated_text=request.source_text, used_tm_examples=[], used_glossary={}
            )
        
        # 0.1. Если source_lang="auto", пусть LLM сам определит нужность перевода
        # Не делаем хардкод определения языка - пусть LLM решает
        
        # 1. Определить ключ (контекстный или текстовый)
        final_key = request.context_key or request.source_text

        # 2. Проверить L1 Cache (in-memory)
        if (cached_text := self._local_cache.get(final_key)):
            return TranslationResult(
                translated_text=cached_text, used_tm_examples=[], used_glossary={}
            )

        # 3. Проверить L2 Cache (TM в БД)
        tm_entry = await self._tm.get_by_key(final_key, request.target_lang)
        if tm_entry:
            self._local_cache[final_key] = tm_entry.translated_text
            return TranslationResult(
                translated_text=tm_entry.translated_text,
                used_tm_examples=[],
                used_glossary={},
            )

        # 4. Обращение к LLM (с учетом найденных неверифицированных примеров)
        # For now, we are not using unverified examples as context for LLM
        tm_examples: List[TMMatch] = []
        # query_vec = self._embedder.embed(request.source_text)
        # tm_examples = await self._tm.search_by_embedding(query_vec, limit=self._tm_search_limit)
        glossary_hits = self._glossary.lookup_terms(request.source_text)

        translated_text = self._invoke_llm(
            text=request.source_text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            context=request.context,
            tm_examples=tm_examples,
            glossary=glossary_hits,
        )

        # 5. Сохранение в L2 и L1
        translated_text_hash = hashlib.sha256(translated_text.encode()).hexdigest()
        await self._tm.add(
            key=final_key,
            language=request.target_lang,
            source_text=request.source_text,
            translated_text=translated_text,
            translated_text_hash=translated_text_hash,
        )
        self._local_cache[final_key] = translated_text

        return TranslationResult(
            translated_text=translated_text,
            used_tm_examples=tm_examples,
            used_glossary=glossary_hits,
        )

    # ---------------- internal helpers ----------------

    def _build_messages(
        self,
        *,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str],
        tm_examples: Sequence[TMMatch],
        glossary: Dict[str, str],
    ) -> List[Dict[str, str]]:
        system_prompt = (
            "You are a professional translation engine. Translate accurately, preserving meaning, tone, and style.\n"
            f"Translate from {source_lang} to {target_lang}. Output only the translated text without additional commentary."
        )

        if context:
            system_prompt += f"\n\nContext of the conversation:\n{context}"

        if glossary:
            glossary_lines = "\n".join([f"{k} -> {v}" for k, v in glossary.items()])
            system_prompt += f"\nUse the following glossary mappings exactly when applicable:\n{glossary_lines}"

        if tm_examples:
            examples_lines = "\n".join(
                [f"{m.source_text} => {m.target_text}" for m in list(tm_examples)[:5]]
            )
            system_prompt += f"\nReference examples (source => target):\n{examples_lines}"

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": text})
        return messages

    def _invoke_llm(
        self,
        *,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str],
        tm_examples: Sequence[TMMatch],
        glossary: Dict[str, str],
    ) -> str:
        messages = self._build_messages(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            context=context,
            tm_examples=tm_examples,
            glossary=glossary,
        )
        return self._llm.chat(messages).strip()




__all__ = [
    "Translator",
]


