from __future__ import annotations

import logging
import os
import time
from typing import List, Optional

from .interfaces import EmbeddingService

logger = logging.getLogger(__name__)


class MixedbreadEmbeddingService(EmbeddingService):
    """Продакшн-реализация EmbeddingService через Mixedbread AI.

    Зависимости импортируются лениво, чтобы не требовать их наличия,
    пока эта реализация не используется.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        model: Optional[str] = None,
        retries: int = 2,
    ) -> None:
        # Ленивая загрузка зависимостей
        try:
            from mixedbread import Mixedbread  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "mixedbread package is required for MixedbreadEmbeddingService."
            ) from exc

        self._Mixedbread = Mixedbread

        effective_api_key = api_key or os.getenv("EMBEDDINGS_API_KEY") or os.getenv("TRANSLATOR_EMBEDDINGS_API_KEY")
        if not effective_api_key:
            raise ValueError(
                "Mixedbread AI API key is required. Provide via arg, EMBEDDINGS_API_KEY or TRANSLATOR_EMBEDDINGS_API_KEY."
            )

        self._client = self._Mixedbread(api_key=effective_api_key, timeout=timeout)
        self._model = model or "mixedbread-ai/mxbai-embed-large-v1"
        self._retries = max(0, retries)
        self._sleep_seconds = 1
        logger.info(f"Initialized MixedbreadEmbeddingService with model: {self._model}")

    def embed(self, text: str) -> List[float]:
        if not text:
            logger.warning("Attempted to embed empty string, returning empty list.")
            return []

        attempts = self._retries + 1
        last_exc: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                return self._embed_once(text)
            except Exception as exc:  # pragma: no cover - network dependent
                last_exc = exc
                if attempt == attempts - 1:
                    break
                time.sleep(self._sleep_seconds)
        assert last_exc is not None
        raise last_exc

    # Реальная единичная попытка без ретраев
    def _embed_once(self, text: str) -> List[float]:
        try:
            logger.debug(f"Requesting embedding for text: {text[:80]}...")
            response = self._client.embed(
                model=self._model,
                input=[text],
                normalized=True,
            )

            if getattr(response, "data", None) and len(response.data) > 0:
                raw = response.data[0].embedding
                # Normalize to List[float] to satisfy typing and len()
                if isinstance(raw, str):
                    vec: List[float] = [float(x) for x in raw.split()] if raw.strip() else []
                elif isinstance(raw, list):
                    vec = [float(x) for x in raw]
                else:
                    try:
                        vec = [float(x) for x in list(raw)]  # type: ignore[arg-type]
                    except Exception:
                        from typing import cast
                        vec = cast(List[float], raw)
                logger.debug(f"Received embedding of dimension {len(vec)}")
                return vec
            logger.error("Mixedbread API returned no data in response.")
            raise ValueError("Mixedbread API returned no data.")
        except Exception as e:
            logger.error(f"Error during embedding request to Mixedbread API: {e}", exc_info=True)
            raise


__all__ = ["MixedbreadEmbeddingService"]


