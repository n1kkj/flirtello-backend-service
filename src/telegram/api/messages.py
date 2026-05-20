"""
Message handling functions for Telegram API.

This module provides functions for sending, editing, and deleting messages,
as well as managing chat actions and menu buttons.
"""

import json
from typing import Any, Optional, Union

import httpx
import sentry_sdk
from md2tgmd import escape

from .core import (
    _request_with_fixed_retry,
    client,
    logger,
    preprocess_telegram_markdown,
)


async def send_tg_message(
    chat_id: Union[int, str],
    text: str,
    token: str,
    reply_markup: Optional[dict] = None,
    disable_notification: Optional[bool] = None,
):
    """Send a text message to a Telegram chat."""
    BASE_URL = f"https://api.telegram.org/bot{token}"

    processed_text = preprocess_telegram_markdown(text)
    params: dict[str, Any] = {
        "chat_id": chat_id,
        "text": processed_text,
        "parse_mode": "MarkdownV2",
    }

    if reply_markup:
        # Передаем reply_markup как объект Python, httpx сам сериализует в JSON
        # НЕ используем json.dumps, так как httpx при json=params автоматически сериализует весь словарь
        params["reply_markup"] = reply_markup
        logger.debug(f"🔑 [send_tg_message] Adding reply_markup: {reply_markup}")

    if disable_notification is not None:
        params["disable_notification"] = disable_notification

    url = f"{BASE_URL}/sendMessage"

    try:
        response = await _request_with_fixed_retry(client.post, url, json=params)
        if response.status_code == 200:
            response_data = response.json()
            if reply_markup:
                logger.info(
                    f"✅ [send_tg_message] Message sent successfully with reply_markup. Response: {response_data}"
                )
                # Проверяем, есть ли ошибка в ответе от Telegram
                if not response_data.get("ok"):
                    error_code = response_data.get("error_code")
                    error_description = response_data.get("description")
                    error_message = (
                        f"❌ [send_tg_message] Telegram API returned ok=False: "
                        f"error_code={error_code}, description={error_description}, "
                        f"full_response={response_data}"
                    )
                    logger.error(error_message)
                    # Отправляем в Sentry с деталями ошибки
                    sentry_sdk.capture_message(
                        f"[send_tg_message] Failed to send message with reply_markup",
                        level="error",
                        extras={
                            "chat_id": chat_id,
                            "text": text,
                            "reply_markup": reply_markup,
                            "telegram_error_code": error_code,
                            "telegram_error_description": error_description,
                            "telegram_response": response_data,
                        },
                    )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            # Пытаемся распарсить JSON ответ для получения деталей ошибки
            error_details = {}
            try:
                error_response = e.response.json()
                error_details = {
                    "error_code": error_response.get("error_code"),
                    "description": error_response.get("description"),
                    "full_response": error_response,
                }
            except (json.JSONDecodeError, ValueError):
                error_details = {"raw_error": e.response.text}
            
            logger.warning(
                f"send_tg_message failed with 400 Bad Request for chat {chat_id}. "
                f"Error details: {error_details}. "
                f"Assuming markdown error and retrying with escaped text."
            )
            sentry_sdk.capture_message(
                "Telegram Markdown Fallback Triggered for send_tg_message",
                level="warning",
                extras={
                    "chat_id": chat_id,
                    "original_text": text,
                    "telegram_error": error_details,
                    "reply_markup": str(reply_markup) if reply_markup else None,
                },
            )
            # Важно: сохраняем reply_markup при переотправке
            params["text"] = escape(text)
            # reply_markup уже в params, не нужно добавлять снова
            logger.debug(
                f"🔑 [send_tg_message] Retrying with escaped text, reply_markup preserved: {reply_markup}"
            )
            response = await _request_with_fixed_retry(client.post, url, json=params)
            if response.status_code == 200:
                response_data = response.json()
                if reply_markup:
                    logger.debug(
                        f"✅ [send_tg_message] Retry successful with reply_markup. Response: {response_data.get('result', {}).get('message_id')}"
                    )
        else:
            raise e

    if response.status_code != 200:
        # Пытаемся распарсить JSON ответ для получения деталей ошибки
        error_details = {}
        try:
            error_response = response.json()
            error_details = {
                "error_code": error_response.get("error_code"),
                "description": error_response.get("description"),
                "full_response": error_response,
            }
        except (json.JSONDecodeError, ValueError):
            error_details = {"raw_error": response.text}
        
        error_message = (
            f"Failed to send message to {chat_id}: "
            f"status_code={response.status_code}, error_details={error_details}"
        )
        logger.error(error_message)
        
        if reply_markup:
            logger.error(
                f"❌ [send_tg_message] Failed to send message with reply_markup: {reply_markup}"
            )
            # Отправляем в Sentry с деталями ошибки
            sentry_sdk.capture_message(
                f"[send_tg_message] Failed to send message with reply_markup",
                level="error",
                extras={
                    "chat_id": chat_id,
                    "text": text,
                    "reply_markup": reply_markup,
                    "status_code": response.status_code,
                    "telegram_error_code": error_details.get("error_code"),
                    "telegram_error_description": error_details.get("description"),
                    "telegram_response": error_details.get("full_response"),
                },
            )
    return response


