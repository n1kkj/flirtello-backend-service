import asyncio
import re
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from src.telegram.api import copy_tg_message, send_tg_message
from src.telegram.config import MKT_COLLECTOR_API_KEY, MKT_COLLECTOR_URL, logger


async def send_marketing_event(
    mkt_collector_url: str,
    mkt_collector_api_key: str,
    user_uuid: str,
    event_name: str,
    params: dict[str, Any],
    retries: int,
    retry_delay: float,
) -> tuple[bool, str]:
    """
    Отправляет событие в MKT-коллектор с логикой повторных попыток.

    :return: Кортеж (success: bool, message: str)
    """
    url = f"{mkt_collector_url}/events/"
    headers = {"X-API-KEY": mkt_collector_api_key}
    payload = {
        "userId": user_uuid,
        "action": event_name,
        "params": params,
    }
    last_error: str = "Неизвестная ошибка"

    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                return True, response.text
        except httpx.HTTPStatusError as e:
            # Не повторяем ошибки клиента (4xx), они фатальны для запроса
            if 400 <= e.response.status_code < 500:
                last_error = f"Ошибка клиента (MKT Collector). Код: {e.response.status_code}, Тело: {e.response.text}"
                return False, last_error

            # Для серверных ошибок (5xx) и других проблем продолжаем цикл
            last_error = f"Ошибка сервера (MKT Collector). Код: {e.response.status_code}, Тело: {e.response.text}"

        except Exception as e:
            last_error = f"Критическая ошибка при отправке события в MKT Collector: {e}"

        if attempt < retries:
            print(
                f"  -> Маркетинг: Ошибка. Попытка {attempt + 1}/{retries + 1}. Повтор через {retry_delay}с..."
            )
            await asyncio.sleep(retry_delay)

    return False, f"Не удалось отправить событие после {retries + 1} попыток. Последняя ошибка: {last_error}"


async def send_mkt_event_fire_and_forget(
    user_id: Union[UUID, str],
    event_name: str,
    params: Optional[dict[str, Any]] = None,
) -> None:
    """
    Fire-and-forget функция для отправки маркетингового события.
    
    Обрабатывает все ошибки внутри, логирует все действия, никогда не бросает исключения.
    Не блокирует выполнение основного кода.
    
    Args:
        user_id: UUID пользователя или строка с UUID
        event_name: Название события (например, "tg_continue_button")
        params: Опциональные параметры события (по умолчанию пустой dict)
    
    Пример использования:
        await send_mkt_event_fire_and_forget(user.id, "tg_continue_button")
        await send_mkt_event_fire_and_forget(user.id, "tg_continue_command", {"source": "button"})
    """
    if not MKT_COLLECTOR_URL or not MKT_COLLECTOR_API_KEY:
        logger.warning(
            f"MKT Collector URL or API Key is not configured. Cannot send event '{event_name}' for user {user_id}."
        )
        return

    try:
        user_uuid_str = str(user_id)
        event_params = params or {}

        success, message = await send_marketing_event(
            mkt_collector_url=MKT_COLLECTOR_URL,
            mkt_collector_api_key=MKT_COLLECTOR_API_KEY,
            user_uuid=user_uuid_str,
            event_name=event_name,
            params=event_params,
            retries=3,
            retry_delay=1.0,
        )

        if success:
            logger.info(
                f"Successfully sent mkt event '{event_name}' for user {user_id}"
            )
        else:
            logger.warning(
                f"Failed to send mkt event '{event_name}' for user {user_id}. Reason: {message}"
            )
    except Exception as e:
        logger.warning(
            f"Error sending analytics event '{event_name}' for user {user_id}: {e}"
        )


def parse_private_post_url(url: str) -> Optional[tuple[int, int]]:
    """
    Разбирает URL приватного поста Telegram.
    Пример: https://t.me/c/1234567890/123
    Возвращает кортеж (chat_id, message_id) или None, если разбор не удался.
    chat_id преобразуется в формат, необходимый для Bot API (-100...).
    """
    match = re.match(r"https://t\.me/c/(\d+)/(\d+)", url)
    if not match:
        return None

    channel_id_part = match.group(1)
    message_id = int(match.group(2))

    # Telegram API требует, чтобы ID приватных каналов начинались с -100
    chat_id = int(f"-100{channel_id_part}")

    return chat_id, message_id


async def send_post(
    user_id: Union[int, str],
    post_url: str,
    token: str,
    button_text: Optional[str] = None,
    button_url: Optional[str] = None,
) -> tuple[bool, Union[str, Exception]]:
    """
    Отправляет пост пользователю и возвращает результат.

    :return: Кортеж (success: bool, message: Union[str, Exception])
    """
    keyboard = None
    if button_text and button_url:
        keyboard = {"inline_keyboard": [[{"text": button_text, "url": button_url}]]}

    try:
        parsed_ids = parse_private_post_url(post_url)
        response = None
        if parsed_ids:
            from_chat_id, message_id = parsed_ids
            response = await copy_tg_message(
                chat_id=user_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
                token=token,
                reply_markup=keyboard,
            )
        else:
            response = await send_tg_message(
                chat_id=user_id, text=post_url, token=token, reply_markup=keyboard
            )

        if response and response.status_code == 200:
            return True, str(response.json())
        else:
            error_message = "Не удалось отправить сообщение."
            if response:
                error_message += (
                    f" Код: {response.status_code}, Тело: {response.text}"
                )
            return False, error_message

    except Exception as e:
        return False, e 