from __future__ import annotations

from .dto import TranslationRequest
from .in_memory import (
    DummyLLMClient,
    InMemoryCache,
    InMemoryEmbeddingService,
    InMemoryGlossary,
    InMemoryTranslationMemory,
)
from .translator import Translator


def test_translator_with_dummy_chat_and_glossary():
    tm = InMemoryTranslationMemory()
    glossary = InMemoryGlossary()
    cache = InMemoryCache()
    embedder = InMemoryEmbeddingService()
    llm = DummyLLMClient()

    glossary.update_term("Apple", "Яблоко")

    engine = Translator(tm=tm, glossary=glossary, cache=cache, embedder=embedder, llm=llm)
    out = engine.translate(
        request=TranslationRequest(source_text="Apple is good", source_lang="en", target_lang="ru", context_messages=None)
    ).translated_text
    assert out == "Яблоко is good [ru]"


