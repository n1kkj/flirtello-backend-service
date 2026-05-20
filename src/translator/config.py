from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .in_memory import (
    DummyLLMClient,
    InMemoryCache,
    InMemoryEmbeddingService,
    InMemoryGlossary,
    InMemoryTranslationMemory,
    NoopTranslationMemory,
)
from .interfaces import (
    BaseCache,
    BaseGlossary,
    BaseTranslationMemory,
    ChatLLMClient,
    EmbeddingService,
)
from .llm_client_uri import UriLLMClient
from .prod_embedding import MixedbreadEmbeddingService
from .translator import Translator


@dataclass
class TranslatorConfig:
    embedding_impl: str = "in_memory"
    cache_impl: str = "in_memory"
    tm_impl: str = "in_memory"
    glossary_impl: str = "in_memory"
    llm_impl: str = "dummy"
    tm_search_limit: int = 3


@dataclass
class TranslatorDependencies:
    tm: BaseTranslationMemory
    glossary: BaseGlossary
    cache: BaseCache
    embedder: EmbeddingService
    llm: ChatLLMClient


def load_config_from_env(prefix: str = "TRANSLATOR_") -> TranslatorConfig:
    def _get(name: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(prefix + name, default)

    cfg = TranslatorConfig()
    cfg.embedding_impl = _get("EMBEDDING_IMPL", cfg.embedding_impl) or cfg.embedding_impl
    cfg.cache_impl = _get("CACHE_IMPL", cfg.cache_impl) or cfg.cache_impl
    cfg.tm_impl = _get("TM_IMPL", cfg.tm_impl) or cfg.tm_impl
    cfg.glossary_impl = _get("GLOSSARY_IMPL", cfg.glossary_impl) or cfg.glossary_impl
    cfg.llm_impl = _get("LLM_IMPL", cfg.llm_impl) or cfg.llm_impl
    cfg.tm_search_limit = int(_get("TM_SEARCH_LIMIT", str(cfg.tm_search_limit)) or cfg.tm_search_limit)
    return cfg


def build_dependencies_from_env(cfg: Optional[TranslatorConfig] = None) -> TranslatorDependencies:
    cfg = cfg or load_config_from_env()

    # For MVP we only support in-memory/dummy implementations
    if cfg.embedding_impl.lower() == "mixedbread":
        embedder = MixedbreadEmbeddingService()
    else:
        embedder = InMemoryEmbeddingService()
    tm_env = (cfg.tm_impl or "in_memory").lower()
    if tm_env in ("disabled", "noop", "off", "0") or os.getenv("TRANSLATOR_TM_ENABLED") == "0":
        tm = NoopTranslationMemory()
    else:
        tm = InMemoryTranslationMemory()
    glossary = InMemoryGlossary()
    cache = InMemoryCache()
    llm_url = os.getenv("TRANSLATOR_LLM_URL")
    if llm_url:
        llm = UriLLMClient(llm_url)
    else:
        llm = DummyLLMClient()

    return TranslatorDependencies(
        tm=tm,
        glossary=glossary,
        cache=cache,
        embedder=embedder,
        llm=llm,
    )


def build_translator_from_env(cfg: Optional[TranslatorConfig] = None) -> Translator:
    cfg = cfg or load_config_from_env()
    deps = build_dependencies_from_env(cfg)
    return Translator(
        tm=deps.tm,
        glossary=deps.glossary,
        cache=deps.cache,
        embedder=deps.embedder,
        llm=deps.llm,
        tm_search_limit=cfg.tm_search_limit,
    )


__all__ = [
    "TranslatorConfig",
    "TranslatorDependencies",
    "load_config_from_env",
    "build_dependencies_from_env",
    "build_translator_from_env",
]


