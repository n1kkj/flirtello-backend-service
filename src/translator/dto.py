from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TranslationRequest:
    source_text: str
    source_lang: str = "auto"
    target_lang: str = "en"
    context: Optional[str] = None
    context_key: Optional[str] = None


@dataclass
class TMMatch:
    source_text: str
    target_text: str
    score: float


@dataclass
class TranslationResult:
    translated_text: str
    used_tm_examples: List[TMMatch]
    used_glossary: Dict[str, str]


@dataclass
class CacheEntry:
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    metadata: Dict[str, Any]


__all__ = [
    "TranslationRequest",
    "TMMatch",
    "TranslationResult",
    "CacheEntry",
]


