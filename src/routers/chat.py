import asyncio
import json  # Keep for other potential uses, or remove if not used elsewhere
import logging
import os
from datetime import datetime
from decimal import Decimal
from enum import Enum
from time import sleep
from typing import Any, List, Optional, cast
from uuid import UUID, uuid4

import sentry_sdk
import yaml  # Added for YAML parsing
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, Json
from sqlmodel import Session, col, insert, select, update

from src.db.lib.billing.balance_transactions import (
    check_user_have_enough_currency,
    transfer_currency_from_balance_to_balance,
)
from src.db.lib.billing.common.content_billing_models import (
    CurrencyType,
    PaidAction,
    TariffPlan,
    TokenBatch,
    Transaction,
    UserBalance,
    UserPlan,
)
from src.db.lib.billing.common.enums import (
    CurrenciesTypes,
    PaidActions,
    SourceNames,
    TopUpWithdrawTransactionTypes,
)
from src.db.lib.billing.common.exceptions import (
    NotEnoughCurrencyError,
    TariffPlanExpired,
)
from src.db.lib.billing.paid_actions import get_paid_action_dataset, process_paid_action
from src.db.lib.chat_models import AuthUser, Channel, ChatUser, Message
from src.db.lib.chat_models import MessageType as ChatMessageType
from src.db.lib.chat_types import MessageType as ChatTypesMessageType
from src.db.lib.content_models import Config, ImageInfo, LLMStats
from src.db.lib.images import (
    IMAGE_TYPES,
    AllImagesAreShownException,
    NoImagesException,
    get_next_image,
    process_image_getting,
)
from src.db.lib.llm_services.api import LLMServiceAPI
from src.db.lib.messages import (
    ReviewStatus,
    add_review_to_message,
    find_or_create_channel_id,
    get_message_images,
    group_messages_attachments,
    send_message,
    send_message_and_get_response,
    start_new_chat_and_send_first_message,
)
from src.lib.billing import (
    check_if_user_has_purchases,
    get_user_current_tariff_plan,
    map_bff_image_type_to_paid_action_name,
    map_bff_unblur_image_type_to_paid_action_name,
)
from src.lib.characters import get_character
from src.lib.config import config
from src.lib.images import get_images_data
from src.routers.images import ImagesDataResponse
from src.schemas.character import Character
from src.schemas.chat import (
    GetResponseFromCharacterOutputDTO,
    StartChatWithCharacterOutputDTO,
)
from src.schemas.config import CharConfigSchema

from ..dependencies import get_current_user, get_debug_user, get_session
from ..lib.verifier import TokenData

logger = logging.getLogger(__name__)

router = APIRouter()


class UserDataResponse(BaseModel):
    user_id: UUID
    user_name: Optional[str]
    user_plan: UserPlan
    user_tariff_plan: TariffPlan
    email: Optional[str]
    is_email_confirmed: bool
    user_balance_amount: Decimal
    user_metadata: Optional[dict]


@router.get("/chat/me")
async def chat_me(
    current_user: TokenData = Depends(get_current_user),
    session: Session = (Depends(get_session)),
) -> UserDataResponse:
    user_id = UUID(current_user.user_id)
    user_name = session.exec(select(ChatUser.display_name).where(ChatUser.id == user_id)).first()
    auth_user = session.get(AuthUser, user_id)
    user_plan = session.get(UserPlan, user_id)
    user_balance_amount = (
        session.exec(
            select(UserBalance)
            .where(UserBalance.user_id == user_id)
            .where(UserBalance.balance_type.has(CurrencyType.name == CurrenciesTypes.TOKEN.value))
        )
        .first()
        .balance_amount
    )
    tariff_plan = session.get(TariffPlan, user_plan.tariff_plan_id)
    return UserDataResponse(
        user_id=user_id,
        user_name=user_name,
        user_plan=user_plan,
        user_tariff_plan=tariff_plan,
        email=auth_user.email,
        is_email_confirmed=bool(auth_user.email_confirmed_at),
        user_balance_amount=user_balance_amount,
        user_metadata=auth_user.raw_user_meta_data,
    )


class SetProfileDataRequest(BaseModel):
    name: str