async def copy_tg_message(
    chat_id: Union[int, str],
    from_chat_id: int,
    message_id: int,
    token: str,
    reply_markup: Optional[dict] = None,
):
    """Копирует сообщение из одного чата в другой."""
    BASE_URL = f"https://api.telegram.org/bot{token}"
    url = f"{BASE_URL}/copyMessage"

    params: dict[str, Any] = {
        "chat_id": chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id,
    }

    if reply_markup:
        # Передаем reply_markup как объект Python, httpx сам сериализует в JSON
        params["reply_markup"] = reply_markup

    response = await _request_with_fixed_retry(client.post, url, json=params)
    if response.status_code != 200:
        logger.error(
            f"Failed to copy message to {chat_id} from {from_chat_id}: {response.text}"
        )
    return response


async def send_tg_chat_action_typing(chat_id: Union[int, str], token: str):
    """Send 'typing' chat action."""
    return await send_tg_chat_action(chat_id, "typing", token)


async def send_tg_chat_action_upload_photo(chat_id: Union[int, str], token: str):
    """Send 'upload_photo' chat action."""
    return await send_tg_chat_action(chat_id, "upload_photo", token)


async def send_tg_chat_action(chat_id: Union[int, str], action: str, token: str):
    """Send a chat action (typing, upload_photo, etc.)."""
    BASE_URL = f"https://api.telegram.org/bot{token}"

    url = f"{BASE_URL}/sendChatAction"
    payload = {"chat_id": chat_id, "action": action}

    response = await _request_with_fixed_retry(client.post, url, json=payload)
    return response.json()


async def edit_message_text(
    chat_id: Union[int, str],
    message_id: int,
    token: str,
    text: str,
    reply_markup: Optional[dict] = None,
):
    """Edits the text of an existing message."""
    BASE_URL = f"https://api.telegram.org/bot{token}"
    telegram_url = f"{BASE_URL}/editMessageText"

    processed_text = preprocess_telegram_markdown(text)
    params: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": processed_text,
        "parse_mode": "MarkdownV2",
    }
    if reply_markup:
        # Передаем reply_markup как объект Python, httpx сам сериализует в JSON
        params["reply_markup"] = reply_markup

    try:
        response = await _request_with_fixed_retry(
            client.post, telegram_url, json=params
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            logger.warning(
                f"edit_message_text failed with 400 Bad Request for chat {chat_id}. "
                f"Assuming markdown error and retrying with escaped text. Original error: {e.response.text}"
            )
            sentry_sdk.capture_message(
                "Telegram Markdown Fallback Triggered for edit_message_text",
                level="warning",
                extras={
                    "chat_id": chat_id,
                    "original_text": text,
                    "telegram_error": e.response.text,
                },
            )
            params["text"] = escape(text)
            response = await _request_with_fixed_retry(
                client.post, telegram_url, json=params
            )
        else:
            raise e

    if response.status_code != 200:
        logger.error(
            f"Failed to edit message text for message {message_id} in chat {chat_id}: {response.text}"
        )
    return response


async def edit_message_caption(
    chat_id: Union[int, str],
    message_id: int,
    token: str,
    caption: str,
    reply_markup: Optional[dict] = None,
):
    """Edits the caption of an existing media message."""
    BASE_URL = f"https://api.telegram.org/bot{token}"
    telegram_url = f"{BASE_URL}/editMessageCaption"

    processed_caption = preprocess_telegram_markdown(caption)
    params: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "caption": processed_caption,
        "parse_mode": "MarkdownV2",
    }
    if reply_markup:
        # Передаем reply_markup как объект Python, httpx сам сериализует в JSON
        params["reply_markup"] = reply_markup

    try:
        response = await _request_with_fixed_retry(
            client.post, telegram_url, json=params
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            logger.warning(
                f"edit_message_caption failed with 400 Bad Request for chat {chat_id}. "
                f"Assuming markdown error and retrying with escaped text. Original error: {e.response.text}"
            )
            sentry_sdk.capture_message(
                "Telegram Markdown Fallback Triggered for edit_message_caption",
                level="warning",
                extras={
                    "chat_id": chat_id,
                    "original_caption": caption,
                    "telegram_error": e.response.text,
                },
            )
            params["caption"] = escape(caption)
            response = await _request_with_fixed_retry(
                client.post, telegram_url, json=params
            )
        else:
            raise e

    if response.status_code != 200:
        logger.error(
            f"Failed to edit message caption for message {message_id} in chat {chat_id}: {response.text}"
        )
    return response


async def delete_message(
    chat_id: Union[int, str],
    message_id: int,
    token: str,
):
    """Deletes a message."""
    BASE_URL = f"https://api.telegram.org/bot{token}"
    telegram_url = f"{BASE_URL}/deleteMessage"

    params: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
    }

    response = await _request_with_fixed_retry(client.post, telegram_url, json=params)
    if response.status_code != 200:
        logger.error(
            f"Failed to delete message {message_id} in chat {chat_id}: {response.text}"
        )
    return response


async def set_chat_menu_button(
    token: str,
    *,
    text: str,
    web_app_url: str,
    chat_id: Optional[Union[int, str]] = None,
):
    """Set Telegram chat menu button to a WebApp with localized text.

    If chat_id is provided, sets menu for specific chat; otherwise sets bot default.
    """
    BASE_URL = f"https://api.telegram.org/bot{token}"
    url = f"{BASE_URL}/setChatMenuButton"

    menu_button = {"type": "web_app", "text": text, "web_app": {"url": web_app_url}}
    payload: dict[str, Any] = {"menu_button": menu_button}
    if chat_id is not None:
        payload["chat_id"] = chat_id

    response = await _request_with_fixed_retry(client.post, url, json=payload)
    if response.status_code != 200:
        logger.error(f"Failed to set chat menu button: {response.text}")
    return response
