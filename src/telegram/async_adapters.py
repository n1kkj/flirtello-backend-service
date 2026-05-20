"""
Централизованный модуль async адаптеров для синхронных функций.
Решает проблемы с AsyncSession vs Session.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from asgiref.sync import sync_to_async
from sqlmodel import Session

from src.db.lib.billing.balance_transactions import (
    check_user_have_enough_currency as sync_check_user_have_enough_currency,
)
from src.db.lib.billing.paid_actions import (
    PaidActionDataset,
)
from src.db.lib.billing.paid_actions import (
    get_paid_action_dataset as sync_get_paid_action_dataset,
)
from src.db.lib.billing.paid_actions import (
    process_paid_action as sync_process_paid_action,
)
from src.db.lib.gift_codes.repository import GiftCodeRepository
from src.db.lib.images import process_image_getting as sync_process_image_getting
from src.db.lib.images import reset_images_user as sync_reset_images_user
from src.db.lib.messages import (
    archive_messages as sync_archive_messages,
)
from src.db.lib.messages import (
    find_or_create_channel_id as sync_find_or_create_channel_id,
)
from src.db.lib.messages import (
    send_message as sync_send_message,
)
from src.db.lib.messages import (
    send_message_and_get_response as sync_send_message_and_get_response_actual,
)
from src.lib.billing import (
    get_user_current_tariff_plan as sync_get_user_current_tariff_plan,
)
from src.lib.characters import get_character as sync_get_character
from src.lib.images import get_images_data as sync_get_images_data
from src.telegram.dependecies import engine as sync_engine

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetachedMessageDTO:
    """DTO для передачи данных Message без привязки к SQLAlchemy Session."""
    id: Optional[int]  # Добавляем id для совместимости
    message_type: Optional[str]
    text: Optional[str]
    attachments: Optional[list]
    

@dataclass(frozen=True)
class DetachedFullMessageDTO:
    """DTO аналогичный MessageDTO, но с detached данными."""
    message_type: str  # это MessageType enum
    message: DetachedMessageDTO
    message_image: Optional[dict] = None  # ImageInfo атрибуты как dict


# --- Synchronous Wrappers ---

def get_paid_action_dataset_sync_wrapper(action_name) -> PaidActionDataset:
    """Synchronous wrapper to be run in a separate thread."""
    with Session(sync_engine) as session:
        return sync_get_paid_action_dataset(session, action_name)


def process_paid_action_sync_wrapper(user_id: UUID, paid_action_dataset: PaidActionDataset, source_name, additional_data: dict):
    """Synchronous wrapper for process_paid_action."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔵 [BILLING DEBUG] STARTING PAID ACTION: user_id={user_id}, price={paid_action_dataset.price}, paid_action_id={paid_action_dataset.id}, source={source_name}, additional_data={additional_data}")
    
    with Session(sync_engine) as session:
        try:
            sync_process_paid_action(session, user_id, paid_action_dataset, source_name, additional_data)
            session.commit()  # Commit is needed as the original function doesn't do it
            logger.info(f"✅ [BILLING DEBUG] PAID ACTION SUCCESS: user_id={user_id}, price={paid_action_dataset.price}")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ [BILLING DEBUG] PAID ACTION FAILED: user_id={user_id}, price={paid_action_dataset.price}, error={e}", exc_info=True)
            raise


