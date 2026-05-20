from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, text

from src.db.lib.auth import SupabaseAuth
from src.db.lib.chat_models import Channel, ChatUser
from src.db.lib.content_models import ContentCharacter
from src.telegram.DTO.chat import (
    SendChatMessageInputDTO,
    SendChatMessageOutputDTO,
    SendChatMessageOutputSubDTO,  # Нужен для start_new_chat_tg
    StartNewChatOutputDTO,
)
from src.telegram.enums.settings_keys import UserSettingsKeys
from src.telegram.use_cases.get_response_from_character import (
    get_response_from_character,
)
from src.telegram.use_cases.start_chat_with_char import start_chat_with_char
from src.telegram.utils.get_user_chat_setting import (
    get_current_char_id,
    get_current_config_id,
)

# Импортируем из api module то, что нужно здесь (например, send_tg_chat_action_typing)
from .api import send_tg_chat_action_typing

# Импортируем необходимые объекты из config.py
from .config import API_URL, PASSKEY, SERVICE_ROLE_KEY, logger
from .context import RequestContext
from .dependecies import async_engine  # Нужен только для create_user_by_tg_data


# Вспомогательная функция dict_to_hstore_str, если она используется только здесь
# Если она более общая, ее можно вынести в utils.py
def dict_to_hstore_str(d: Optional[dict]) -> str:
    """Convert a dictionary to hstore format string, handling enum keys"""
    if not d:
        return ""
    items = []
    for k, v in d.items():
        if v is not None:  # Только добавляем не-None значения
            items.append(f'"{str(k)}"=>"{v}"')
    return ", ".join(items)


async def create_user_by_tg_data(tg_sender_data) -> ChatUser:
    print("create_user_by_tg_data", tg_sender_data)
    full_name = " ".join(
        [tg_sender_data.get("first_name", ""), tg_sender_data.get("last_name", "")]
    ).strip()
    if full_name == "":
        full_name = tg_sender_data.get("username")

    auth = SupabaseAuth(API_URL, SERVICE_ROLE_KEY, PASSKEY, async_engine)
    user = await auth.create_tg_user(tg_sender_data["id"], full_name)

    return user


async def write_to_current_chat(
    data: dict,  # Это оригинальный data из вебхука
    known_char_id: int,
    token: str,  # Токен для отправки chat_action
    user: ChatUser,
    session: AsyncSession,  # ✅ ИСПРАВЛЕНИЕ: принимаем сессию как параметр вместо создания новой
    config_id: Optional[UUID] = None,
    context: Optional[RequestContext] = None,
) -> SendChatMessageOutputDTO:
    # sender = data["message"]["from"] # Не используется sender напрямую
    sender_chat_id = data["message"]["chat"]["id"]  # Нужен для chat_action
    message_text: str = data["message"].get("text", "")
    if message_text.strip() == "":
        return SendChatMessageOutputDTO(messages=[])

    # ✅ ИСПРАВЛЕНИЕ: используем переданную сессию вместо создания новой
    if known_char_id != -1:
        char_id = known_char_id
    else:
        char_id = await get_current_char_id(session, user.id) or 1

    char = await session.get(ContentCharacter, char_id)

    if char is None:
        return SendChatMessageOutputDTO.from_single_text_message(message="/start")

    if config_id is None:
        config_id = await get_current_config_id(session, user.id)

    result = await session.execute(
        select(Channel).where(
            Channel.char_id == char_id,
            Channel.user_id == user.id,
            Channel.config_id == config_id,  # Используем актуальный config_id
        )
    )
    channel = result.scalars().first()

    if channel is None:
        return SendChatMessageOutputDTO.from_single_text_message(message="/start")

    # Отправка chat_action должна использовать токен, соответствующий боту, который обрабатывает чат
    await send_tg_chat_action_typing(sender_chat_id, token)

    logger.info(
        f"[CHAT_LOGIC_DEBUG] About to call get_response_from_character: char_id={char_id}, user_id={user.id}, config_id={config_id} (type: {type(config_id)})"
    )

    messages_responses = await get_response_from_character(
        char_id,
        user.id,
        SendChatMessageInputDTO(message=message_text, config_id=config_id),
        session,
        context=context,
    )
    return messages_responses


