from typing import Optional, cast
from uuid import UUID

import sentry_sdk
from sqlmodel import Session

from src.db.lib.chat_models import ChatUser
from src.db.lib.content_models import DirectusFile, ImageInfo
from src.db.lib.gift_codes.common.exceptions import (
    GiftCodeAlreadyActivated,
    GiftCodeInactive,
    GiftCodeNotFound,
)
from src.telegram.api import (
    download_and_send_image,
    send_tg_chat_action_typing,
    send_tg_chat_action_upload_photo,
    send_tg_message,
    set_chat_menu_button,
)
from src.telegram.chat_logic import start_new_chat_tg
from src.telegram.config import (
    MKT_COLLECTOR_API_KEY,
    MKT_COLLECTOR_URL,
    STORAGE_ROOT,
    WEB_APP_FULL_LIST_URL,
    logger,
)
from src.telegram.context import RequestContext
from src.telegram.enums.settings_keys import UserSettingsKeys
from src.telegram.handlers.utils import (
    merge_attachment_messages,
    parse_start_command_payload,
)
from src.telegram.keyboards import (
    create_character_selection_keyboard,
    create_context_keyboard,
)
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.lib.insufficient_balance import (
    check_and_notify_zero_balance,
    send_no_tokens_message_with_keyboards,
)
from src.telegram.lib.sender_utils import send_marketing_event
from src.telegram.template_messages import TemplateMessages