@router.post("/chat/me")
async def set_profile(
    request: SetProfileDataRequest,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_id = current_user.user_id
    user = session.get(ChatUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if request.name is not None:
        user.display_name = request.name

    session.commit()

    return {"ok": True}


class StartNewChatResponse(BaseModel):
    is_new: bool
    channel: Channel
    scenario: str
    character: Character


@router.put("/chat/with/char/{char_id}")
async def get_chat_info(
    char_id: int,
    config_id: Optional[UUID] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StartNewChatResponse:
    user_id = current_user.user_id
    if config_id:
        response: StartChatWithCharacterOutputDTO | None = await LLMServiceAPI(
            api_url=config.roleplay_api_url,
            api_key=config.api_key,
        ).post(
            params={
                "user_id": user_id,
                "character_id": char_id,
                "config_id": str(config_id),
            },
            validation_schema=StartChatWithCharacterOutputDTO,
            endpoint_url="/chat/create",
        )
        if response is None:
            sentry_sdk.capture_message("No response from LLMServiceAPI in /chat/with/char/{char_id}")
            raise HTTPException(status_code=500, detail="No response from LLMServiceAPI")
        roleplay_api_response = response
        is_new = roleplay_api_response.is_new
        channel_id = roleplay_api_response.channel_id
        character = get_character(session, char_id)
        character["profile_images_ids"] = get_images_data(
            character["profile_images_ids"], user_id, session
        )
        channel = session.exec(select(Channel).where(Channel.id == channel_id)).first()
        for message in roleplay_api_response.messages:
            # Save all messages from roleplay api to db
            send_message(
                session=session,
                char_id=char_id,
                user_id=current_user.user_id,
                sender="character" if message.user_id is None else "user",
                text=message.text or "",
                llm_stats=LLMStats.dummy(),
                attachments=message.attachments,
                message_type=message.message_type,
                stage_name=message.stage_name,
                config_id=config_id,
            )

        return StartNewChatResponse(
            is_new=is_new,
            channel=channel,
            scenario="Life goes on!",
            character=character,
        )
    channel = session.exec(
        select(Channel).where(
            Channel.char_id == char_id, Channel.user_id == user_id, Channel.config_id == config_id
        )
    ).first()

    character = get_character(session, char_id)
    character["profile_images_ids"] = get_images_data(
        character["profile_images_ids"], user_id, session
    )

    if channel:
        scenario = channel.context.scenario
        if scenario is None:
            scenario = "Life goes on!"
        return StartNewChatResponse(
            is_new=False,
            channel=channel,
            scenario=scenario,
            character=character,
        )

    try:
        response = start_new_chat_and_send_first_message(session, user_id, char_id, True)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Error starting new chat")

    if response is None:
        logger.error("Error starting new chat")
        raise HTTPException(status_code=500, detail="Error starting new chat")
    channel = session.exec(
        select(Channel).where(
            Channel.char_id == char_id, Channel.user_id == user_id, Channel.config_id == config_id
        )
    ).first()
    scenario = channel.context.scenario
    if scenario is None:
        scenario = "Life goes on!"
    return StartNewChatResponse(
        is_new=True,
        channel=channel,
        scenario=scenario,
        character=character,
    )


class SendChatMessageRequest(BaseModel):
    message: str
    config_id: Optional[UUID] = None


class Attachment(BaseModel):
    type: str
    id: UUID
    # is_blurred: bool # TODO: decide


class SendChatMessageResponse(BaseModel):
    message: str
    attachments: Optional[List[Attachment]]


class MessageType(Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class IllustrationMessage(BaseModel):
    """Model for a chat message."""

    role: str
    content: str
    image: Optional[str] = None
    category: Optional[str] = None
    imagined_tags2: Optional[str] = None
    imagined_tags_embedding: Optional[List[float]] = None

    class Config:
        extra = "ignore"


class GetIllustrationRequest(BaseModel):
    """Request model for getting an illustration."""

    messages: List[IllustrationMessage]
    shown_image_ids: Optional[List[str]] = Field(default_factory=list)
    character_id: Optional[int] = None
    num_results: Optional[int] = 1
    config_id: Optional[str] = None
    channel_id: Optional[int] = None


class IllustrationResponse(BaseModel):
    """Response model for an illustration."""

    url: Optional[str] = None
    image_id: Optional[UUID] = None
    photo_type: Optional[str] = None
    action_description: Optional[str] = None


class MessageContent(BaseModel):
    """Content of a message, depending on type."""

    message_id: int
    message_type: MessageType
    text: Optional[str] = None
    image_id: Optional[UUID] = None


class MessageResponse(BaseModel):
    """Response model for a message."""

    messages: List[Message]


# TODO: add config id for defining right channel
@router.put(
    "/chat/{char_id}/message",
    description="Статус код 412, если тарифный план истек. Статус код, 402 если на счёту пользователя недостаточно токенов",
)
async def send_chat_message(
    char_id: int,
    data: SendChatMessageRequest,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SendChatMessageResponse:
    try:
        user_id = UUID(current_user.user_id)
        paid_action_dataset = get_paid_action_dataset(session, PaidActions.MESSAGE.value)
        check_user_have_enough_currency(
            session, user_id, paid_action_dataset.price, CurrenciesTypes.TOKEN.value
        )
        tariff_plan_id = str(get_user_current_tariff_plan(session, user_id).id)
        if data.config_id:
            channel = session.exec(
                select(Channel).where(
                    Channel.char_id == char_id,
                    Channel.user_id == user_id,
                    Channel.config_id == data.config_id,
                )
            ).first()
            if not channel:
                raise HTTPException(status_code=404, detail="Channel not found")
            roleplay_api_response: Optional[MessageResponse] = await LLMServiceAPI(
                api_url=config.roleplay_api_url,
                api_key=config.api_key,
            ).post(
                params={
                    "user_id": str(user_id),
                    "text": data.message,
                    "character_id": char_id,
                    "config_id": str(data.config_id),
                },
                validation_schema=MessageResponse,
                endpoint_url="/chat/messages",
            )

            attachments = []
            if not roleplay_api_response:
                logger.info("No response from roleplay API in send_chat_message")
                sentry_sdk.capture_message("No response from roleplay API in send_chat_message")
                return SendChatMessageResponse(
                    message="I can't talk right now darling", attachments=None
                )
            for message in roleplay_api_response.messages:
                # Save all messages from roleplay api to db
                send_message(
                    session=session,
                    char_id=char_id,
                    user_id=current_user.user_id,
                    sender="character" if message.user_id is None else "user",
                    text=message.text or "",
                    llm_stats=LLMStats.dummy(),
                    attachments=message.attachments,
                    message_type=message.message_type,
                    stage_name=message.stage_name,
                    config_id=data.config_id,
                )
                if message.message_type == MessageType.TEXT:
                    paid_action_dataset = get_paid_action_dataset(session, PaidActions.MESSAGE.value)
                    additional_data = {
                        "char_id": char_id,
                        "message_id": message.message_id,
                        "tariff_plan_id": tariff_plan_id,
                        "config_id": str(data.config_id),
                    }
                    process_paid_action(
                        session,
                        user_id,
                        paid_action_dataset,
                        SourceNames.WEB_SITE,
                        additional_data=additional_data,
                    )
                    response_text = message.text
                elif message.message_type == MessageType.IMAGE:
                    image_type = (
                        session.exec(select(ImageInfo).where(ImageInfo.id == message.image_id))
                        .first()
                        .rating
                    )
                    paid_action_name = map_bff_image_type_to_paid_action_name(image_type)
                    paid_action_dataset = get_paid_action_dataset(session, paid_action_name)
                    additional_data = {
                        "char_id": char_id,
                        "image_id": str(message.image_id),
                        "tariff_plan_id": tariff_plan_id,
                        "config_id": str(data.config_id),
                    }
                    process_paid_action(
                        session,
                        user_id,
                        paid_action_dataset,
                        SourceNames.WEB_SITE,
                        additional_data=additional_data,
                    )
                    attachments.append(Attachment(type="image", id=message.image_id))

            session.commit()
            return SendChatMessageResponse(
                message=message.text, attachments=attachments if attachments else None
            )

        message_dots = await send_message_and_get_response(session, user_id, char_id, data.message)
        # Check response type and change handling pipeline if we have context image
        for message_dto in message_dots:
            if message_dto.message_type == ChatTypesMessageType.IMAGE:
                paid_action_name = map_bff_image_type_to_paid_action_name(
                    message_dto.message_image.rating
                )
                paid_action_dataset = get_paid_action_dataset(session, paid_action_name)
                check_user_have_enough_currency(
                    session, user_id, paid_action_dataset.price, CurrenciesTypes.TOKEN.value
                )
                additional_data = {
                    "char_id": char_id,
                    "image_id": str(message_dto.message_image.id),
                    "tariff_plan_id": tariff_plan_id,
                }
                process_paid_action(
                    session,
                    user_id,
                    paid_action_dataset,
                    SourceNames.WEB_SITE,
                    additional_data=additional_data,
                )
            elif message_dto.message_type == ChatTypesMessageType.TEXT:
                paid_action_dataset = get_paid_action_dataset(session, PaidActions.MESSAGE.value)
                additional_data = {
                    "char_id": char_id,
                    "message_id": message_dto.message.id,
                    "tariff_plan_id": tariff_plan_id,
                }
                process_paid_action(
                    session,
                    user_id,
                    paid_action_dataset,
                    SourceNames.WEB_SITE,
                    additional_data=additional_data,
                )
    except TariffPlanExpired as e:
        raise HTTPException(status_code=412, detail=e.message)
    except NotEnoughCurrencyError as e:
        raise HTTPException(status_code=402, detail=e.message)
    except Exception as e:
        session.rollback()
        raise e
    else:
        session.commit()

    return SendChatMessageResponse(message=message_dto.message.text, attachments=None)


# TODO: add config id for defining right channel
@router.get("/chat/{char_id}/context")
async def get_chat_context(
    char_id: int,
    config_id: Optional[UUID] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> str:
    user_id = current_user.user_id
    channel = session.exec(
        select(Channel).where(
            Channel.char_id == char_id, Channel.user_id == user_id, Channel.config_id == config_id
        )
    ).first()

    if channel is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if channel.context is None:
        raise HTTPException(status_code=404, detail="Chat context not found")

    result = channel.context.scenario
    if result is None:
        result = "Life goes on!"

    return result


# TODO: add config id for defining right channel
@router.get("/chat/{char_id}/get_image")
async def request_image(
    char_id: int,
    config_id: Optional[UUID] = None,
    channel_id: Optional[int] = None,
    current_user: TokenData = Depends(get_current_user),
    # current_user: TokenData = Depends(get_debug_user("05c914c2-5a6b-4d9f-b0e6-28bf319f7239")),
    session: Session = Depends(get_session),
) -> SendChatMessageResponse:
    user_id = UUID(current_user.user_id)
    try:
        if channel_id:
            channel = session.exec(
                select(Channel).where(
                    Channel.id == channel_id,
                    Channel.user_id == user_id,
                )
            ).first()
        else:
            channel = session.exec(
                select(Channel).where(
                    Channel.char_id == char_id,
                    Channel.user_id == user_id,
                    Channel.config_id == config_id,
            )
        ).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Chat not found")

        # Get messages for context
        messages = session.exec(
            select(Message)
            .where(Message.channel_id == channel.id)
            .order_by(Message.inserted_at.asc())
        ).all()

        # Extract shown image IDs
        shown_image_ids = get_message_images(messages)
        shown_image_ids = [str(image_id) for image_id in shown_image_ids]

        # Prepare messages for illustration request
        illustration_messages = []
        for msg in messages:
            if msg.text:  # Only include messages with text
                role = "assistant" if msg.char_id else "user"
                illustration_messages.append(IllustrationMessage(role=role, content=msg.text))

        # Make request to illustration service
        illustration_service = LLMServiceAPI(
            api_url=config.roleplay_api_url, api_key=config.api_key, timeout=100
        )

        config_id_for_illustration_api: Optional[str] = None

        if config_id is not None:
            db_character_config = session.exec(select(Config).where(Config.id == config_id)).first()

            if not db_character_config:
                raise HTTPException(
                    status_code=404, detail="Character configuration not found in DB."
                )

            if not db_character_config.config:
                raise HTTPException(
                    status_code=404,
                    detail="Character configuration data is missing in the database record.",
                )

            # Ensure it's a string before trying to load YAML
            if not isinstance(db_character_config.config, str):
                raise HTTPException(
                    status_code=500, detail="Character configuration is not a YAML string."
                )

            try:
                parsed_char_config = yaml.safe_load(db_character_config.config)
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML config: {e}")
                raise HTTPException(status_code=500, detail="Error parsing character configuration.")

            if not isinstance(parsed_char_config, dict):
                raise HTTPException(
                    status_code=500, detail="Parsed character configuration is not a dictionary."
                )

            config_schema = CharConfigSchema(**parsed_char_config)

            # Start with the provided config_id if it exists
            if config_schema.common.include_default_images:
                config_id_for_illustration_api = None
            else:
                config_id_for_illustration_api = str(config_id)

        illustration_request = GetIllustrationRequest(
            messages=illustration_messages,
            shown_image_ids=shown_image_ids,
            character_id=char_id,
            config_id=config_id_for_illustration_api,
            channel_id=channel_id,
        )

        illustration_response: Optional[IllustrationResponse] = await illustration_service.post(
            params=illustration_request.model_dump(),
            validation_schema=IllustrationResponse,
            endpoint_url="/illustrations/get_illustration",
        )

        if not illustration_response or not illustration_response.image_id:
            return SendChatMessageResponse(
                message="I couldn't generate an image for you right now", attachments=None
            )

        # Get ImageInfo object for the received image_id
        image = session.exec(
            select(ImageInfo).where(ImageInfo.id == illustration_response.image_id)
        ).first()
        if not image:
            raise HTTPException(status_code=404, detail="Generated image not found in database")

        # Get paid action dataset based on returned photo type
        paid_action_name = map_bff_image_type_to_paid_action_name(illustration_response.photo_type)
        paid_action_dataset = get_paid_action_dataset(session, paid_action_name)
        check_user_have_enough_currency(
            session, user_id, paid_action_dataset.price, CurrenciesTypes.TOKEN.value
        )
        # Process the image and get message
        message_dto = await process_image_getting(
            session,
            user_id,
            char_id,
            image,
            config_id,
        )
        # Process payment
        tariff_plan_id = str(get_user_current_tariff_plan(session, user_id).id)
        additional_data = {
            "char_id": char_id,
            "image_id": str(illustration_response.image_id),
            "tariff_plan_id": tariff_plan_id,
            "config_id": config_id_for_illustration_api,
        }

        process_paid_action(
            session,
            user_id,
            paid_action_dataset,
            SourceNames.WEB_SITE,
            additional_data=additional_data,
        )

    except TariffPlanExpired as e:
        raise HTTPException(status_code=412, detail=e.message)
    except NotEnoughCurrencyError as e:
        raise HTTPException(status_code=402, detail=e.message)
    except Exception as e:
        session.rollback()
        raise e
    else:
        session.commit()

    return SendChatMessageResponse(
        message=message_dto.message.text,
        attachments=[Attachment(type="image", id=illustration_response.image_id)],
    )


# TODO: add config id for defining right channel
@router.get(
    "/chat/{char_id}/unblur_image/{image_id}",
    description="Статус код 412, если тарифный план истек. Статус код, 402 если на счёту пользователя недостаточно токенов",
)
async def unblur_image(
    char_id: int,
    image_id: UUID,
    config_id: Optional[UUID] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_id = UUID(current_user.user_id)
    try:
        # Getting image
        stmt = select(ImageInfo).where(ImageInfo.id == image_id)
        image = session.exec(stmt).first()
        if not image:
            raise HTTPException(status_code=404, detail="Invalid image id. No such image")
        # Checking if user has access to unblur image
        image_type = image.rating
        if (
            not check_if_user_has_purchases(session, user_id) and image_type == IMAGE_TYPES[3]
        ):  # TODO: change to enum, very sensitive to changes
            raise HTTPException(
                status_code=405,
                detail="You have no access to unblur images. Please purchase a subscription or tokens",
            )
        paid_action_name = map_bff_unblur_image_type_to_paid_action_name(image_type)
        paid_action_dataset = get_paid_action_dataset(session, paid_action_name)
        check_user_have_enough_currency(
            session, user_id, paid_action_dataset.price, CurrenciesTypes.TOKEN.value
        )
        tariff_plan_id = str(get_user_current_tariff_plan(session, user_id).id)
        additional_data = {
            "char_id": char_id,
            "image_id": str(image_id),
            "tariff_plan_id": tariff_plan_id,
            "config_id": str(config_id),
        }
        process_paid_action(
            session,
            user_id,
            paid_action_dataset,
            SourceNames.WEB_SITE,
            additional_data=additional_data,
        )
    except TariffPlanExpired as e:
        raise HTTPException(status_code=412, detail=e.message)
    except NotEnoughCurrencyError as e:
        raise HTTPException(status_code=402, detail=e.message)
    except Exception as e:
        session.rollback()
        raise e
    else:
        session.commit()
    return {"ok": True}


class AddReviewToMessageRequest(BaseModel):
    review_status: ReviewStatus
    review_categories: Optional[list[str]] = Field(default=None)
    review_text: Optional[str] = Field(default=None)


class AddReviewToMessageResponse(BaseModel):
    review_status: ReviewStatus


@router.patch("/chat/add_review/{message_id}", response_model=AddReviewToMessageResponse)
async def apply_review_to_message(
    message_id: int,
    review_data: AddReviewToMessageRequest,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Ensure that message belongs the current user
    user_id = current_user.user_id
    stmt = select(Message).where(Message.id == message_id and Message.user_id == user_id)
    res = session.exec(stmt).first()
    if not res:
        raise HTTPException(
            status_code=404,
            detail="Invalid message id. There are no messages with such an id among the user's messages",
        )
    review_status = review_data.review_status
    review_categories = review_data.review_categories
    review_text = review_data.review_text
    add_review_to_message(session, message_id, review_status, review_categories, review_text)
    return AddReviewToMessageResponse(review_status=review_status)


@router.get("/chat/last_messages")
async def get_last_user_messages(
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_id = UUID(current_user.user_id)
    stmt = (
        select(Message)
        .join(Channel, Channel.id == Message.channel_id)
        .where(Channel.user_id == user_id)
        .order_by(Message.channel_id, Message.inserted_at.desc())
        .distinct(Message.channel_id)
    )
    last_messages = session.exec(stmt).all()
    return last_messages


class ChatMessage(BaseModel):
    id: Optional[int]
    inserted_at: datetime
    text: Optional[str]
    attachments: Optional[list[ImagesDataResponse]]
    user_id: Optional[UUID]
    char_id: Optional[int]
    channel_id: int
    review_status: ReviewStatus
    review_categories: Optional[list[str]]
    review_text: Optional[str]
    message_type: Optional[ChatMessageType]


class ChatMessageResponse(BaseModel):
    messages: list[ChatMessage]
    limit: int
    offset: int
    total: int


@router.get("/chat/{char_id}/messages")
def get_chat_messages(
    char_id: int,
    limit: int = 100,
    offset: int = 0,
    config_id: Optional[UUID] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatMessageResponse:
    user_id = UUID(current_user.user_id)
    channel = session.exec(
        select(Channel).where(
            Channel.char_id == char_id, Channel.user_id == user_id, Channel.config_id == config_id
        )
    ).first()
    if channel is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    messages = session.exec(
        select(Message)
        .where(Message.channel_id == channel.id)
        .order_by(Message.inserted_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    messages = messages[::-1]
    grouped_messages = group_messages_attachments(messages)
    images_ids = get_message_images(grouped_messages)
    images_data = get_images_data(images_ids, user_id, session)

    # Create a mapping of image_id to image_data for faster lookup
    images_map = {img.image_id: img for img in images_data}
    # Convert messages to ChatMessageResponse objects with updated attachments
    response_messages = []
    for message in grouped_messages:
        if message.attachments:
            # Replace each attachment with corresponding image data
            updated_attachments = []
            for attachment in message.attachments:
                if attachment["type"] == "image":
                    image_id = attachment["id"]
                    if image_id in images_map:
                        updated_attachments.append(images_map[image_id])
            message_dict = message.model_dump()
            message_dict["attachments"] = updated_attachments
            response_messages.append(ChatMessage(**message_dict))
        else:
            response_messages.append(ChatMessage(**message.model_dump()))
    return ChatMessageResponse(
        messages=response_messages,
        limit=limit,
        offset=offset,
        total=len(messages),
    )
