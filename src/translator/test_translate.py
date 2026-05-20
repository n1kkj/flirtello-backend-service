from .dto import TranslationRequest
from .in_memory import (
    DummyLLMClient,
    InMemoryCache,
    InMemoryEmbeddingService,
    InMemoryGlossary,
    InMemoryTranslationMemory,
)
from .translator import Translator, t
from .worker import CurationWorker


def test_t_default_appends_lang_marker():
    assert t("Hello", target_lang="ru") == "Hello [ru]"


def test_glossary_replacement_influence():
    tm = InMemoryTranslationMemory()
    glossary = InMemoryGlossary()
    cache = InMemoryCache()
    embedder = InMemoryEmbeddingService()
    llm = DummyLLMClient()

    glossary.update_term("Apple", "Яблоко")

    engine = Translator(
        tm=tm,
        glossary=glossary,
        cache=cache,
        embedder=embedder,
        llm=llm,
    )

    out = t("Apple is nice", target_lang="ru", translator=engine)
    assert out == "Яблоко is nice [ru]"


def test_worker_moves_cache_entries_into_tm():
    tm = InMemoryTranslationMemory()
    glossary = InMemoryGlossary()
    cache = InMemoryCache()
    embedder = InMemoryEmbeddingService()
    llm = DummyLLMClient()

    engine = Translator(
        tm=tm,
        glossary=glossary,
        cache=cache,
        embedder=embedder,
        llm=llm,
    )

    # Perform a translation to populate the cache
    req = TranslationRequest(
        source_text="Ping", source_lang="en", target_lang="ru", context="A network test."
    )
    res = engine.translate(req)
    assert res.translated_text == "Ping [ru]"

    # Process cache into TM
    worker = CurationWorker(tm=tm, glossary=glossary, cache=cache, embedder=embedder)
    accepted = worker.process_cache_once(batch_size=10)
    assert accepted >= 1

    # TM should now return at least one match for the same source
    matches = tm.search_by_embedding(embedder.embed("Ping"), limit=3)
    assert matches
    assert any(m.target_text == "Ping [ru]" for m in matches)