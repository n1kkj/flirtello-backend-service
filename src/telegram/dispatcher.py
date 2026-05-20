import os
import traceback
from typing import Optional

import sentry_sdk
from asgiref.sync import sync_to_async
from fastapi import BackgroundTasks
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
from sqlmodel import Session, select

from src.db.lib.auth import SupabaseAuth
from src.db.lib.chat_models import ChatUser
from src.db.lib.gift_codes.common.models import GiftCode, GiftCodeUserLink
from src.telegram.DTO.chat import (
    SendChatMessageOutputSubDTO,  # noqa: F401 (imported for type references/log formatting)
)
from src.telegram.handlers.button_continue_preprocessor import (
    preprocess_button_continue,
)
from src.telegram.handlers.commands import route_command
from src.telegram.handlers.messages import process_regular_message
from src.telegram.handlers.payments import (
    handle_pre_checkout_query,
    handle_successful_payment,
)
from src.telegram.handlers.service import handle_my_chat_member
from src.telegram.handlers.voice_postprocessor import postprocess_text_to_voice
from src.telegram.handlers.voice_preprocessor import preprocess_voice_to_text
from src.telegram.lib.i18n import get_gettext_for_language
from src.telegram.utils.get_user_chat_setting import (
    get_current_char_id,
    get_current_config_id,
    get_user_language,
    is_language_overridden_by_user,
    set_user_language,
)
from src.translator import Translator
from src.translator.in_memory import (
    InMemoryCache,
    InMemoryEmbeddingService,
    InMemoryGlossary,
)
from src.translator.llm_client_uri import UriLLMClient
from src.translator.sql_tm import SQLTranslationMemory

from .api import (
    delete_message,
    send_tg_chat_action_typing,
    send_tg_message,
)
from .config import (
    API_URL,
    PASSKEY,
    SERVICE_ROLE_KEY,
    TELEGRAM_BOT_TOKEN,
    WEB_APP_FULL_LIST_URL,
    config,
    engine,
    logger,
    personal_tokens,
)
from .context import RequestContext
from .dependecies import get_async_session
from .handlers.callbacks import handle_callback_query
from .handlers.utils import parse_start_command_payload  # noqa: F401
from .keyboards import (
    create_character_selection_keyboard,
)
from .lib.sender_utils import send_mkt_event_fire_and_forget

# --- Synchronous Wrappers for Async Execution ---


def find_user_by_tg_id_sync_wrapper(tg_id: int) -> Optional[ChatUser]:
    """Synchronous wrapper for SupabaseAuth.find_user_by_tg_id."""
    auth_handler = SupabaseAuth(API_URL, SERVICE_ROLE_KEY, PASSKEY, engine)
    return auth_handler.find_user_by_tg_id(tg_id)


def create_user_by_tg_data_sync_wrapper(tg_sender_data: dict) -> ChatUser:
    """Synchronous wrapper for create_user_by_tg_data."""
    full_name = " ".join(
        [tg_sender_data.get("first_name", ""), tg_sender_data.get("last_name", "")]
    ).strip()
    if full_name == "":
        full_name = tg_sender_data.get("username")

    auth = SupabaseAuth(API_URL, SERVICE_ROLE_KEY, PASSKEY, engine)
    user = auth.create_tg_user(tg_sender_data["id"], full_name)

    return user


def check_welcome_gift_code_sync_wrapper(user_id):
    """Synchronous wrapper to check if user has activated welcome gift code 'TEST'."""
    with Session(engine) as session:
        gift_code = session.exec(
            select(GiftCode).where(GiftCode.code == "TEST")
        ).first()
        if not gift_code:
            logger.warning("Welcome gift code 'TEST' not found in database")
            return False
        activation = session.exec(
            select(GiftCodeUserLink).where(
                (GiftCodeUserLink.gift_code_id == gift_code.id)
                & (GiftCodeUserLink.user_id == user_id)
            )
        ).first()
        return activation is not None


