from __future__ import annotations

import hashlib
import logging
import random
import time
from typing import Optional
from uuid import UUID

import sentry_sdk
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from src.db.lib.chat_models import Channel, ChatUser, Message
from src.db.lib.chat_models import MessageType as ChatMessageType
from src.db.lib.content_models import (
    ContentCharacter,
    ContentContext,
    ImageInfo,
    LLMStats,
)
from src.db.lib.llm_services.api import LLMServiceAPI
from src.db.lib.messages import (
    start_new_chat_and_send_first_message as sync_start_new_chat_and_send_first_message,
)
from src.schemas.chat import StartChatWithCharacterOutputDTO
from src.telegram.async_adapters import (
    async_archive_messages,
    async_get_character,
    async_get_images_data,
    async_process_image_getting,
    async_send_message,
)
from src.telegram.config import config
from src.telegram.context import RequestContext, TimingEntry
from src.telegram.dependecies import engine as sync_engine
from src.telegram.DTO.chat import (
    Attachment,
    SendChatMessageOutputSubDTO,
    StartNewChatOutputDTO,
)
from src.translator import TranslationRequest

logger = logging.getLogger(__name__)


async def async_find_or_create_channel(
    session: AsyncSession, char_id: int, user_id: UUID, config_id: Optional[UUID] = None,
    char_usable_contexts: Optional[list] = None
) -> int:
    """Асинхронная версия find_or_create_channel_id"""
    result = await session.execute(
        select(Channel).where(
            Channel.char_id == char_id, 
            Channel.user_id == user_id, 
            Channel.config_id == config_id
        )
    )
    channel = result.scalars().first()
    
    if channel is None:
        if char_usable_contexts is None:
            char = await session.get(ContentCharacter, char_id)
            if char is None:
                raise ValueError(f"No character with id {char_id}")
            char_usable_contexts = char.usable_contexts
        
        suitable_contexts = [
            ctx for ctx in char_usable_contexts 
            if ctx.context_type == "first_interaction"
        ]
        if not suitable_contexts:
            raise ValueError(f"No suitable contexts for character {char_id}")
            
        channel = Channel(
            char_id=char_id,
            user_id=user_id,
            config_id=config_id,
            current_char_context=random.choice(suitable_contexts).id,
        )
        session.add(channel)
        await session.commit()
        await session.refresh(channel)
    
    return channel.id


