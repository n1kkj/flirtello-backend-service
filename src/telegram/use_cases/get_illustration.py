import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

import httpx
import sentry_sdk
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.lib.billing.common.enums import CurrenciesTypes, SourceNames
from src.db.lib.billing.common.exceptions import (
    NotEnoughCurrencyError,
)
from src.db.lib.chat_models import Channel, Message
from src.db.lib.content_models import Config, ImageInfo
from src.db.lib.llm_services.api import LLMServiceAPI
from src.db.lib.messages import (
    get_message_images,
)
from src.lib.billing import (
    map_bff_image_type_to_paid_action_name,
)
from src.lib.config import config
from src.routers.chat import (
    GetIllustrationRequest,
    IllustrationMessage,
    IllustrationResponse,
)
from src.schemas.config import CharConfigSchema
from src.telegram.async_adapters import (
    async_check_user_have_enough_currency,
    async_get_paid_action_dataset,
    async_get_user_current_tariff_plan,
    async_process_image_getting,
    async_process_paid_action,
)
from src.telegram.context import RequestContext
from src.telegram.DTO.chat import (
    Attachment,
    IllustrationOutputDTO,
    SendChatMessageOutputSubDTO,
)
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.template_messages import TemplateMessages

logger = logging.getLogger(__name__)