def check_user_have_enough_currency_sync_wrapper(user_id: UUID, amount: Decimal, currency_type: str):
    """Synchronous wrapper for check_user_have_enough_currency."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 [BILLING DEBUG] CHECKING USER BALANCE: user_id={user_id}, required_amount={amount}, currency_type={currency_type}")
    with Session(sync_engine) as session:
        try:
            sync_check_user_have_enough_currency(session, user_id, amount, currency_type)
            logger.info(f"✅ [BILLING DEBUG] BALANCE CHECK PASSED: user_id={user_id}, amount={amount}")
        except Exception as e:
            logger.error(f"❌ [BILLING DEBUG] BALANCE CHECK FAILED: user_id={user_id}, amount={amount}, error={e}", exc_info=True)
            raise


def get_user_current_tariff_plan_sync_wrapper(user_id: UUID):
    """Synchronous wrapper for get_user_current_tariff_plan."""
    with Session(sync_engine) as session:
        return sync_get_user_current_tariff_plan(session, user_id)


def send_message_sync_wrapper(
    char_id: int,
    user_id: UUID,
    sender: str,
    text: str,
    llm_stats,
    attachments=None,
    message_type=None,
    config_id: Optional[UUID] = None,
    stage_name: Optional[str] = None,
):
    """Synchronous wrapper for send_message."""
    with Session(sync_engine) as session:
        return sync_send_message(
            session=session,
            char_id=char_id,
            user_id=user_id,
            sender=sender,
            text=text,
            llm_stats=llm_stats,
            attachments=attachments,
            message_type=message_type,
            config_id=config_id,
            stage_name=stage_name,
        )


def get_character_sync_wrapper(char_id: int) -> Optional[dict]:
    """Synchronous wrapper to be run in a separate thread."""
    with Session(sync_engine) as session:
        return sync_get_character(session, char_id)


def get_images_data_sync_wrapper(image_ids: list, user_id: UUID) -> list:
    """Synchronous wrapper to be run in a separate thread."""
    with Session(sync_engine) as session:
        return sync_get_images_data(image_ids, user_id, session)


def archive_messages_sync_wrapper(char_id: int, user_id: UUID, config_id: Optional[UUID]) -> tuple[UUID, list[int]]:
    """Synchronous wrapper to be run in a separate thread."""
    with Session(sync_engine) as session:
        return sync_archive_messages(session, char_id, user_id, config_id)


def process_image_getting_sync_wrapper(
    user_id: UUID,
    char_id: int,
    image,
    config_id: Optional[UUID]
):
    """Synchronous wrapper to be run in a separate thread."""
    with Session(sync_engine) as session:
        result = sync_process_image_getting(session, user_id, char_id, image, config_id=config_id)
        # If the wrapped function is actually async (returns a coroutine), run it to completion
        if asyncio.iscoroutine(result):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(result)
            finally:
                loop.close()
        return result


def send_message_and_get_response_sync_wrapper(
    user_id: UUID,
    char_id: int,
    message_text: str,
    translated_message_text: str = None,
) -> List[DetachedFullMessageDTO]:
    """Synchronous wrapper for send_message_and_get_response.
    
    ENGLISH-ONLY DB POLICY: message_text should be English (translated) text to save in DB.
    translated_message_text is for backward compatibility but both should be English.
    
    Note: The original function is marked as async but actually uses sync Session.
    This wrapper handles the sync Session properly and converts Message objects
    to DetachedMessageDTO to avoid DetachedInstanceError.
    """
    with Session(sync_engine) as session:
        # The original function is actually sync despite being marked as async
        # We need to call it without await since it's really synchronous
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # This is a bit hacky, but necessary due to the mixed async/sync nature
            result = loop.run_until_complete(sync_send_message_and_get_response_actual(session, user_id, char_id, message_text))
            
            # Convert Message objects to DetachedMessageDTO to avoid DetachedInstanceError
            detached_result = []
            for message_dto in result:
                # Получаем все данные из Message объекта пока сессия открыта
                message_obj = message_dto.message
                detached_message = DetachedMessageDTO(
                    id=message_obj.id,  # Добавляем id
                    message_type=message_obj.message_type,
                    text=message_obj.text,
                    attachments=message_obj.attachments,
                )
                
                # Также конвертируем ImageInfo если есть
                detached_image = None
                if message_dto.message_image:
                    detached_image = {
                        'id': message_dto.message_image.id,
                        'name': message_dto.message_image.name,
                        'hash': message_dto.message_image.hash,
                        'character': message_dto.message_image.character,
                        'image': message_dto.message_image.image,
                        'image_blurred': message_dto.message_image.image_blurred,
                        'location': message_dto.message_image.location,
                        'cloths': message_dto.message_image.cloths,
                        'rating': message_dto.message_image.rating,
                        'behavior': message_dto.message_image.behavior,
                        'prompt': message_dto.message_image.prompt,
                        'char_name': message_dto.message_image.char_name,
                        'is_free': message_dto.message_image.is_free,
                        'config_id': message_dto.message_image.config_id,
                    }
                
                detached_dto = DetachedFullMessageDTO(
                    message_type=message_dto.message_type.value,  # enum to string
                    message=detached_message,
                    message_image=detached_image
                )
                detached_result.append(detached_dto)
            
            return detached_result
        finally:
            loop.close()


def reset_images_user_sync_wrapper(user_id: UUID):
    """Synchronous wrapper for reset_images_user."""
    with Session(sync_engine) as session:
        sync_reset_images_user(session, user_id)


def find_or_create_channel_id_sync_wrapper(
    char_id: int, user_id: UUID, config_id: Optional[UUID] = None
) -> int:
    """Synchronous wrapper for find_or_create_channel_id."""
    with Session(sync_engine) as session:
        return sync_find_or_create_channel_id(session, char_id, user_id, config_id)


class GiftCodeRepositoryWrapper:
    """Wrapper class for GiftCodeRepository that handles Session creation."""
    
    def __init__(self):
        pass
    
    def activate_gift_code(self, code: str, user_id: UUID):
        """Wrapper for GiftCodeRepository.activate_gift_code."""
        with Session(sync_engine) as session:
            repo = GiftCodeRepository(session)
            result = repo.activate_gift_code(code, user_id)
            session.commit()
            return result
    
    def process_gift_code(self, code: str, user_id: UUID):
        """Wrapper for GiftCodeRepository.process_gift_code."""
        with Session(sync_engine) as session:
            repo = GiftCodeRepository(session)
            result = repo.process_gift_code(code, user_id)
            session.commit()
            return result


# --- Async Adapters ---

async_get_paid_action_dataset = sync_to_async(get_paid_action_dataset_sync_wrapper, thread_sensitive=False)
async_process_paid_action = sync_to_async(process_paid_action_sync_wrapper, thread_sensitive=False)
async_check_user_have_enough_currency = sync_to_async(check_user_have_enough_currency_sync_wrapper, thread_sensitive=False)
async_get_user_current_tariff_plan = sync_to_async(get_user_current_tariff_plan_sync_wrapper, thread_sensitive=False)
async_send_message = sync_to_async(send_message_sync_wrapper, thread_sensitive=False)
async_get_character = sync_to_async(get_character_sync_wrapper, thread_sensitive=False)
async_get_images_data = sync_to_async(get_images_data_sync_wrapper, thread_sensitive=False)
async_archive_messages = sync_to_async(archive_messages_sync_wrapper, thread_sensitive=False)
async_process_image_getting = sync_to_async(process_image_getting_sync_wrapper, thread_sensitive=False)
async_send_message_and_get_response = sync_to_async(send_message_and_get_response_sync_wrapper, thread_sensitive=False)
async_reset_images_user = sync_to_async(reset_images_user_sync_wrapper, thread_sensitive=False)
async_find_or_create_channel_id = sync_to_async(find_or_create_channel_id_sync_wrapper, thread_sensitive=False)

# Gift code repository wrapper (instantiated)
gift_code_repo_wrapper = GiftCodeRepositoryWrapper()
async_gift_code_activate = sync_to_async(gift_code_repo_wrapper.activate_gift_code, thread_sensitive=False)
async_gift_code_process = sync_to_async(gift_code_repo_wrapper.process_gift_code, thread_sensitive=False)


__all__ = [
    # Async adapters
    "async_get_paid_action_dataset",
    "async_process_paid_action", 
    "async_check_user_have_enough_currency",
    "async_get_user_current_tariff_plan",
    "async_send_message",
    "async_get_character",
    "async_get_images_data",
    "async_archive_messages",
    "async_process_image_getting",
    "async_send_message_and_get_response",
    "async_reset_images_user",
    "async_find_or_create_channel_id",
    "async_gift_code_activate",
    "async_gift_code_process",
    # DTOs
    "DetachedMessageDTO",
    "DetachedFullMessageDTO",
]
