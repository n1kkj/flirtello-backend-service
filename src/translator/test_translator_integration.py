from __future__ import annotations

import os
import time

import pytest

from . import build_translator_from_env
from .dto import TranslationRequest


def _require_llm_url_or_skip():
    llm_url = os.getenv("TRANSLATOR_LLM_URL")
    if not llm_url:
        pytest.skip("Integration prerequisite: TRANSLATOR_LLM_URL is not set")
    return llm_url


def test_translator_smoke_ru_to_en():
    llm_url = _require_llm_url_or_skip()
    # Prefer running with TM disabled to reduce side-effects
    os.environ.setdefault("TRANSLATOR_TM_IMPL", "disabled")

    try:
        translator = build_translator_from_env()
    except Exception as exc:
        pytest.skip(f"Translator init failed due to LLM dependency: {exc}")

    req = TranslationRequest(
        source_text="Привет, как дела?", source_lang="ru", target_lang="en", context="A casual chat between friends."
    )
    try:
        start = time.perf_counter()
        res = translator.translate(req)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
    except Exception as exc:
        pytest.fail(f"Translator raised unexpectedly: {exc}")

    assert isinstance(res.translated_text, str)
    assert len(res.translated_text.strip()) > 0
    assert (
        elapsed_ms <= 2000.0
    ), f"Translator call took {elapsed_ms:.1f} ms, expected <= 2000 ms (model: {llm_url}, tune model/timeout if needed)"


def test_translator_respects_env_toggle_tm_disabled(monkeypatch):
    llm_url = _require_llm_url_or_skip()
    monkeypatch.setenv("TRANSLATOR_LLM_URL", llm_url)
    monkeypatch.setenv("TRANSLATOR_TM_IMPL", "disabled")

    try:
        translator = build_translator_from_env()
    except Exception as exc:
        pytest.skip(f"Translator init failed due to LLM dependency: {exc}")

    req = TranslationRequest(
        source_text="Кошка на диване", source_lang="ru", target_lang="en", context="Describing a living room scene."
    )
    res = translator.translate(req)
    print(res.translated_text)
    assert isinstance(res.translated_text, str)
    assert len(res.translated_text.strip()) > 0
    # TM is disabled, so we expect no TM examples used
    assert res.used_tm_examples == []


def test_translator_context_influence():
    _require_llm_url_or_skip()
    os.environ.setdefault("TRANSLATOR_TM_IMPL", "disabled")
    try:
        translator = build_translator_from_env()
    except Exception as exc:
        pytest.skip(f"Translator init failed due to LLM dependency: {exc}")

    # "лук" can be "onion" or "bow"
    # Case 1: Cooking context
    req1 = TranslationRequest(
        source_text="Добавь лук",
        source_lang="ru",
        target_lang="en",
        context="Я готовлю ужин и мне нужен рецепт.",
    )
    res1 = translator.translate(req1)
    print(res1.translated_text)
    assert "onion" in res1.translated_text.lower()

    # Case 2: Archery context
    req2 = TranslationRequest(
        source_text="Возьми лук",
        source_lang="ru",
        target_lang="en",
        context="Стрельба из лука - олимпийский вид спорта.",
    )
    res2 = translator.translate(req2)
    print(res2.translated_text)
    assert "bow" in res2.translated_text.lower()


