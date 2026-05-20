"""
Core utilities for Telegram API client.

This module provides the fundamental building blocks for making requests
to the Telegram Bot API, including retry logic and markdown preprocessing.
"""

import asyncio
import json
import re
from typing import Any, Callable, Coroutine, Optional

import httpx
import sentry_sdk
from md2tgmd import escape

# Import shared HTTP client and logger from config
from ..config import client, logger


def preprocess_telegram_markdown(text: str) -> str:
    """
    Pre-processes markdown text to fix common issues for Telegram's MarkdownV2 parser.
    - Escapes periods, hyphens, and some other special characters that frequently
      cause parsing errors when not escaped.
    """
    # Using negative lookbehind to avoid escaping an already escaped character.
    # e.g., don't convert \. to \\\.
    # Characters to escape: . ! - = >
    if text:
        text = re.sub(r"(?<!\\)\.", r"\\.", text)
        text = re.sub(r"(?<!\\)!", r"\\!", text)
        text = re.sub(r"(?<!\\)-", r"\\-", text)
        text = re.sub(r"(?<!\\)=", r"\\=", text)
        text = re.sub(r"(?<!\\)>", r"\\>", text)
    return text


async def _request_with_fixed_retry(
    actual_request_func: Callable[..., Coroutine[Any, Any, httpx.Response]],
    url: str,
    max_retries: int = 5,
    fixed_delay_seconds: float = 0.5,
    *args: Any,
    **kwargs: Any,
) -> httpx.Response:
    """
    Make an HTTP request with automatic retry logic for common failures.

    This function handles transient network errors, rate limiting, and server errors
    by automatically retrying the request with a fixed delay between attempts.

    Args:
        actual_request_func: The HTTP method to call (e.g., client.post, client.get)
        url: The URL to request
        max_retries: Maximum number of retry attempts
        fixed_delay_seconds: Delay between retries in seconds
        *args: Positional arguments to pass to the request function
        **kwargs: Keyword arguments to pass to the request function

    Returns:
        httpx.Response: The successful response

    Raises:
        Exception: If all retry attempts fail
    """
    last_exception: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            response = await actual_request_func(url, *args, **kwargs)

            # --- START: Graceful handling of Telegram API errors ---
            if response.status_code in [400, 403]:  # Bad Request or Forbidden
                try:
                    error_data = response.json()
                    error_description = error_data.get("description", "").lower()

                    if (
                        "chat not found" in error_description
                        or "bot was blocked by the user" in error_description
                    ):
                        logger.warning(
                            f"Telegram API Warning on {url}: {response.text}. This will not be retried or raised as an exception."
                        )
                        return (
                            response  # Return the response without raising an exception
                        )
                except json.JSONDecodeError:
                    # If response is not JSON, proceed to the normal error handling below
                    pass
            # --- END: Graceful handling of Telegram API errors ---

            if response.status_code != 200:
                logger.error(f"Failed to send message to {url}: {response.text}")
                response.raise_for_status()
            return response
        except (
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.PoolTimeout,
            httpx.NetworkError,
        ) as e:
            last_exception = e
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed for {actual_request_func.__name__} to {url} due to {type(e).__name__}. Retrying in {fixed_delay_seconds}s..."
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(fixed_delay_seconds)
            else:  # Last attempt failed
                break
        except httpx.HTTPStatusError as e:
            # --- START: Logic to ignore non-critical Telegram errors ---
            if e.response.status_code in [400, 403]:
                try:
                    response_json = e.response.json()
                    description = response_json.get("description", "").lower()
                    block_reasons = [
                        "bot was blocked by the user",
                        "user is deactivated",
                        "chat not found",
                        "bot was kicked from the supergroup or channel",
                    ]
                    if any(reason in description for reason in block_reasons):
                        logger.warning(
                            f"Request to {url} failed with a non-critical Telegram error: {description}. "
                            f"Status: {e.response.status_code}, Response: {e.response.text}. This is expected and will not be reported to Sentry."
                        )
                        return e.response  # Return the response to avoid Sentry logging
                except json.JSONDecodeError:
                    # If the response is not valid JSON, proceed with normal error handling
                    pass
            # --- END: Logic to ignore non-critical Telegram errors ---

            # Повторяем только для определенных серверных ошибок или 429
            if (
                e.response.status_code in [429, 500, 502, 503, 504]
                and attempt < max_retries - 1
            ):
                last_exception = e
                # Для 429 используем Retry-After заголовок, если он есть
                retry_delay = fixed_delay_seconds
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            retry_delay = float(retry_after)
                            logger.info(
                                f"Telegram API returned 429 with Retry-After={retry_after}s. Will wait {retry_delay}s before retry."
                            )
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Invalid Retry-After header value: {retry_after}. Using default delay {fixed_delay_seconds}s."
                            )
                    else:
                        # Если Retry-After нет, используем экспоненциальную задержку для 429
                        retry_delay = min(
                            fixed_delay_seconds * (2**attempt), 60.0
                        )  # Максимум 60 секунд
                        logger.warning(
                            f"Telegram API returned 429 without Retry-After header. Using exponential backoff: {retry_delay}s."
                        )

                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed for {actual_request_func.__name__} to {url} with status {e.response.status_code}. Retrying in {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
            else:  # Если статус не в списке для повтора, или попытки кончились, пробрасываем ошибку
                last_exception = e
                break  # Exit loop to log to Sentry and re-raise

    # Если все попытки провалились и было исключение
    if last_exception is not None:
        request_method_name = actual_request_func.__name__
        if hasattr(actual_request_func, "__self__") and isinstance(
            actual_request_func.__self__, httpx.AsyncClient
        ):
            if "method" in kwargs:
                request_method_name = kwargs["method"]
            elif (
                args
                and isinstance(args[0], str)
                and args[0].upper()
                in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
            ):
                request_method_name = args[0]

        request_details = {
            "method": request_method_name.upper(),
            "url": url,
            "params_query": kwargs.get("params"),
            "json_payload": kwargs.get("json"),
            "data_payload": str(kwargs.get("data")),
            "has_files": "files" in kwargs,
        }
        request_details = {k: v for k, v in request_details.items() if v is not None}

        sentry_extras = {
            "original_exception_type": type(last_exception).__name__,
            "original_exception_message": str(last_exception),
            "request_details": request_details,
            "final_attempt_number": attempt + 1,
        }
        if isinstance(last_exception, httpx.HTTPStatusError):
            sentry_extras["telegram_response_body"] = last_exception.response.text

        sentry_sdk.capture_message(
            f"Очень плохо: Запрос к Telegram API ({request_details.get('method', 'UNKNOWN_METHOD')} {url}) провалился после {max_retries} попыток.",
            level="error",
            extras=sentry_extras,
        )
        raise last_exception

    raise Exception(
        f"Запрос к {url} не удался после {max_retries} попыток, но не было зафиксировано финальное исключение."
    )
