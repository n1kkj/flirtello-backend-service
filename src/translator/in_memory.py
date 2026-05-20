from __future__ import annotations

import builtins
from typing import Dict, Iterable, List, Sequence, Tuple

from .dto import CacheEntry, TMMatch

# Note: interfaces are not required here; this module provides concrete impls
from .utils import cosine_similarity


class InMemoryEmbeddingService:
    def __init__(self, dimension: int = 16) -> None:
        self._dim = max(4, dimension)

    def embed(self, text: str) -> List[float]:
        counts = [0.0] * self._dim
        if not text:
            return counts
        for ch in text.lower():
            idx = (ord(ch) * 1315423911) % self._dim
            counts[idx] += 1.0
        norm = builtins.sum(v * v for v in counts) ** 0.5 or 1.0
        return [v / norm for v in counts]


class InMemoryTranslationMemory:
    def __init__(self) -> None:
        self._items: List[Tuple[str, str, List[float]]] = []

    def add(self, source_text: str, target_text: str, embedding: Sequence[float]) -> None:
        self._items.append((source_text, target_text, list(embedding)))

    def search_by_embedding(self, embedding: Sequence[float], limit: int = 3) -> List[TMMatch]:
        if not self._items:
            return []
        query = list(embedding)
        out: List[TMMatch] = []
        for s, t, e in self._items:
            score = cosine_similarity(query, e)
            out.append(TMMatch(source_text=s, target_text=t, score=score))
        out.sort(key=lambda m: m.score, reverse=True)
        return out[: max(0, limit)]


class NoopTranslationMemory:
    """Disabled TM: accepts writes, never returns matches."""

    def add(self, source_text: str, target_text: str, embedding: Sequence[float]) -> None:
        return None

    def search_by_embedding(self, embedding: Sequence[float], limit: int = 3) -> List[TMMatch]:
        return []


class InMemoryGlossary:
    def __init__(self) -> None:
        self._map: Dict[str, str] = {}

    def lookup_terms(self, text: str) -> Dict[str, str]:
        if not self._map or not text:
            return {}
        lowered = text.lower()
        result: Dict[str, str] = {}
        for term, tr in self._map.items():
            if term.lower() in lowered:
                result[term] = tr
        return result

    def update_term(self, term: str, translation: str) -> None:
        if term and translation:
            self._map[term] = translation


class InMemoryCache:
    def __init__(self) -> None:
        self._entries: List[CacheEntry] = []

    def write(self, entry: CacheEntry) -> None:
        self._entries.append(entry)

    def read_batch(self, limit: int = 100) -> List[CacheEntry]:
        if limit <= 0:
            return []
        return self._entries[:limit]

    def remove(self, entries: Iterable[CacheEntry]) -> None:
        to_remove = set(id(e) for e in entries)
        self._entries = [e for e in self._entries if id(e) not in to_remove]


class DummyLLMClient:
    def __init__(self, prefix: str = ""):
        self._prefix = prefix

    def chat(self, messages: Sequence[Dict[str, str]]) -> str:
        text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                text = m.get("content", "")
                break
        glossary: Dict[str, str] = {}
        target_hint = "[en]"
        for m in messages:
            if m.get("role") == "system":
                content = m.get("content", "")
                for line in content.splitlines():
                    if "->" in line:
                        k, v = line.split("->", 1)
                        glossary[k.strip()] = v.strip()
                if "Translate from" in content and " to " in content:
                    try:
                        after = content.split(" to ", 1)[1]
                        target = after.split(".", 1)[0].strip()
                        target_hint = f"[{target}]"
                    except Exception:
                        pass
        for term, term_tr in glossary.items():
            text = text.replace(term, term_tr)
        return f"{self._prefix}{text} {target_hint}"


__all__ = [
    "InMemoryEmbeddingService",
    "InMemoryTranslationMemory",
    "NoopTranslationMemory",
    "InMemoryGlossary",
    "InMemoryCache",
    "DummyLLMClient",
]