async def async_start_new_chat_and_send_first_message(
    session: AsyncSession, 
    user_id: UUID, 
    char_id: int, 
    archive_existing: bool = False,
    context: Optional[RequestContext] = None
) -> Optional[dict]:
    """Полностью асинхронная версия start_new_chat_and_send_first_message"""
    
    # Параллельно получаем пользователя и персонажа с eager loading
    if context:
        with context.record_timing("async_get_user_and_char"):
            user_task = session.get(ChatUser, user_id)
            # Загружаем character с связанными данными
            char_query = select(ContentCharacter).where(ContentCharacter.id == char_id).options(selectinload(ContentCharacter.usable_contexts))
            char_task = session.execute(char_query)
            
            user = await user_task
            char_result = await char_task
            char = char_result.scalars().first()
    else:
        user_task = session.get(ChatUser, user_id)
        # Загружаем character с связанными данными
        char_query = select(ContentCharacter).where(ContentCharacter.id == char_id).options(selectinload(ContentCharacter.usable_contexts))
        char_task = session.execute(char_query)
        
        user = await user_task
        char_result = await char_task  
        char = char_result.scalars().first()
    
    if user is None:
        raise ValueError(f"User {user_id} not found")
    if char is None:
        raise ValueError(f"Character {char_id} not found")
    
    # Извлекаем ВСЕ нужные данные из объектов СРАЗУ (уже загружены с eager loading)
    char_onboarding_message = char.onboarding_message  
    char_usable_contexts = char.usable_contexts  # Уже загружены с selectinload
    
    # Найти или создать канал
    if context:
        with context.record_timing("async_find_or_create_channel"):
            chan_id = await async_find_or_create_channel(session, char_id, user_id, None, char_usable_contexts)
    else:
        chan_id = await async_find_or_create_channel(session, char_id, user_id, None, char_usable_contexts)
    
    # Архивировать старые сообщения если нужно
    if archive_existing:
        if context:
            with context.record_timing("async_check_and_archive"):
                count_result = await session.execute(
                    select(func.count()).where(Message.channel_id == chan_id)
                )
                count_messages = count_result.scalar_one()
                if count_messages > 0:
                    await session.commit()
                    archive_id, message_ids = await async_archive_messages(char_id, user_id, None)
                    logger.info(f"Archived: {archive_id}, {len(message_ids)} messages")
        else:
            count_result = await session.execute(
                select(func.count()).where(Message.channel_id == chan_id)
            )
            count_messages = count_result.scalar_one()
            if count_messages > 0:
                await session.commit()
                archive_id, message_ids = await async_archive_messages(char_id, user_id, None)
                logger.info(f"Archived: {archive_id}, {len(message_ids)} messages")
    
    # Получить контекст канала
    if context:
        with context.record_timing("async_setup_context"):
            chan = await session.get(Channel, chan_id)
            current_char_context = await session.get(ContentContext, chan.current_char_context)
    else:
        chan = await session.get(Channel, chan_id)
        current_char_context = await session.get(ContentContext, chan.current_char_context)
    
    if not current_char_context:
        raise ValueError(f"No context found for channel {chan_id}")
    
    # Извлекаем ВСЕ данные из current_char_context пока он привязан к сессии
    context_first_image = current_char_context.first_image
    context_first_message = current_char_context.first_message
    
    # Отправляем сообщения асинхронно и батчами
    messages_to_send = []
    
    # Первое изображение если есть
    if context_first_image:
        messages_to_send.append({
            'type': 'image',
            'text': '',
            'attachments': [{"type": "image", "id": context_first_image.hex}],
            'message_type': ChatMessageType.GREETING_IMAGE
        })
    
    # Onboarding сообщение
    if char_onboarding_message:
        messages_to_send.append({
            'type': 'text',
            'text': char_onboarding_message,
            'attachments': None,
            'message_type': ChatMessageType.ONBOARDING_TEXT
        })
    
    # Первое текстовое сообщение
    messages_to_send.append({
        'type': 'text',
        'text': context_first_message,
        'attachments': None,
        'message_type': ChatMessageType.GREETING_TEXT
    })
    
    # Отправляем сообщения ПОСЛЕДОВАТЕЛЬНО для сохранения порядка
    if context:
        with context.record_timing("async_send_all_messages"):
            for msg_data in messages_to_send:
                await async_send_message(
                    char_id=char_id,
                    user_id=user_id,
                    sender="character",
                    text=msg_data['text'],
                    llm_stats=LLMStats.dummy(),
                    attachments=msg_data['attachments'],
                    message_type=msg_data['message_type'],
                    stage_name=None,
                    config_id=None,
                )
    else:
        for msg_data in messages_to_send:
            await async_send_message(
                char_id=char_id,
                user_id=user_id,
                sender="character",
                text=msg_data['text'],
                llm_stats=LLMStats.dummy(),
                attachments=msg_data['attachments'],
                message_type=msg_data['message_type'],
                stage_name=None,
                config_id=None,
            )
    
    return {
        "message_text": context_first_message,
        "channel_id": chan_id
    }


def start_new_chat_sync_wrapper(user_id: UUID, char_id: int, archive_existing_chat: bool):
    """Synchronous wrapper to be run in a separate thread."""
    with Session(sync_engine) as session:
        return sync_start_new_chat_and_send_first_message(session, user_id, char_id, archive_existing_chat)


