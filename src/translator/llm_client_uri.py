from __future__ import annotations

import os
from typing import Any, Dict, Optional, Sequence, Tuple
from urllib.parse import parse_qs, urlparse

from .interfaces import ChatLLMClient


def create_llm_client_from_url(url: str) -> Tuple[Any, str, Dict[str, str]]:
    """Return (client, model, params) based on URL scheme.

    Supported:
    - aisuite://provider/model?param=value
    - openrouter://model?timeout=30
    """
    parsed = urlparse(url)
    scheme = parsed.scheme
    provider = parsed.netloc
    model = parsed.path.lstrip("/")
    params: Dict[str, str] = {k: v[0] for k, v in parse_qs(parsed.query).items()}

    if scheme == "aisuite":
        try:
            import aisuite as ai  # type: ignore
        except Exception as e:
            raise ImportError("aisuite package is required for aisuite:// URLs") from e

        # Build provider configs from URL params with pc_ prefix
        provider_configs = {}
        if provider:
            provider_config = {}
            # Extract parameters with pc_ prefix (provider config)
            for key, value in list(params.items()):
                if key.startswith("pc_"):
                    # Remove pc_ prefix and add to provider config
                    config_key = key[3:]  # Remove "pc_" prefix
                    provider_config[config_key] = value
                    # Remove from params so it doesn't get passed to completion API
                    del params[key]
            if provider_config:
                provider_configs[provider] = provider_config

        client = ai.Client(provider_configs=provider_configs)
        model_id = f"{provider}:{model}" if provider else model
        return client, model_id, params

    if scheme == "openrouter":
        from openai import Client as OpenAIClient  # type: ignore

        api_key = os.environ.get("OPENROUTER_API_KEY")
        timeout = int(params.get("timeout", 30))
        base_url = "https://openrouter.ai/api/v1"
        client = OpenAIClient(api_key=api_key, base_url=base_url, timeout=timeout)
        model_id = f"{provider}/{model}" if provider else model
        return client, model_id, params

    raise ValueError(f"Unknown LLM scheme: {scheme}")


class UriLLMClient(ChatLLMClient):
    """Chat client backed by a provider specified via URI. Does not build prompts."""

    def __init__(self, url: str, *, system_prompt: Optional[str] = None) -> None:
        self._client, self._model, self._params = create_llm_client_from_url(url)
        self._system_prompt = system_prompt or (
            "You are a professional translation engine. Translate accurately, preserving meaning, tone, and style."
        )

    def chat(self, messages: Sequence[Dict[str, str]]) -> str:
        return self._chat(messages)

    # ---------------- internal helpers ----------------

    # No prompt assembly here by design.

    def _process_messages_for_sys_role(
        self, messages: Sequence[Dict[str, str]]
    ) -> list[Dict[str, str]]:
        """Process messages based on sys_role parameter."""
        processed_messages = list(messages)
        sys_role = self._params.get("sys_role", "").lower()
        if sys_role == "user":
            # Find system message and merge it with first user message
            system_content = None
            user_index = None
            for i, msg in enumerate(processed_messages):
                if msg.get("role") == "system":
                    system_content = msg.get("content", "")
                    processed_messages.pop(i)
                    break
            # Find first user message
            for i, msg in enumerate(processed_messages):
                if msg.get("role") == "user":
                    user_index = i
                    break
            # Merge system content with user message
            if system_content and user_index is not None:
                user_content = processed_messages[user_index].get("content", "")
                processed_messages[user_index] = {
                    "role": "user",
                    "content": f"{system_content}\n\n{user_content}".strip(),
                }
        return processed_messages

    def _chat(self, messages: Sequence[Dict[str, str]]) -> str:
        # Try OpenAI chat.completions API style first
        chat = getattr(self._client, "chat", None)
        if (
            chat is not None
            and hasattr(chat, "completions")
            and hasattr(chat.completions, "create")
        ):
            # Handle sys_role parameter - merge system message with user message if needed
            processed_messages = self._process_messages_for_sys_role(messages)

            # build extra args for chat completion
            extra_body: Dict[str, Any] = {}
            # Handle OpenRouter provider sorting. `priority` is an alias for `sort`.
            sort_value = self._params.get("sort") or self._params.get("priority")
            if sort_value and sort_value in ("price", "throughput", "latency"):
                extra_body["provider"] = {"sort": sort_value}

            # Build completion parameters
            completion_kwargs: Dict[str, Any] = {
                "model": self._model,
                "messages": processed_messages,
            }

            # Pass through parameters from URL (excluding special ones)
            excluded_params = {"timeout", "sort", "priority", "sys_role"}
            for key, value in self._params.items():
                if key not in excluded_params and not key.startswith("pc_"):
                    completion_kwargs[key] = value

            resp = chat.completions.create(extra_body=extra_body, **completion_kwargs)
            content = resp.choices[0].message.content  # type: ignore[attr-defined]
            return content or ""

        # Try "responses" API style
        responses = getattr(self._client, "responses", None)
        if responses is not None and hasattr(responses, "create"):
            # Handle sys_role parameter for responses API too
            processed_messages = self._process_messages_for_sys_role(messages)

            resp = responses.create(model=self._model, input=processed_messages)
            try:
                # OpenAI responses API shape
                return resp.output[0].content[0].text  # type: ignore[attr-defined]
            except Exception:
                pass

        # Fallback: raise explicit error
        raise NotImplementedError("Unsupported client API for chat completion.")


__all__ = ["UriLLMClient", "create_llm_client_from_url"]