async def process_start_command(
    data: dict,
    MONO_CHAR_ID: Optional[int],
    token: str,
    config_id_from_settings: Optional[
        UUID
    ],  # This is the GLOBAL config_id from user settings, used for context/logging
    sender_chat_id: int,
    session: Session,
    user: ChatUser,
    context: RequestContext,
):
    command_text = data["message"]["text"]
    payload = parse_start_command_payload(command_text)
    lang_code = context.user_language or "en"
    _ = get_gettext_for_language(lang_code)
    logger.info(
        f"[{context.request_id}] Processing /start command with parsed payload: {payload} for user {user.id}"
    )

    # --- Set internal_source in context (needed before welcome message check) ---
    if payload.internal_source:
        context.internal_source = payload.internal_source
        logger.info(f"[{context.request_id}] Set internal_source in context: {context.internal_source}")

    # --- Handle new user: tokens and welcome message ---
    # context.is_new_user is already set in dispatcher.py based on gift code activation check
    if context.is_new_user:
        # 1. Activate gift code "TEST"
        try:
            from src.telegram.async_adapters import async_gift_code_process
            await async_gift_code_process("TEST", user.id)
            logger.info(
                f"[{context.request_id}] Successfully activated welcome gift code 'TEST' for new user {user.id}."
            )
        except (GiftCodeNotFound, GiftCodeInactive, GiftCodeAlreadyActivated) as e:
            logger.warning(
                f"[{context.request_id}] Could not activate welcome gift code 'TEST' for new user {user.id}: {e}"
            )
            sentry_sdk.capture_exception(e)
        except Exception as e:
            logger.error(
                f"[{context.request_id}] An unexpected error occurred during welcome gift activation for user {user.id}: {e}"
            )
            sentry_sdk.capture_exception(e)

    # --- Send welcome messages (all scenarios) ---
    if context.internal_source == 'quiz':
        if context.is_new_user:
            # Scenario 1: New user + quiz → show combined welcome + quiz message
            quiz_onboarding = _("quiz_onboarding_message")
            await send_tg_message(sender_chat_id, quiz_onboarding, token)
        else:
            # Scenario 3: Existing user + quiz → show only quiz match message
            quiz_match_msg = _("quiz_match_message")
            await send_tg_message(sender_chat_id, quiz_match_msg, token)
    elif context.is_new_user:
        # Scenario 2: New user + regular start → show regular welcome
        welcome_message = _(
            "Welcome! 👋\nChoose your first story from the list below or open the full catalog 📚"
        )
        await send_tg_message(sender_chat_id, welcome_message, token)

    # --- Set internal_source in context ---
    if payload.internal_source:
        context.internal_source = payload.internal_source
        logger.info(f"[{context.request_id}] Set internal_source in context: {context.internal_source}")

    # --- Set localized Chat Menu Button (WebApp) for this user ---
    try:
        await set_chat_menu_button(
            token,
            text=_("✨ Open all characters"),
            web_app_url=cast(str, WEB_APP_FULL_LIST_URL),
            chat_id=sender_chat_id,
        )
    except Exception as e:
        logger.warning(f"Failed to set localized chat menu button for user {user.id}: {e}")

    # --- 1. Handle marketing collector ---
    if payload.mkt_source:
        logger.info(f"Sending mkt data for user {user.id}, source: {payload.mkt_source}")
        if not MKT_COLLECTOR_URL or not MKT_COLLECTOR_API_KEY:
            logger.error("MKT Collector URL or API Key is not configured. Cannot send event.")
        else:
            success, message = await send_marketing_event(
                mkt_collector_url=MKT_COLLECTOR_URL,
                mkt_collector_api_key=MKT_COLLECTOR_API_KEY,
                user_uuid=str(user.id),
                event_name="tg_ad_start",
                params={"source": payload.mkt_source},
                retries=3,
                retry_delay=1.0,
            )
            if success:
                logger.info(f"Successfully sent mkt event 'tg_ad_start' for user {user.id}")
            else:
                error_message = f"Failed to send mkt event 'tg_ad_start' for user {user.id}. Reason: {message}"
                logger.error(error_message)
                sentry_sdk.capture_message(f"MKT Collector event sending failed: {message}", level="error")

    # --- 2. Handle onboarding flow (all configs list) ---
    user_had_saved_char_id_in_settings: bool = False
    saved_char_id_from_settings: Optional[int] = None
    if user.settings:
        raw_char_id_val = user.settings.get(UserSettingsKeys.CURRENT_CHAR_ID.value)
        if isinstance(raw_char_id_val, (str, int)) and str(raw_char_id_val).isdigit():
            user_had_saved_char_id_in_settings = True
            saved_char_id_from_settings = int(raw_char_id_val)

    is_fresh_start_for_general_bot = (
        MONO_CHAR_ID is None and not payload.char_id and not user_had_saved_char_id_in_settings
    )

    if payload.is_onboarding_request or is_fresh_start_for_general_bot:
        if payload.is_onboarding_request:
            logger.info(f"Forced onboarding flow (character list) for user {user.id}.")
        else:
            logger.info(f"New user onboarding flow (character list) for user {user.id}.")

        await send_tg_chat_action_typing(sender_chat_id, token)
        # welcome_message = _(
        #     "Welcome! 👋\nChoose your first story from the list below or open the full catalog 📚"
        # )
        # await send_tg_message(sender_chat_id, welcome_message, token)

        message_text, character_keyboard_markup = await create_character_selection_keyboard(
            session,
            include_descriptions_in_message=True,
            web_app_url=WEB_APP_FULL_LIST_URL,
            language_code=(context.user_language or "en"),
            context=context,
        )
        await send_tg_message(
            sender_chat_id, message_text, token, reply_markup=character_keyboard_markup
        )
        return

    # --- 3. Determine the final char_id and config_id to use for starting the chat ---
    char_id_to_start_chat_with: Optional[int] = None
    config_id_to_use_explicitly: Optional[UUID] = None

    if MONO_CHAR_ID is not None:
        char_id_to_start_chat_with = MONO_CHAR_ID
        config_id_to_use_explicitly = payload.config_id
        logger.info(
            f"Mono Bot: Starting with char {char_id_to_start_chat_with}, explicit_config_id from payload: {config_id_to_use_explicitly}"
        )
    else:  # General Bot decision logic
        if payload.char_id is not None:
            # User provided char_id via command
            char_id_to_start_chat_with = payload.char_id
            config_id_to_use_explicitly = payload.config_id
            logger.info(
                f"General Bot: Command contained char_id {char_id_to_start_chat_with}. explicit_config_id: {config_id_to_use_explicitly}"
            )
        elif user_had_saved_char_id_in_settings and saved_char_id_from_settings is not None:
            # Plain /start and user has a saved char_id.
            char_id_to_start_chat_with = saved_char_id_from_settings
            config_id_to_use_explicitly = config_id_from_settings  # Use the global config from settings
            logger.info(
                f"General Bot: Plain /start. Using saved char_id {char_id_to_start_chat_with} with SAVED config_id {config_id_to_use_explicitly} from user settings."
            )
        else:
            # Plain /start and user has NO saved char_id. Show character selection list.
            logger.info(
                "General Bot: Plain /start, no saved char. Showing character selection list."
            )
            await send_tg_chat_action_typing(sender_chat_id, token)
            message_text, character_keyboard_markup = await create_character_selection_keyboard(
                session,
                include_descriptions_in_message=True,
                web_app_url=WEB_APP_FULL_LIST_URL,
                language_code=(context.user_language or "en"),
                context=context,
            )

            has_character_buttons = False
            if character_keyboard_markup and character_keyboard_markup.get("inline_keyboard"):
                for row in character_keyboard_markup["inline_keyboard"]:
                    if any("callback_data" in button for button in row):
                        has_character_buttons = True
                        break

            if not has_character_buttons:
                text_for_no_chars = _(
                    "No characters available for quick selection yet. Please check the full list!"
                )
                only_webapp_keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": _("✨ Open all characters"),
                                "web_app": {"url": WEB_APP_FULL_LIST_URL},
                            }
                        ]
                    ]
                }
                await send_tg_message(
                    sender_chat_id,
                    text_for_no_chars,
                    token,
                    reply_markup=only_webapp_keyboard,
                )
            else:
                await send_tg_message(
                    sender_chat_id, message_text, token, reply_markup=character_keyboard_markup
                )
            return

    # --- 4. Safety check and proceeding to start_new_chat_tg ---
    if char_id_to_start_chat_with is None:
        logger.error(
            f"Critical Logic Flaw: char_id_to_start_chat_with is None before calling start_new_chat_tg. User: {user.id}, Command: '{command_text}', Payload: {payload}"
        )
        await send_tg_message(
            sender_chat_id,
            _(
                "An error occurred while determining the character. Please try again or select from the /list."
            ),
            token,
        )
        return

    logger.info(
        f"process_start_command: Proceeding to start_new_chat_tg. CharID: {char_id_to_start_chat_with}, ExplicitConfigID: {config_id_to_use_explicitly}."
    )

    first_messages = await start_new_chat_tg(
        data=data,
        char_id=char_id_to_start_chat_with,
        user=user,
        session=session,
        explicit_config_id=config_id_to_use_explicitly,
        context=context,
    )

    if first_messages and first_messages.messages:
        first_messages.messages = merge_attachment_messages(first_messages.messages)

        # Разделяем сообщения на обычные и NO_TOKENS
        regular_messages = []
        has_insufficient_balance = False
        
        for msg in first_messages.messages:
            if msg.insufficient_balance:
                has_insufficient_balance = True
                logger.info(f"Detected insufficient_balance in /start: {msg.message[:50]}...")
            else:
                regular_messages.append(msg)
        
        # Отправка обычных сообщений
        for message in regular_messages:
            if message.attachments:
                for attachment in message.attachments:
                    await send_tg_chat_action_upload_photo(sender_chat_id, token)
                    image = await session.get(ImageInfo, attachment.id)
                    if image is None:
                        logger.error(
                            f"Image {attachment.id} not found for char {char_id_to_start_chat_with}"
                        )
                        await send_tg_message(
                            sender_chat_id, _("Problems loading the picture... 💔"), token
                        )
                        continue
                    file = await session.get(DirectusFile, image.image)
                    if file is None:
                        logger.error(
                            f"File {image.image} not found for char {char_id_to_start_chat_with}"
                        )
                        await send_tg_message(sender_chat_id, _("Picture file not found... 💔"), token)
                        continue
                    await download_and_send_image(
                        f"{STORAGE_ROOT}/{file.filename_disk}",
                        str(sender_chat_id),
                        True,
                        token,
                        caption=message.message,
                    )
            else:
                # Обычное текстовое сообщение
                await send_tg_message(
                    sender_chat_id,
                    message.message,
                    token,
                    reply_markup=create_context_keyboard(lang_code)
                )
        
        # NO_TOKENS сообщение ПОСЛЕДНИМ
        if has_insufficient_balance:
            await send_no_tokens_message_with_keyboards(
                sender_chat_id=sender_chat_id,
                message_text=_(TemplateMessages.NO_TOKENS.value),
                token=token,
                lang_code=lang_code,
                context=context,
                source="start_command",
            )
            logger.info("✅ NO_TOKENS sent as last message in /start with keyboards")
        
        # Проактивная проверка баланса (только если не было недостатка средств)
        if not has_insufficient_balance:
            await check_and_notify_zero_balance(
                user_id=user.id,
                sender_chat_id=sender_chat_id,
                token=token,
                context=context,
                session=session,
            )