async def start_new_chat_tg(
    data: dict,  # Это оригинальный data из вебхука или mock_message_data
    char_id: Optional[int],
    # token: str, # Токен больше не нужен здесь, т.к. отправка сообщений вынесена
    user: ChatUser,
    session: AsyncSession,
    explicit_config_id: Optional[UUID] = None,
    context: Optional[RequestContext] = None,
) -> StartNewChatOutputDTO:
    logger.info(
        f"[SNC_TG_DEBUG] start_new_chat_tg CALLED: char_id={char_id}, user_id={user.id}, explicit_config_id={explicit_config_id} (type: {type(explicit_config_id)})"
    )

    # --- Async adapters for sync functions ---
    from src.telegram.async_adapters import async_reset_images_user

    if data["message"]["chat"]["type"] != "private":
        return StartNewChatOutputDTO(
            messages=[
                SendChatMessageOutputSubDTO(
                    message="Only private chats are supported =("
                )
            ]
        )

    user_id = user.id

    real_char_id = char_id

    if real_char_id is None:
        if user.settings is not None:
            real_char_id = user.settings.get(
                UserSettingsKeys.CURRENT_CHAR_ID.value, None
            )
            if isinstance(real_char_id, str) and real_char_id.isdigit():
                real_char_id = int(real_char_id)
            elif not isinstance(real_char_id, int):
                real_char_id = None

        if real_char_id is None:
            curr_char_from_db_result = await session.execute(select(ContentCharacter))
            curr_char_from_db = curr_char_from_db_result.scalars().first()
            if curr_char_from_db is None:
                return StartNewChatOutputDTO(
                    messages=[
                        SendChatMessageOutputSubDTO(message="No characters found")
                    ]
                )
            real_char_id = curr_char_from_db.id

    char_check = await session.get(ContentCharacter, real_char_id)
    if char_check is None:
        fallback_char_result = await session.execute(select(ContentCharacter))
        fallback_char = fallback_char_result.scalars().first()
        if fallback_char is None:
            return StartNewChatOutputDTO(
                messages=[
                    SendChatMessageOutputSubDTO(
                        message="Character not found and no fallback available"
                    )
                ]
            )
        real_char_id = fallback_char.id

    final_effective_config_id_for_chat_and_settings = explicit_config_id

    logger.info(f"[SNC_TG] Char_id to start: {real_char_id}")
    logger.info(
        f"[SNC_TG] Explicit_config_id received by start_new_chat_tg: {explicit_config_id}"
    )
    logger.info(
        f"[SNC_TG] Final config_id for chat and to save in settings: {final_effective_config_id_for_chat_and_settings}"
    )

    settings_to_save = {
        UserSettingsKeys.CURRENT_CHAR_ID: real_char_id,
        UserSettingsKeys.CONFIG_ID: str(final_effective_config_id_for_chat_and_settings)
        if final_effective_config_id_for_chat_and_settings is not None
        else None,
    }
    hstore_settings = dict_to_hstore_str(settings_to_save)
    logger.info(
        f"[SNC_TG] Attempting to save settings for user {user.id}: {hstore_settings}"
    )

    save_settings_query = text(
        """
    UPDATE public.users
    SET settings = CASE
        WHEN settings IS NULL THEN cast(:settings as hstore)
        ELSE settings || cast(:settings as hstore)
    END
    WHERE id = :id
    """
    )
    await session.execute(
        save_settings_query,
        {"settings": hstore_settings, "id": user.id},
    )
    await session.commit()
    logger.info(f"[SNC_TG] Executed save_settings_query for user {user.id}")

    # Reset history only if character or config actually changed to avoid heavy deletes on each /start
    try:
        current_char_id_in_settings = None
        current_config_id_in_settings = None
        if user.settings is not None:
            current_char_id_in_settings = user.settings.get(
                UserSettingsKeys.CURRENT_CHAR_ID.value
            )
            current_config_id_in_settings = user.settings.get(
                UserSettingsKeys.CONFIG_ID.value
            )
        char_changed = str(current_char_id_in_settings) != str(real_char_id)
        conf_changed = str(current_config_id_in_settings) != (
            str(final_effective_config_id_for_chat_and_settings)
            if final_effective_config_id_for_chat_and_settings is not None
            else None
        )
        if char_changed or conf_changed:
            await async_reset_images_user(user.id)
            logger.info(
                f"[SNC_TG] Called reset_images_user for user {user.id} (char_changed={char_changed}, conf_changed={conf_changed})"
            )
        else:
            logger.info(
                f"[SNC_TG] Skipped reset_images_user for user {user.id} (no changes)"
            )
    except Exception as _e_reset:
        logger.warning(
            f"[SNC_TG] Failed to check/perform reset_images_user: {_e_reset}"
        )

    updated_user_in_snc = await session.get(ChatUser, user.id)
    if updated_user_in_snc and updated_user_in_snc.settings:
        logger.info(
            f"[SNC_TG] User settings AFTER update in start_new_chat_tg for user {user.id}: {updated_user_in_snc.settings}"
        )
    else:
        logger.warning(
            f"[SNC_TG] Could not verify user settings after update for user {user.id}"
        )

    if updated_user_in_snc:
        user.settings = updated_user_in_snc.settings

    logger.info(
        f"[SNC_CALL_DEBUG] About to call start_chat_with_char: char_id={real_char_id}, user_id={user_id}"
    )
    first_messages = await start_chat_with_char(
        char_id=real_char_id,
        user_id=user_id,
        session=session,
        archive_existing_chat=True,
        config_id=final_effective_config_id_for_chat_and_settings,
        context=context,
    )
    # await sleep(1) # sleep удален, т.к. он был для симуляции и не несет логической нагрузки здесь

    # Welcome messages are now shown in process_start_command, not here
    # No system messages to add before character messages

    return first_messages