async def get_illustration(
    char_id: int,
    user_id: UUID,
    session: AsyncSession,
    context: RequestContext,
    config_id: Optional[UUID] = None,
    channel_id: Optional[int] = None,
) -> IllustrationOutputDTO:
    """
    This function now contains the core, "heavy" logic for generating an illustration.
    It is intended to be called from a background task.
    It raises exceptions on failure, which should be caught by the calling task.
    """
    with context.record_timing("get_illustration_total"):
        # --- START: Pre-check for user balance ---
        try:
            # Per user request, check if the user has at least 1 token.
            await async_check_user_have_enough_currency(
                user_id, Decimal(1), CurrenciesTypes.TOKEN.value
            )
        except NotEnoughCurrencyError:
            logger.info(f"User {user_id} failed pre-check for illustration due to insufficient funds (less than 1 token).")
            return IllustrationOutputDTO(
                messages=[
                    SendChatMessageOutputSubDTO(
                        message=TemplateMessages.NO_TOKENS.value,
                        insufficient_balance=True
                    )
                ]
            )
        # --- END: Pre-check for user balance ---

        logger.info(
            f"Getting illustration for char_id: {char_id}, user_id: {user_id}, config_id: {config_id}, channel_id: {channel_id}"
        )
        with context.record_timing("get_illustration_db_queries"):
            if channel_id:
                result = await session.execute(
                    select(Channel).where(
                        Channel.id == channel_id,
                        Channel.user_id == user_id,
                    )
                )
                channel = result.scalars().first()
            else:
                result = await session.execute(
                    select(Channel).where(
                        Channel.char_id == char_id,
                        Channel.user_id == user_id,
                        Channel.config_id == config_id,
                    )
                )
                channel = result.scalars().first()
            if not channel:
                raise Exception("Chat not found")

            # Get messages for context
            result = await session.execute(
                select(Message)
                .where(Message.channel_id == channel.id)
                .order_by(Message.inserted_at.asc())
            )
            messages = result.scalars().all()

        # Extract shown image IDs
        shown_image_ids = get_message_images(list(messages))
        shown_image_ids = [str(image_id) for image_id in shown_image_ids]

        # Prepare messages for illustration request (limit to recent context only)
        # Only use last 10 messages for better performance and cleaner context
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        
        illustration_messages = []
        for msg in recent_messages:
            if msg.text:  # Only include messages with text
                role = "assistant" if msg.char_id else "user"
                illustration_messages.append(IllustrationMessage(role=role, content=msg.text))

        # Make request to illustration service
        illustration_service = LLMServiceAPI(
            api_url=config.roleplay_api_url, api_key=config.api_key, timeout=60
        )

        config_id_for_illustration_api: Optional[str] = None

        if config_id is None:
            # Случай 1: config_id не передан -> фильтр по config_id IS NULL (только дефолтные фотки)
            config_id_for_illustration_api = "null"
        else:
            # Случай 2: config_id передан -> проверяем флаг include_default_images
            result = await session.execute(select(Config).where(Config.id == config_id))
            db_character_config = result.scalars().first()

            if not db_character_config:
                raise Exception("Character configuration not found in DB.")

            if not db_character_config.config:
                raise Exception("Character configuration data is missing in the database record.")

            # Ensure it's a string before trying to load YAML
            if not isinstance(db_character_config.config, str):
                raise Exception("Character configuration is not a YAML string.")

            try:
                parsed_char_config = yaml.safe_load(db_character_config.config)
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML config: {e}")
                raise Exception("Error parsing character configuration.")

            if not isinstance(parsed_char_config, dict):
                raise Exception("Parsed character configuration is not a dictionary.")

            config_schema = CharConfigSchema(**parsed_char_config)

            if config_schema.common.include_default_images:
                # Случай 2.1: include_default_images = true -> без фильтра (все фотки персонажа)
                config_id_for_illustration_api = None
            else:
                # Случай 2.2: include_default_images = false -> строго по config_id
                config_id_for_illustration_api = str(config_id)

        illustration_request = GetIllustrationRequest(
            messages=illustration_messages,
            shown_image_ids=shown_image_ids,
            character_id=char_id,
            config_id=config_id_for_illustration_api,
            channel_id=channel_id,
        )

        # Lightweight retry to reduce random fallbacks
        with context.record_timing("get_illustration_llm_call"):
            illustration_response: Optional[IllustrationResponse] = None
            try:
                illustration_response = await illustration_service.post(
                    params=illustration_request.model_dump(),
                    validation_schema=IllustrationResponse,
                    endpoint_url="/illustrations/get_illustration",
                )
                if not illustration_response or not illustration_response.image_id:
                    logger.info("First attempt for illustration returned empty. Retrying once...")
                    illustration_response = await illustration_service.post(
                        params=illustration_request.model_dump(),
                        validation_schema=IllustrationResponse,
                        endpoint_url="/illustrations/get_illustration",
                    )
            except httpx.TimeoutException:
                logger.error("Timeout while requesting illustration from illustration service.")
                sentry_sdk.capture_exception()


        if not illustration_response or not illustration_response.image_id:
            logger.info("No response from illustration service: sending fallback message")
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("char_id", char_id)
                scope.set_extra("user_id", user_id)
                scope.set_extra("config_id", config_id)
                scope.set_extra("channel_id", channel_id)
                scope.set_extra("illustration_request", illustration_request.model_dump() if illustration_request else None)
                sentry_sdk.capture_message(
                    "No response from illustration service, fallback message sent to user.",
                    level="error"
                )
            # Get user language for translation
            lang_code = context.user_language if context else "en"
            _ = get_gettext_for_language(lang_code)
            
            return IllustrationOutputDTO.from_single_text_message(
                message=_("Mmm... 🙈 I was just taking the perfect selfie for you, but my camera got too hot from all this passion! 🔥 Give me another try in a moment, baby... 💋 I promise to make it extra special for you! ✨💖")
            )

        with context.record_timing("get_illustration_billing_and_processing"):
            # Get ImageInfo object for the received image_id
            result = await session.execute(
                select(ImageInfo).where(ImageInfo.id == illustration_response.image_id)
            )
            image = result.scalars().first()
            if not image:
                raise Exception("Generated image not found in database")

            # Get paid action dataset based on returned photo type
            if illustration_response.photo_type is None:
                raise Exception("Photo type not found in illustration response")
            paid_action_name = map_bff_image_type_to_paid_action_name(
                illustration_response.photo_type
            )
            paid_action_dataset = await async_get_paid_action_dataset(paid_action_name)
            await async_check_user_have_enough_currency(
                user_id, paid_action_dataset.price, CurrenciesTypes.TOKEN.value
            )
            # Process the image and get message
            message_dto = await async_process_image_getting(
                user_id,
                char_id,
                image,
                config_id,
            )
            # Process payment
            tariff_plan = await async_get_user_current_tariff_plan(user_id)
            tariff_plan_id = str(tariff_plan.id)
            additional_data = {
                "char_id": char_id,
                "image_id": str(illustration_response.image_id),
                "tariff_plan_id": tariff_plan_id,
                "config_id": config_id_for_illustration_api,
            }

            logger.info(f"🔵 [BILLING DEBUG] CALLING ILLUSTRATION BILLING: user_id={user_id}, char_id={char_id}, image_id={illustration_response.image_id}, photo_type={illustration_response.photo_type}, price={paid_action_dataset.price}")
            
            # КРИТИЧЕСКИ ВАЖНО: списание токенов должно произойти ДО возврата изображения
            # Если списание не удалось, изображение НЕ должно быть отправлено пользователю
            try:
                await async_process_paid_action(
                    user_id,
                    paid_action_dataset,
                    SourceNames.TELEGRAM,
                    additional_data,
                )
                logger.info(f"✅ [BILLING DEBUG] ILLUSTRATION BILLING CALL COMPLETED: user_id={user_id}, char_id={char_id}, image_id={illustration_response.image_id}")
            except NotEnoughCurrencyError:
                # Если недостаточно токенов для списания, возвращаем ошибку
                logger.error(f"❌ [BILLING DEBUG] ILLUSTRATION BILLING FAILED: user_id={user_id}, char_id={char_id}, image_id={illustration_response.image_id}, price={paid_action_dataset.price} - insufficient balance")
                await session.rollback()  # Откатываем транзакцию, чтобы не сохранить изображение без списания
                return IllustrationOutputDTO(
                    messages=[
                        SendChatMessageOutputSubDTO(
                            message=TemplateMessages.NO_TOKENS.value,
                            insufficient_balance=True
                        )
                    ]
                )
            except Exception as e:
                # Если произошла другая ошибка при списании, логируем и откатываем транзакцию
                logger.error(f"❌ [BILLING DEBUG] ILLUSTRATION BILLING ERROR: user_id={user_id}, char_id={char_id}, image_id={illustration_response.image_id}, error={e}", exc_info=True)
                await session.rollback()  # Откатываем транзакцию, чтобы не сохранить изображение без списания
                raise  # Пробрасываем ошибку дальше
    
        await session.commit()

        return IllustrationOutputDTO(
            messages=[
                SendChatMessageOutputSubDTO(
                    message=message_dto.message.text if message_dto.message.text is not None else "",
                    attachments=[Attachment(type="image", id=illustration_response.image_id)],
                )
            ]
        )
