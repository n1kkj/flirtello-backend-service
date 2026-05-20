from __future__ import annotations

import types


from .dto import TranslationRequest
from .in_memory import (
    InMemoryCache,
    InMemoryEmbeddingService,
    InMemoryGlossary,
    InMemoryTranslationMemory,
)
from .llm_client_uri import UriLLMClient
from .translator import Translator


class _FakeChatResponse:
    def __init__(self, content: str) -> None:
        msg = types.SimpleNamespace(content=content)
        choice = types.SimpleNamespace(message=msg)
        self.choices = [choice]


class _FakeChatCompletions:
    def __init__(self, content: str) -> None:
        self._content = content

    def create(self, model: str, messages):  # noqa: D401 - minimal stub
        return _FakeChatResponse(self._content)


class _FakeChat:
    def __init__(self, content: str) -> None:
        self.completions = _FakeChatCompletions(content)


class _FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = _FakeChat(content)


def test_uri_llm_client_chat_calls_underlying(monkeypatch):
    def _fake_factory(url: str):
        return _FakeClient("Привет мир"), "fake-model", {}

    monkeypatch.setattr("src.translator.llm_client_uri.create_llm_client_from_url", _fake_factory)

    cli = UriLLMClient("aisuite://provider/model")
    out = cli.chat([{"role": "user", "content": "Hello"}])
    assert out == "Привет мир"


def test_translator_uses_uri_llm_via_env(monkeypatch):
    def _fake_factory(url: str):
        return _FakeClient("Здравствуй мир"), "fake-model", {}

    monkeypatch.setattr("src.translator.llm_client_uri.create_llm_client_from_url", _fake_factory)
    monkeypatch.setenv("TRANSLATOR_LLM_URL", "aisuite://provider/model")

    tm = InMemoryTranslationMemory()
    glossary = InMemoryGlossary()
    cache = InMemoryCache()
    embedder = InMemoryEmbeddingService()
    llm = UriLLMClient("aisuite://provider/model")

    engine = Translator(tm=tm, glossary=glossary, cache=cache, embedder=embedder, llm=llm)
    result = engine.translate(
        request=TranslationRequest(source_text="Hello", source_lang="en", target_lang="ru", context_messages=None)
    )
    assert result.translated_text == "Здравствуй мир"