async def start_chat_with_char(
    char_id: int,
    user_id: UUID,
    session: AsyncSession,
    config_id: Optional[UUID] = None,
    archive_existing_chat: bool = False,
    context: Optional[RequestContext] = None,
) -> StartNewChatOutputDTO:
    # Требуем, чтобы контекст присутствовал всегда
    assert context is not None, "RequestContext must be provided"
    # Общий таймер для всей функции
    context._start_timer = time.perf_counter()
    
    # Получение пользователя из БД
    with context.record_timing("db_get_user"):
        user: Optional[ChatUser] = await session.get(ChatUser, user_id)
    
    if not user:
        raise ValueError(f"User with id {user_id} not found")

    # Получение персонажа из БД
    with context.record_timing("db_get_character"):
        character: Optional[ContentCharacter] = await session.get(ContentCharacter, char_id)
    
    if not character:
        raise ValueError(f"Character with id {char_id} not found")

    # Debug logging for translation context
    logger.info(f"[TRANSLATION_DEBUG] start_chat_with_char called for user {user_id}, char {char_id}")
    logger.info(f"[TRANSLATION_DEBUG] Context available: {context is not None}")
    logger.info(f"[TRANSLATION_DEBUG] Translator available: {context.translator is not None}")
    logger.info(f"[TRANSLATION_DEBUG] User language: {context.user_language}")
    logger.info(f"[TRANSLATION_DEBUG] Request ID: {context.request_id}")

    # Using fully async implementation instead of sync_to_async wrapper
    
    # Общий блок архивирования: должен срабатывать для обоих случаев (с/без config_id)
    if archive_existing_chat:
        # Находим существующий канал (по config_id, который может быть None)
        with context.record_timing("db_find_channel"):
            result = await session.execute(
                select(Channel).where(
                    Channel.user_id == user_id,
                    Channel.char_id == char_id,
                    Channel.config_id == config_id,
                )
            )
            channel = result.scalars().first()

        if channel:
            archive_channel_id = channel.id
            with context.record_timing("archive_messages"):
                count_messages = await session.execute(
                    select(func.count()).where(Message.channel_id == archive_channel_id)
                )
                count_messages = count_messages.scalar_one()
                if count_messages > 0:
                    await session.commit()
                    archive_id, message_ids = await async_archive_messages(char_id, user_id, config_id)
                    await session.commit()
                    logger.info(f"Archived: {archive_id}, {len(message_ids)} messages")

    if config_id:
        with context.record_timing("llm_api_create_chat"):
            response: StartChatWithCharacterOutputDTO | None = await LLMServiceAPI(
                api_url=config.roleplay_api_url,
                api_key=config.api_key,
            ).post(
                params={
                    "user_id": str(user_id),
                    "character_id": char_id,
                    "config_id": str(config_id),
                },
                validation_schema=StartChatWithCharacterOutputDTO,
                endpoint_url="/chat/create",
            )
        if response is None:
            sentry_sdk.capture_message("No response from LLMServiceAPI in /chat/with/char/{char_id}")
            raise Exception("No response from LLMServiceAPI")
        roleplay_api_response = response
        # is_new = roleplay_api_response.is_new  # TODO: use this variable if needed
        channel_id = roleplay_api_response.channel_id
        
        with context.record_timing("get_character_data"):
            character_dict = await async_get_character(char_id)
            if character_dict:
                character_dict["profile_images_ids"] = await async_get_images_data(
                    character_dict.get("profile_images_ids", []), user_id
                )
        channel = await session.execute(select(Channel).where(Channel.id == channel_id))
        channel = channel.scalars().first()
        
        messages = []
        for message in roleplay_api_response.messages:
            # Извлекаем ВСЕ данные из message объекта заранее
            message_attachments = message.attachments
            message_text = message.text
            message_type = message.message_type
            message_user_id = message.user_id
            message_stage_name = message.stage_name
            
            if message_attachments:
                image_id = message_attachments[0]["id"]
                logger.info(f"Processing image: {image_id}")
                with context.record_timing("process_image"):
                    image = await session.execute(select(ImageInfo).where(ImageInfo.id == image_id))
                    image = image.scalars().first()
                    logger.info(f"Image: {image}")
                    if image:
                        await async_process_image_getting(
                            user_id, char_id, image, config_id
                        )
                
                # Translate attachment message text if present
                original_text = message_text or ""
                translated_text = original_text
                logger.info(f"[TRANSLATION_DEBUG] Processing attachment message text: '{original_text[:50]}...'")
                
                if (
                    context.translator
                    and context.user_language
                    and context.user_language != "en"
                    and original_text
                ):
                    try:
                        with context.record_timing("translate_message"):
                            text_hash = hashlib.sha256(original_text.encode()).hexdigest()
                            req = TranslationRequest(
                                source_text=original_text,
                                source_lang="en",
                                target_lang=context.user_language,
                                context="A chat message from a female character, talking to a male user.",
                                context_key=f"first_message:char_id:{char_id}:story_id:{config_id}:hash:{text_hash}",
                            )
                            res = await context.translator.translate(req)
                            translated_text = res.translated_text
                        logger.info(f"[{context.request_id}] Translated attachment message for user {user_id}")
                    except Exception as e:
                        logger.error(f"[{context.request_id}] Translation failed for attachment message: {e}")
                        sentry_sdk.capture_exception(e)
                
                # Create attachment DTO with translated text
                attachment_dto = SendChatMessageOutputSubDTO(
                    message=translated_text,
                    attachments=[
                        Attachment(type=attachment["type"], id=attachment["id"])
                        for attachment in message_attachments
                    ] if message_attachments else None,
                    message_type=message_type
                )
                messages.append(attachment_dto)

            else:
                # Используем заранее извлеченные данные
                original_text = message_text or ""
                await async_send_message(
                    char_id=char_id,
                    user_id=user_id,
                    sender="character" if message_user_id is None else "user",
                    text=original_text,
                    llm_stats=LLMStats.dummy(),
                    attachments=message_attachments,
                    message_type=message_type,  # type: ignore
                    stage_name=message_stage_name,
                    config_id=config_id,
                )

                translated_text = original_text
                logger.info(f"[TRANSLATION_DEBUG] Processing text message: '{original_text[:50]}...'")
                translation_conditions = {
                    "translator_exists": context.translator is not None,
                    "user_language_exists": context.user_language is not None,
                    "language_not_en": context.user_language != "en" if context.user_language else False,
                    "original_text_exists": bool(original_text),
                }
                logger.info(f"[TRANSLATION_DEBUG] Translation conditions: {translation_conditions}")
                
                if (
                    context.translator
                    and context.user_language
                    and context.user_language != "en"
                    and original_text
                ):
                    try:
                        with context.record_timing("translate_message"):
                            text_hash = hashlib.sha256(original_text.encode()).hexdigest()
                            req = TranslationRequest(
                                source_text=original_text,
                                source_lang="en",  # Assuming character's language is English
                                target_lang=context.user_language,
                                context="A chat message from a female character, talking to a male user.",
                                context_key=f"first_message:char_id:{char_id}:story_id:{config_id}:hash:{text_hash}",
                            )
                            res = await context.translator.translate(req)
                            translated_text = res.translated_text
                        logger.info(
                            f"[{context.request_id}] Translated message for user {user_id} to {context.user_language}"
                        )
                    except Exception as e:
                        logger.error(f"[{context.request_id}] Translation failed for user {user_id}: {e}")
                        sentry_sdk.capture_exception(e)

                messages.append(
                    SendChatMessageOutputSubDTO(
                        message=translated_text, message_type=message_type  # type: ignore
                    )
                )

        return StartNewChatOutputDTO(messages=messages)
    
    # Handle case without config_id - use new async implementation
    # Вместо двойной обработки (создание + получение из БД), создаем сообщения прямо здесь
    try:
        with context.record_timing("get_character_and_context"):
            # Получаем персонажа с контекстами
            char_query = select(ContentCharacter).where(ContentCharacter.id == char_id).options(selectinload(ContentCharacter.usable_contexts))
            char_result = await session.execute(char_query)
            char = char_result.scalars().first()
            
            if char is None:
                raise ValueError(f"Character {char_id} not found")
            
            # Извлекаем данные заранее
            char_onboarding_message = char.onboarding_message
            char_usable_contexts = char.usable_contexts
            
            # Найти подходящий контекст
            suitable_contexts = [
                ctx for ctx in char_usable_contexts 
                if ctx.context_type == "first_interaction"
            ]
            if not suitable_contexts:
                raise ValueError(f"No suitable contexts for character {char_id}")
            
            selected_context = random.choice(suitable_contexts)
            # Извлекаем данные из контекста заранее
            context_first_image = selected_context.first_image
            context_first_message = selected_context.first_message
            context_scenario = selected_context.scenario

        # Создаем сообщения для отправки БЕЗ сохранения в БД
        first_messages = []
        
        # 1. Onboarding сообщение (первым)
        if char_onboarding_message:
            # ✅ ВСЕГДА сохраняем АНГЛИЙСКИЙ в БД (English-Only DB Policy)
            await async_send_message(
                char_id=char_id,
                user_id=user_id,
                sender="character",
                text=char_onboarding_message,  # ✅ АНГЛИЙСКИЙ в БД
                llm_stats=LLMStats.dummy(),
                message_type=ChatMessageType.ONBOARDING_TEXT
            )
            
            # 🌍 Переводим ТОЛЬКО для отображения пользователю
            translated_onboarding = char_onboarding_message
            if context.translator and context.user_language != "en":
                try:
                    text_hash = hashlib.sha256(char_onboarding_message.encode()).hexdigest()
                    req = TranslationRequest(
                        source_text=char_onboarding_message,
                        source_lang="en",
                        target_lang=context.user_language,
                        context="A chat message from a female character, talking to a male user.",
                        context_key=f"first_message:char_id:{char_id}:hash:{text_hash}",
                    )
                    res = await context.translator.translate(req)
                    translated_onboarding = res.translated_text
                except Exception as e:
                    logger.error(f"Translation failed for onboarding message: {e}")
            
            first_messages.append(SendChatMessageOutputSubDTO(
                message=translated_onboarding,  # 🌍 ПЕРЕВЕДЕННЫЙ для отображения
                message_type=ChatMessageType.ONBOARDING_TEXT
            ))
        
        # 2. Первое изображение + scenario (вторым)
        if context_first_image:
            # ✅ ВСЕГДА сохраняем АНГЛИЙСКИЙ scenario в БД (English-Only DB Policy)
            scenario_text = context_scenario or ""
            await async_send_message(
                char_id=char_id,
                user_id=user_id,
                sender="character",
                text=scenario_text,  # ✅ АНГЛИЙСКИЙ scenario в БД
                llm_stats=LLMStats.dummy(),
                attachments=[{"type": "image", "id": context_first_image.hex}],
                message_type=ChatMessageType.GREETING_IMAGE
            )
            
            # 🌍 Переводим scenario ТОЛЬКО для отображения пользователю
            translated_scenario = scenario_text
            if scenario_text and context.translator and context.user_language != "en":
                try:
                    text_hash = hashlib.sha256(scenario_text.encode()).hexdigest()
                    req = TranslationRequest(
                        source_text=scenario_text,
                        source_lang="en",
                        target_lang=context.user_language,
                        context="A scenario description for a character image in a chat.",
                        context_key=f"scenario:char_id:{char_id}:hash:{text_hash}",
                    )
                    res = await context.translator.translate(req)
                    translated_scenario = res.translated_text
                except Exception as e:
                    logger.error(f"Translation failed for scenario: {e}")
            
            first_messages.append(SendChatMessageOutputSubDTO(
                message=translated_scenario,  # 🌍 ПЕРЕВЕДЕННЫЙ scenario для отображения
                attachments=[Attachment(type="image", id=context_first_image.hex)],
                message_type=ChatMessageType.GREETING_IMAGE
            ))
        
        # 3. Первое текстовое сообщение (третьим)
        # ✅ ВСЕГДА сохраняем АНГЛИЙСКИЙ в БД (English-Only DB Policy)
        await async_send_message(
            char_id=char_id,
            user_id=user_id,
            sender="character",
            text=context_first_message,  # ✅ АНГЛИЙСКИЙ в БД
            llm_stats=LLMStats.dummy(),
            message_type=ChatMessageType.GREETING_TEXT
        )
        
        # 🌍 Переводим ТОЛЬКО для отображения пользователю
        translated_first_message = context_first_message
        if context.translator and context.user_language != "en":
            try:
                text_hash = hashlib.sha256(context_first_message.encode()).hexdigest()
                req = TranslationRequest(
                    source_text=context_first_message,
                    source_lang="en",
                    target_lang=context.user_language,
                    context="A chat message from a female character, talking to a male user.",
                    context_key=f"first_message:char_id:{char_id}:hash:{text_hash}",
                )
                res = await context.translator.translate(req)
                translated_first_message = res.translated_text
            except Exception as e:
                logger.error(f"Translation failed for first message: {e}")
        
        first_messages.append(SendChatMessageOutputSubDTO(
            message=translated_first_message,  # 🌍 ПЕРЕВЕДЕННЫЙ для отображения
            message_type=ChatMessageType.GREETING_TEXT
        ))
        
        # Добавляем общий таймер
        total_duration = (time.perf_counter() - context._start_timer) * 1000
        context.timings.append(TimingEntry("total_start_chat_with_char", total_duration))
        
        return StartNewChatOutputDTO(messages=first_messages)
        
    except Exception as e:
        logger.error(f"Error in legacy chat creation: {e}")
        sentry_sdk.capture_exception(e)
        return StartNewChatOutputDTO(messages=[])
