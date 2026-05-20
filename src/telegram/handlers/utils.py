from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from src.telegram.config import logger
from src.telegram.DTO.chat import SendChatMessageOutputSubDTO


@dataclass
class StartCommandPayload:
    """Структура для хранения разобранных параметров из команды /start."""

    char_id: Optional[int] = None
    config_id: Optional[UUID] = None
    mkt_source: Optional[str] = None
    is_onboarding_request: bool = False
    internal_source: Optional[str] = None
    language: Optional[str] = None


def parse_start_command_payload(text: str) -> StartCommandPayload:
    """
    Разбирает текст команды /start и возвращает структурированный объект StartCommandPayload.

    Поддерживаемые форматы:
    - /start: пустой payload
    - /start onboarding: запрос на онбординг
    - /start _chat_{id}_story_{uuid}_u_{ref}: новый сложный формат
    - /start {char_id} {config_uuid}: запуск с персонажем и конфигом
    - /start {mkt_source}: запуск с маркетинговым источником
    """
    parts = text.split(" ")
    payload = StartCommandPayload()

    if len(parts) < 2:
        return payload  # Пустая команда /start

    command_payload = parts[1]

    # 1. Новый сложный формат: /start _chat_24_story_uuid..._u_ref2_src_quiz_lang_ru
    if command_payload.startswith("_"):
        try:
            param_parts = command_payload.strip("_").split("_")
            params_dict = dict(zip(param_parts[::2], param_parts[1::2]))

            if "chat" in params_dict and params_dict["chat"].isdigit():
                payload.char_id = int(params_dict["chat"])
                logger.info(f"Parsed char_id from new payload: {payload.char_id}")

            if "story" in params_dict:
                try:
                    payload.config_id = UUID(params_dict["story"])
                    logger.info(f"Parsed config_id from new payload: {payload.config_id}")
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid UUID for 'story' in start payload: {params_dict['story']}"
                    )

            if "u" in params_dict:
                payload.mkt_source = params_dict["u"]
                logger.info(f"Parsed mkt_source from new payload: {payload.mkt_source}")

            if "src" in params_dict:
                payload.internal_source = params_dict["src"]
                logger.info(f"Parsed internal_source from new payload: {payload.internal_source}")

            if "lang" in params_dict:
                payload.language = params_dict["lang"]
                logger.info(f"Parsed language from new payload: {payload.language}")

            return payload
        except Exception as e:
            logger.error(f"Failed to parse new start command format '{command_payload}': {e}")
            # Возвращаем пустой payload, чтобы обработка пошла по пути "неизвестная команда" или "простой /start"
            return StartCommandPayload()

    # 2. Формат /start onboarding
    if command_payload.lower() == "onboarding":
        payload.is_onboarding_request = True
        return payload

    # 3. Формат /start {char_id} [config_id]
    if command_payload.isdigit():
        payload.char_id = int(command_payload)
        if len(parts) >= 3:
            try:
                payload.config_id = UUID(parts[2])
            except (ValueError, TypeError):
                logger.warning(f"Invalid UUID for config_id in start payload: {parts[2]}")
        return payload

    # 4. Формат /start {mkt_source}
    if command_payload and command_payload[0].isalpha():
        payload.mkt_source = command_payload
        return payload

    # 5. Если ничего не подошло, это может быть невалидный параметр (например, "_test")
    logger.info(f"Could not determine start command type for payload: '{command_payload}'")
    return payload


def merge_attachment_messages(
    original_messages: List[SendChatMessageOutputSubDTO],
) -> List[SendChatMessageOutputSubDTO]:
    """Объединяет сообщения только с вложениями (без текста) с ближайшими текстовыми сообщениями."""
    if not original_messages:
        return []

    new_merged_messages: List[SendChatMessageOutputSubDTO] = []
    idx = 0
    while idx < len(original_messages):
        current_msg = original_messages[idx]

        # Проверяем, есть ли в сообщении вложения и отсутствует ли текст (None или пустая строка)
        if current_msg.attachments and not current_msg.message:
            # Специальная ветка: если следующее сообщение типа SCENARIO_TEXT, объединяем с ним
            if idx + 1 < len(original_messages):
                next_msg = original_messages[idx + 1]
                if next_msg.message_type == "SCENARIO_TEXT":
                    all_attachments = current_msg.attachments
                    if next_msg.attachments:
                        all_attachments = all_attachments + next_msg.attachments

                    merged_dto = SendChatMessageOutputSubDTO(
                        message=next_msg.message,
                        attachments=all_attachments,
                        message_type=next_msg.message_type
                    )
                    new_merged_messages.append(merged_dto)
                    idx += 2  # Потребили current_msg и next_msg
                    continue

            # Попытка №1: Объединить с ПРЕДЫДУЩИМ обработанным сообщением
            merged_with_prev = False
            if new_merged_messages:
                last_processed_msg_candidate = new_merged_messages[-1]
                if last_processed_msg_candidate.message:  # Убеждаемся, что у предыдущего есть текст
                    prev_dto_to_update = new_merged_messages.pop()

                    updated_attachments = prev_dto_to_update.attachments or []
                    updated_attachments = updated_attachments + current_msg.attachments

                    updated_prev_dto = SendChatMessageOutputSubDTO(
                        message=prev_dto_to_update.message, attachments=updated_attachments
                    )
                    new_merged_messages.append(updated_prev_dto)
                    idx += 1  # Потребили current_msg
                    merged_with_prev = True

            if merged_with_prev:
                continue

            # Попытка №2: Если не объединили с предыдущим, пробуем объединить со СЛЕДУЮЩИм сообщением
            merged_with_next = False
            if idx + 1 < len(original_messages):
                next_msg_candidate = original_messages[idx + 1]
                if next_msg_candidate.message:  # Убеждаемся, что у следующего есть текст
                    all_attachments = current_msg.attachments
                    if next_msg_candidate.attachments:
                        all_attachments = all_attachments + next_msg_candidate.attachments

                    merged_dto = SendChatMessageOutputSubDTO(
                        message=next_msg_candidate.message, attachments=all_attachments
                    )
                    new_merged_messages.append(merged_dto)
                    idx += 2  # Потребили current_msg и next_msg_candidate
                    merged_with_next = True

            if merged_with_next:
                continue

            # Если не удалось объединить ни с предыдущим, ни со следующим, добавляем current_msg как есть
            new_merged_messages.append(current_msg)
            idx += 1
        else:
            # Это обычное сообщение (есть текст или нет вложений).
            new_merged_messages.append(current_msg)
            idx += 1

    return new_merged_messages 