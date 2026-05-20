import builtins
from typing import Sequence

from .interfaces import BaseGlossary


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = builtins.sum(x * y for x, y in zip(a, b))
    na = builtins.sum(x * x for x in a) ** 0.5 or 1.0
    nb = builtins.sum(y * y for y in b) ** 0.5 or 1.0
    return dot / (na * nb)


def basic_filter(source: str, target: str) -> bool:
    if not source or not target:
        return False
    if len(source.strip()) < 2 or len(target.strip()) < 2:
        return False
    if all(not ch.isalnum() for ch in source):
        return False
    if all(not ch.isalnum() for ch in target):
        return False
    return True


def maybe_update_glossary(glossary: BaseGlossary, source: str, target: str) -> None:
    s_tokens = source.strip().split()
    t_tokens = target.strip().split()
    if len(s_tokens) == 1 and len(t_tokens) == 1:
        s_tok = s_tokens[0]
        t_tok = t_tokens[0]
        if s_tok and t_tok and s_tok[0].isupper():
            glossary.update_term(s_tok, t_tok)


__all__ = [
    "cosine_similarity",
    "basic_filter",
    "maybe_update_glossary",
]