async def process_telegram_update(
    data: dict,
    mono_char_id_from_webhook: int,
    context: RequestContext,
    background_tasks: BackgroundTasks,
):
    # --- Async adapters for sync functions ---
    async_find_user_by_tg_id = sync_to_async(
        find_user_by_tg_id_sync_wrapper, thread_sensitive=False
    )
    async_create_user_by_tg_data = sync_to_async(
        create_user_by_tg_data_sync_wrapper, thread_sensitive=False
    )
    # async_stats_command = sync_to_async(stats_command, thread_sensitive=False) # This is incorrect, stats_command is already async

    # --- Start of new logic: Handle my_chat_member first to fix Sentry issue and log kicks ---
    if "my_chat_member" in data:
        # This part remains synchronous as it uses a sync engine instance directly.
        auth_handler_for_kick = SupabaseAuth(
            supabase_url=API_URL,
            supabase_key=SERVICE_ROLE_KEY,
            passkey=PASSKEY,
            engine=engine,
        )
        await handle_my_chat_member(data, auth_handler_for_kick)
        return
    # --- End of new logic ---
    original_update_data = (
        data.copy()
    )  # Копируем на случай, если понадобится исходный объект
    if "webapp_data" in data:
        webapp_data_content = data["webapp_data"]
        sender_id_from_webapp = webapp_data_content.get("user_id")
        language_from_webapp = webapp_data_content.get("language_code")

        if sender_id_from_webapp is None:
            logger.error("Critical: webapp_data received without user_id.")
            sentry_sdk.capture_message(
                "webapp_data without user_id",
                level="error",
                extras={"update_data": original_update_data},
            )
            return

        data = {  # Переопределяем `data` для последующей обработки
            "message": {
                "from": {
                    "id": sender_id_from_webapp,
                    "first_name": webapp_data_content.get("first_name", "Web User"),
                    "last_name": webapp_data_content.get("last_name", ""),
                    "language_code": language_from_webapp,
                },
                "chat": {"id": sender_id_from_webapp, "type": "private"},
                "text": webapp_data_content.get("message", ""),
                # "date": webapp_data_content.get("date", int(time.time())) # Раскомментировать при необходимости
            }
        }
        logger.info(f"Processed webapp_data for user_id: {sender_id_from_webapp}")

    async for session in get_async_session():
        try:
            tm = SQLTranslationMemory(session)
            context.translator = Translator(
                tm=tm,
                glossary=InMemoryGlossary(),
                cache=InMemoryCache(),
                embedder=InMemoryEmbeddingService(),
                llm=UriLLMClient(config.translator_llm_url),
            )
            auth_handler = SupabaseAuth(
                supabase_url=API_URL,
                supabase_key=SERVICE_ROLE_KEY,
                passkey=PASSKEY,
                engine=engine,
            )

            MONO_CHAR_ID = (
                None if mono_char_id_from_webhook == -1 else mono_char_id_from_webhook
            )
            bot_type_is_mono = MONO_CHAR_ID is not None

            token_to_use: str
            active_char_id: Optional[int] = None  # Будет определен позже

            if bot_type_is_mono:
                active_char_id = MONO_CHAR_ID  # Для моно-бота active_char_id всегда его собственный ID
                # Set active_char_id in context for analytics (моно-бот)
                context.active_char_id = active_char_id
                if MONO_CHAR_ID not in personal_tokens:
                    env_token_name = f"PERSON_BOT_TOKEN_{MONO_CHAR_ID}"
                    ztoken = os.environ.get(env_token_name)
                    if ztoken is None:
                        logger.error(
                            f"CRITICAL: NO BOT TOKEN FOR MONO_CHAR_ID {MONO_CHAR_ID} (env var {env_token_name} not found). This monobot instance will not function correctly."
                        )
                        # Это приведет к KeyError ниже, если personal_tokens[active_char_id] будет вызван, что правильно.
                        personal_tokens[active_char_id] = None  # type: ignore
                    else:
                        personal_tokens[active_char_id] = ztoken
                        logger.info(
                            f"Successfully loaded token for MONO_CHAR_ID {MONO_CHAR_ID} from environment variable {env_token_name}."
                        )
                # Если токен не был найден и personal_tokens[active_char_id] теперь None, следующий вызов вызовет ошибку.
                # Это правильное поведение для неконфигурированного моно-бота.
                try:
                    token_to_use = personal_tokens[active_char_id]
                    if (
                        token_to_use is None
                    ):  # Дополнительная проверка на случай, если None был явно записан
                        raise KeyError(
                            f"Token for MONO_CHAR_ID {active_char_id} is None in personal_tokens."
                        )
                except KeyError:
                    logger.error(
                        f"CRITICAL: Failed to retrieve token for MONO_CHAR_ID {active_char_id} after attempting to load. Bot cannot operate."
                    )
                    # Можно либо re-raise, либо просто return, чтобы остановить обработку.
                    # Для ясности, давайте просто вернем, предполагая, что критическая ошибка залогирована.
                    return
            else:  # Общий бот
                token_to_use = TELEGRAM_BOT_TOKEN
                # active_char_id для общего бота будет определен позже, после получения объекта user

            # --- Language persistence logic (early) ---
            try:
                tg_from = None
                if "message" in data and isinstance(data.get("message"), dict):
                    tg_from = data["message"].get("from")
                elif "callback_query" in data and isinstance(
                    data.get("callback_query"), dict
                ):
                    tg_from = data["callback_query"].get("from")
                elif "pre_checkout_query" in data and isinstance(
                    data.get("pre_checkout_query"), dict
                ):
                    tg_from = data["pre_checkout_query"].get("from")

                if isinstance(tg_from, dict):
                    tg_id_candidate = tg_from.get("id")
                    lang_code_candidate = tg_from.get("language_code")
                    context.user_language = (
                        lang_code_candidate  # Устанавливаем язык в контекст
                    )
                    if tg_id_candidate is not None and lang_code_candidate:
                        user_for_lang = await async_find_user_by_tg_id(tg_id_candidate)
                        if user_for_lang is not None:
                            saved_lang = await get_user_language(
                                session, user_for_lang.id
                            )
                            lang_overridden = await is_language_overridden_by_user(
                                session, user_for_lang.id
                            )

                            final_lang_code = (
                                context.user_language
                            )  # Start with client language

                            if lang_overridden and saved_lang:
                                # If override is set, it has the highest priority
                                final_lang_code = saved_lang
                                logger.info(
                                    f"[{context.request_id}] Language is overridden by user setting: using '{saved_lang}'"
                                )
                            elif not lang_overridden:
                                # If not overridden, update the saved language to match the client's current language
                                if saved_lang != lang_code_candidate:
                                    logger.info(
                                        f"[{context.request_id}] User {user_for_lang.id} language changed from '{saved_lang}' to '{lang_code_candidate}'. Saving to settings."
                                    )
                                    await set_user_language(
                                        session, user_for_lang.id, lang_code_candidate
                                    )
                                final_lang_code = lang_code_candidate

                            context.user_language = final_lang_code  # Set the final determined language in the context

                        # The menu button is now set exclusively within the /lang command handler
                        # to avoid race conditions and ensure the UI updates predictably.
            except Exception as e:
                logger.warning(f"Failed to persist language early: {e}")

            # --- Create user if not exists (for all update types) ---
            # Extract tg_id and tg_from from any update type
            user: Optional[ChatUser] = None
            tg_id_for_user = None
            tg_from_for_user = None
            if "message" in data and isinstance(data.get("message"), dict):
                tg_from_for_user = data["message"].get("from")
                if tg_from_for_user:
                    tg_id_for_user = tg_from_for_user.get("id")
            elif "callback_query" in data and isinstance(
                data.get("callback_query"), dict
            ):
                tg_from_for_user = data["callback_query"].get("from")
                if tg_from_for_user:
                    tg_id_for_user = tg_from_for_user.get("id")
            elif "pre_checkout_query" in data and isinstance(
                data.get("pre_checkout_query"), dict
            ):
                tg_from_for_user = data["pre_checkout_query"].get("from")
                if tg_from_for_user:
                    tg_id_for_user = tg_from_for_user.get("id")

            # Create user if tg_id is available and user doesn't exist
            if tg_id_for_user is not None:
                user = await async_find_user_by_tg_id(tg_id_for_user)
                if user is None:
                    if tg_from_for_user:
                        logger.info(
                            f"User with TG ID {tg_id_for_user} not found, creating new user."
                        )
                        try:
                            user = await async_create_user_by_tg_data(tg_from_for_user)
                            logger.info(
                                f"Created new user {user.id} for TG ID {tg_id_for_user}."
                            )
                            # Mark as new user in context (will be verified by gift code check below)
                            context.is_new_user = True
                        except Exception as e:
                            logger.error(
                                f"Failed to create user for TG ID {tg_id_for_user}: {e}",
                                exc_info=True,
                            )
                            sentry_sdk.capture_exception(e)
                    else:
                        logger.warning(
                            f"Cannot create user: 'from' field missing for TG ID {tg_id_for_user}"
                        )
                else:
                    logger.info(
                        f"Found existing user {user.id} for TG ID {tg_id_for_user}."
                    )

                # Set user_id and active_char_id in context for analytics and other uses
                if user is not None:
                    context.user_id = user.id

                # Check if user has activated welcome gift code "TEST" to determine if truly new
                # This handles the case where user was created via WebApp but hasn't done /start yet
                if user is not None:
                    async_check_welcome_gift_code = sync_to_async(
                        check_welcome_gift_code_sync_wrapper, thread_sensitive=False
                    )
                    has_activated_welcome_code = await async_check_welcome_gift_code(
                        user.id
                    )

                    # Set is_new_user based on gift code activation status
                    context.is_new_user = not has_activated_welcome_code
                    logger.info(
                        f"User {user.id} welcome code activation: {has_activated_welcome_code}, "
                        f"setting context.is_new_user = {context.is_new_user}"
                    )

            # Handle pre_checkout_query
            if "pre_checkout_query" in data:
                await handle_pre_checkout_query(data, token_to_use)
                return

            # Handle successful_payment
            if "message" in data and "successful_payment" in data["message"]:
                await handle_successful_payment(
                    data, token_to_use, session, auth_handler, context
                )
                return

            # Обработка callback_query. Он использует context_token (token_to_use)
            if "callback_query" in data:
                await handle_callback_query(
                    data,
                    session,
                    token_to_use,
                    auth_handler,
                    context,
                )
                return

            # Преобразование webapp_data в структуру message, если необходимо
            # ЭТОТ БЛОК ПЕРЕНЕСЕН ВВЕРХ, ДО `with Session(engine) as session:`
            # Проверка на edited_message и обязательное наличие "message"
            if data.get("edited_message") is not None:
                await send_tg_message(
                    data["edited_message"]["chat"]["id"],
                    "<system> editing past messages is not supported, don't even try :D",
                    token_to_use,
                )
                return

            if (
                "message" not in data
                or "chat" not in data["message"]
                or "id" not in data["message"]["chat"]
            ):
                warning_message = "Update received without 'message.chat.id' key or not handled by previous blocks."
                logger.warning(
                    warning_message,
                    extra={
                        "original_update": original_update_data,
                        "current_data": data,
                    },
                )
                sentry_sdk.capture_message(
                    warning_message,
                    level="warning",
                    extras={
                        "original_update": original_update_data,
                        "current_data": data,
                    },
                )
                return

            sender_chat_id = data["message"]["chat"]["id"]

            # User should already be created above (before callback/message handlers)
            # Just get it for message processing
            user = await async_find_user_by_tg_id(sender_chat_id)
            if user is None:
                logger.error(
                    f"User with TG ID {sender_chat_id} not found. This should not happen - user should be created earlier in dispatcher."
                )
                sentry_sdk.capture_message(
                    f"User not found for message processing: TG ID {sender_chat_id}",
                    level="error",
                    extras={"data": data},
                )
                return

            # =================================================================================
            # Single Source of Truth for Language Determination
            # =================================================================================
            final_lang_code = "en"  # Default fallback
            try:
                # 1. Get language from the Telegram client
                client_lang = "en"
                tg_from = data.get("message", {}).get("from", {}) or data.get(
                    "callback_query", {}
                ).get("from", {})
                if tg_from and tg_from.get("language_code"):
                    client_lang = tg_from["language_code"]

                # 2. Check for user override in the database
                saved_lang = await get_user_language(session, user.id)
                lang_overridden = await is_language_overridden_by_user(session, user.id)

                # 3. Determine the final language
                if lang_overridden and saved_lang:
                    # Override is the highest priority
                    final_lang_code = saved_lang
                else:
                    # Otherwise, use the client's language
                    final_lang_code = client_lang
                    # And if it has changed, update it in the DB for future reference
                    if saved_lang != client_lang:
                        await set_user_language(session, user.id, client_lang)

                # 4. Set the determined language in the context for all subsequent operations
                context.user_language = final_lang_code
                logger.info(
                    f"[{context.request_id}] Final language for user {user.id} is '{final_lang_code}' (overridden={lang_overridden}, client_lang='{client_lang}')"
                )
            except Exception as e:
                logger.error(
                    f"Error determining language for user {user.id}: {e}", exc_info=True
                )
                context.user_language = "en"  # Fallback on error
            # =================================================================================

            # Финализация active_char_id для общего бота
            if not bot_type_is_mono:
                char_id_from_settings = await get_current_char_id(
                    session, user.id
                )  # Теперь user точно определен
                if char_id_from_settings is not None:
                    active_char_id = char_id_from_settings
                # Если char_id_from_settings is None, active_char_id останется None (для общего бота без выбора)

                # Set active_char_id in context for analytics
                context.active_char_id = active_char_id

            # ============================================================
            # ПРЕПРОЦЕССОР: Voice → Text (САМЫЙ РАННИЙ ЭТАП!)
            # Проверяет баланс на STT и TTS, конвертирует voice в text
            # Устанавливает context.is_voice_message и context.can_afford_tts
            # ============================================================
            data = await preprocess_voice_to_text(
                data, token_to_use, user, sender_chat_id, session, context
            )

            if data is None:
                # Нет денег на STT - сообщение уже отправлено
                return

            # Проверка режима обслуживания
            if os.environ.get("MM") is not None:
                await send_tg_message(
                    sender_chat_id, "Maintenance mode, come back later", token_to_use
                )
                return

            logger.info(
                f"Processing message from user: {user.id} (TG: {sender_chat_id}), active_char_id: {active_char_id}, bot_type_is_mono: {bot_type_is_mono}, is_voice: {context.is_voice_message}"
            )

            # После препроцессора data всегда имеет text (даже если был voice)
            text = data["message"].get("text")
            if text is None:
                logger.info(
                    "Received non-text message (e.g., photo, sticker). No text to process."
                )
                return

            current_config_id_from_settings = await get_current_config_id(
                session, user.id
            )

            # Get translated command for "Get Image" based on the single source of truth language
            lang_code = context.user_language
            _ = get_gettext_for_language(lang_code)
            get_image_command_text = _("Get Image ❤️‍🔥")
            continue_command_text = _("Continue 💬")

            # Define the list of commands for help messages
            GENERAL_BOT_COMMANDS = [
                "/start",
                "/list",
                "/help",
                "/stats",
                "/story",
                "/photo",
                "/gift",
                "/lang",
            ]
            commands_text = ", ".join(GENERAL_BOT_COMMANDS)

            # Check if message is continue button click
            if text == continue_command_text:
                # Delete the button message from chat
                try:
                    message_id = data.get("message", {}).get("message_id")
                    if message_id:
                        await delete_message(sender_chat_id, message_id, token_to_use)
                        logger.info(
                            f"Deleted Continue button message {message_id} for user {user.id}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to delete continue button message for user {user.id}: {e}"
                    )
                    # Continue processing - deletion is not critical

                # Send analytics event
                await send_mkt_event_fire_and_forget(user.id, "tg_continue_button")

                # Replace text with localized "continue" for the model
                data = await preprocess_button_continue(data, context)
                text = data["message"]["text"]

            # Гейткипер: общий бот, нет активного персонажа, действие требует персонажа
            # Проверяем это ДО роутинга команд, чтобы не пропускать /photo или обычные сообщения
            if (
                not bot_type_is_mono
                and active_char_id is None
                and (
                    text == "/photo"
                    or text == get_image_command_text
                    or text == continue_command_text
                    or not text.startswith("/")
                )
            ):
                logger.info(
                    f"General bot: User {user.id} (TG: {sender_chat_id}) has no active character for action '{text}'. Prompting for selection."
                )
                await send_tg_chat_action_typing(sender_chat_id, token_to_use)

                (
                    selection_prompt_text,
                    character_keyboard_markup,
                ) = await create_character_selection_keyboard(
                    session,
                    include_descriptions_in_message=True,
                    web_app_url=WEB_APP_FULL_LIST_URL,
                    language_code=await get_user_language(session, user.id) or "en",
                    context=context,
                )
                has_character_buttons = False
                if character_keyboard_markup and character_keyboard_markup.get(
                    "inline_keyboard"
                ):
                    for row in character_keyboard_markup["inline_keyboard"]:
                        if any(
                            button.get("callback_data", "").startswith("/start ")
                            for button in row
                        ):
                            has_character_buttons = True
                            break

                if not has_character_buttons:
                    text_for_no_chars = _(
                        "Чтобы продолжить, выберите персонажа. No characters available for quick selection yet. Please check the full list!"
                    )
                    only_webapp_keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": _("✨ Open all characters"),
                                    "web_app": {
                                        "url": f"{WEB_APP_FULL_LIST_URL}?lang={lang_code}"
                                    },
                                }
                            ]
                        ]
                    }
                    await send_tg_message(
                        sender_chat_id,
                        text_for_no_chars,
                        token_to_use,
                        reply_markup=only_webapp_keyboard,
                    )
                    return
                else:
                    await send_tg_message(
                        sender_chat_id,
                        selection_prompt_text,
                        token_to_use,
                        reply_markup=character_keyboard_markup,
                    )
                # session.commit() здесь не нужен, если не было изменений в сессии.
                # Если create_character_selection_keyboard не меняет сессию, то коммит не нужен.
                # Оставим пока без коммита, т.к. это в основном чтение и отправка.
                return  # Завершаем обработку, ожидая выбора пользователя

            # ============================================================
            # РОУТИНГ КОМАНД через centralized router
            # ============================================================
            command_handled = await route_command(
                text=text,
                data=data,
                bot_type_is_mono=bot_type_is_mono,
                mono_char_id=MONO_CHAR_ID,
                token=token_to_use,
                sender_chat_id=sender_chat_id,
                session=session,
                user=user,
                active_char_id=active_char_id,
                config_id=current_config_id_from_settings,
                context=context,
                background_tasks=background_tasks,
                lang_code=lang_code,
                get_image_command_text=get_image_command_text,
                engine=engine,
            )

            if command_handled:
                await session.commit()
                return

            # ============================================================
            # ОБРАБОТКА ОБЫЧНОГО СООБЩЕНИЯ (если не команда)
            # ============================================================
            if text.startswith("/"):
                # Неизвестная команда
                help_text_unknown_command = (
                    _("Unknown command: {text}.\nAvailable commands:").format(text=text)
                    + f" {commands_text}"
                )
                if WEB_APP_FULL_LIST_URL:
                    lang_param = f"?lang={lang_code}" if lang_code else ""
                    final_web_app_url = f"{WEB_APP_FULL_LIST_URL}{lang_param}"
                    help_text_unknown_command += _(
                        "\nFull character catalog: {url}"
                    ).format(url=final_web_app_url)
                await send_tg_message(
                    sender_chat_id, help_text_unknown_command, token_to_use
                )
            elif active_char_id is not None:
                # Обычное текстовое сообщение - обрабатываем через regular_message
                response_dto = await process_regular_message(
                    data,
                    active_char_id,
                    token_to_use,
                    current_config_id_from_settings,
                    sender_chat_id,
                    session,
                    user,
                    context,
                )

                # ============================================================
                # ПОСТПРОЦЕССОР: Text → Voice (если context.is_voice_message и can_afford_tts)
                # ============================================================
                if response_dto and response_dto.messages:
                    for msg in response_dto.messages:
                        if msg.message:
                            await postprocess_text_to_voice(
                                msg.message,
                                sender_chat_id,
                                token_to_use,
                                user,
                                context,
                            )
            else:
                # Общий бот без активного персонажа (должен был быть пойман гейткипером)
                logger.error(
                    f"Critical error: Reached regular message processing with no active_char_id for user {user.id} (TG: {sender_chat_id}). Text: '{text}'. Bot type mono: {bot_type_is_mono}. This should have been caught by the gatekeeper."
                )
                await send_tg_message(
                    sender_chat_id,
                    "Произошла непредвиденная ошибка. Пожалуйста, выберите персонажа или сообщите администратору.",
                    token_to_use,
                )

            await session.commit()  # Основной коммит в конце успешной обработки

            # --- Performance logging ---
            if context and context.timings:
                timings_str = "; ".join(
                    [f"{t.label}={t.duration_ms:.2f}ms" for t in context.timings]
                )
                total_time = sum(t.duration_ms for t in context.timings)
                logger.info(
                    f"[{context.request_id}] Performance metrics: Total measured: {total_time:.2f}ms; Breakdown: {timings_str}"
                )

                # --- Grafana Metrics Export ---
                from src.telegram.metrics_exporter import metrics_exporter
                metrics_exporter.export_timings(context)

        except SQLTimeoutError as e:
            # Специальная обработка ошибок пула соединений
            await session.rollback()  # Откатываем изменения в сессии при любой ошибке
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("error_type", "database_pool_timeout")
                scope.set_context(
                    "pool_info",
                    {
                        "error": str(e),
                        "user_id": str(context.user_id)
                        if hasattr(context, "user_id")
                        else None,
                        "request_id": context.request_id
                        if hasattr(context, "request_id")
                        else None,
                    },
                )
                scope.level = "error"
                sentry_sdk.capture_exception(e)
            pretty_e = "{}: {} {}".format(type(e).__name__, e, traceback.format_exc())
            logger.error(f"⚠️ DATABASE POOL TIMEOUT in dispatcher: {pretty_e}")
        except Exception as e:
            await session.rollback()  # Откатываем изменения в сессии при любой ошибке
            sentry_sdk.capture_exception(e)
            pretty_e = "{}: {} {}".format(type(e).__name__, e, traceback.format_exc())
            logger.error(f"Error in background task: {pretty_e}")
