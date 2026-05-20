import logging
import re
from typing import Any, Optional, Union
from uuid import UUID

from asyncpg.exceptions import ConnectionDoesNotExistError
from sqlalchemy.exc import DBAPIError, PendingRollbackError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import text

from src.db.lib.chat_models import ChatUser
from src.telegram.enums.settings_keys import UserSettingsKeys

logger = logging.getLogger(__name__)
T = object


async def get_user_chat_setting(
    session: AsyncSession,
    user_id: UUID,
    setting_key: Union[str, UserSettingsKeys],
    default_value: T = None,
    cast_to: Optional[type] = None,
) -> Optional[Any]:
    """
    Get a specific setting from user's hstore settings
    Args:
        session: SQLModel session
        user_id: User's UUID
        setting_key: Key to look up in hstore settings (string or UserSettingsKeys enum)
        default_value: Value to return if setting not found
        cast_to: Type to cast the value to (e.g. int, UUID)
    Returns:
        The setting value cast to specified type, or default_value if not found
    """
    try:
        user = await session.get(ChatUser, user_id)
    except (DBAPIError, PendingRollbackError, ConnectionDoesNotExistError) as e:
        logger.error(f"Database error while getting user {user_id}: {e}")
        # Try to rollback the session to recover from PendingRollbackError
        try:
            await session.rollback()
            logger.info(f"Session rollback successful for user {user_id}")
            # Retry once after rollback
            user = await session.get(ChatUser, user_id)
        except Exception as retry_error:
            logger.error(f"Failed to recover from database error for user {user_id}: {retry_error}")
            return default_value
    if not user or not user.settings:
        return default_value

    # Convert enum to string if needed
    key = str(setting_key)
    value = user.settings.get(key)
    if value is None:
        return default_value

    if cast_to:
        try:
            if cast_to == UUID:
                return UUID(value)
            return cast_to(value)
        except (ValueError, TypeError):
            return default_value

    return value


async def get_current_char_id(session: AsyncSession, user_id: UUID) -> Optional[int]:
    """Get current character ID for user"""
    return await get_user_chat_setting(
        session, user_id, UserSettingsKeys.CURRENT_CHAR_ID, cast_to=int
    )


async def get_current_config_id(session: AsyncSession, user_id: UUID) -> Optional[UUID]:
    """Get current config ID for user"""
    result = await get_user_chat_setting(
        session, user_id, UserSettingsKeys.CONFIG_ID, cast_to=UUID
    )
    logger.info(f"[CONFIG_DEBUG] get_current_config_id for user {user_id}: {result} (type: {type(result)})")
    return result


async def get_user_language(session: AsyncSession, user_id: UUID) -> Optional[str]:
    """Get saved user language code (e.g., 'en', 'ru')"""
    return await get_user_chat_setting(
        session, user_id, UserSettingsKeys.LANGUAGE, cast_to=str
    )


async def is_language_overridden_by_user(session: AsyncSession, user_id: UUID) -> bool:
    """Return True if user set explicit language override flag"""
    value = await get_user_chat_setting(
        session,
        user_id,
        UserSettingsKeys.LANGUAGE_OVERRIDE,
        default_value="false",
        cast_to=str,
    )
    return str(value).lower() in {"1", "true", "yes"}


async def remove_user_chat_settings(
    session: AsyncSession, user_id: UUID, keys_to_remove: list[Union[str, UserSettingsKeys]]
) -> None:
    """
    Remove specified keys from user's hstore settings.
    Args:
        session: SQLModel session
        user_id: User's UUID
        keys_to_remove: List of keys to remove from hstore settings
    """
    if not keys_to_remove:
        return

    # Convert enum members to string values
    str_keys_to_remove = [str(key) for key in keys_to_remove]
    
    # Use more robust approach: rebuild hstore without the keys to remove
    try:
        # First get current settings
        get_settings_query = text(
            """
        SELECT settings FROM public.users WHERE id = :id
        """
        )
        result = await session.execute(get_settings_query, {"id": user_id})
        current_settings = result.scalar()
        
        if current_settings:
            # Parse hstore string if needed
            if isinstance(current_settings, str):
                # Parse hstore string format: "key1"=>"value1", "key2"=>"value2"
                updated_settings = _parse_hstore_string(current_settings)
            elif isinstance(current_settings, dict):
                updated_settings = current_settings.copy()
            else:
                # If it's not a dict or string, try to convert it safely
                try:
                    updated_settings = dict(current_settings)
                except (ValueError, TypeError):
                    # If conversion fails, create empty dict and log warning
                    logger.warning(f"Could not convert current_settings to dict for user {user_id}: {type(current_settings)} {current_settings}")
                    updated_settings = {}
            
            for key_to_remove in str_keys_to_remove:
                updated_settings.pop(key_to_remove, None)
            
            # Convert back to hstore format and update
            if updated_settings:
                hstore_settings = _dict_to_hstore_str(updated_settings)
            else:
                # If no settings remain, set to empty hstore instead of NULL (to avoid NOT NULL constraint)
                hstore_settings = ""
            
            update_query = text(
                """
            UPDATE public.users
            SET settings = :settings
            WHERE id = :id
            """
            )
            await session.execute(update_query, {"settings": hstore_settings, "id": user_id})
                
    except (DBAPIError, PendingRollbackError) as e:
        logger.error(f"Database error while removing settings for user {user_id}: {e}")
        try:
            await session.rollback()
            logger.info(f"Session rollback successful for user settings removal {user_id}")
            # Retry once after rollback - same logic
            get_settings_query = text(
                """
            SELECT settings FROM public.users WHERE id = :id
            """
            )
            result = await session.execute(get_settings_query, {"id": user_id})
            current_settings = result.scalar()
            
            if current_settings:
                # Same logic as above for retry
                if isinstance(current_settings, str):
                    updated_settings = _parse_hstore_string(current_settings)
                elif isinstance(current_settings, dict):
                    updated_settings = current_settings.copy()
                else:
                    try:
                        updated_settings = dict(current_settings)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert current_settings to dict for user {user_id} (retry): {type(current_settings)} {current_settings}")
                        updated_settings = {}
                
                for key_to_remove in str_keys_to_remove:
                    updated_settings.pop(key_to_remove, None)
                
                if updated_settings:
                    hstore_settings = _dict_to_hstore_str(updated_settings)
                else:
                    # If no settings remain, set to empty hstore instead of NULL
                    hstore_settings = ""
                
                update_query = text(
                    """
                UPDATE public.users
                SET settings = :settings
                WHERE id = :id
                """
                )
                await session.execute(update_query, {"settings": hstore_settings, "id": user_id})
        except Exception as retry_error:
            logger.error(f"Failed to recover from database error while removing settings for user {user_id}: {retry_error}")
            # Re-raise to let caller handle it
            raise


def _dict_to_hstore_str(d: dict) -> str:
    """Local helper to convert dictionary to hstore string, supports Enum keys."""
    if not d:
        return ""
    items = []
    for k, v in d.items():
        if v is not None:  # Только добавляем не-None значения
            items.append(f'"{str(k)}"=>"{v}"')
    return ", ".join(items)


def _parse_hstore_string(hstore_str: str) -> dict:
    """Parse hstore string format: "key1"=>"value1", "key2"=>"value2" into Python dict."""
    if not hstore_str.strip():
        return {}
    
    # Pattern to match "key"=>"value" pairs, handling escaped quotes
    pattern = r'"([^"]*?)"\s*=>\s*"([^"]*?)"'
    matches = re.findall(pattern, hstore_str)
    
    result = {}
    for key, value in matches:
        result[key] = value
    
    return result


async def set_user_language(
    session: AsyncSession,
    user_id: UUID,
    language_code: Optional[str],
) -> None:
    """Set user's language preference WITHOUT override.
    This is for automatically updating the user's last known language.
    This writes into users.settings hstore 'language' key.
    """
    if not language_code:
        return

    settings_to_save = {UserSettingsKeys.LANGUAGE: language_code}
    hstore_settings = _dict_to_hstore_str(settings_to_save)
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
    try:
        await session.execute(save_settings_query, {"settings": hstore_settings, "id": user_id})
    except (DBAPIError, PendingRollbackError) as e:
        logger.error(f"Database error while setting language for user {user_id}: {e}")
        try:
            await session.rollback()
            logger.info(f"Session rollback successful for language setting {user_id}")
            # Retry once after rollback
            await session.execute(save_settings_query, {"settings": hstore_settings, "id": user_id})
        except Exception as retry_error:
            logger.error(f"Failed to recover from database error while setting language for user {user_id}: {retry_error}")
            # Re-raise to let caller handle it
            raise


async def set_user_language_override(
    session: AsyncSession,
    user_id: UUID,
    language_code: Optional[str],
) -> None:
    """Set user's language and override flag from a manual user command.
    If language_code is provided (and not 'auto'), it sets LANGUAGE and LANGUAGE_OVERRIDE.
    If language_code is None or "auto", it removes the LANGUAGE_OVERRIDE flag.
    This writes into users.settings hstore keys.
    """
    if language_code and language_code != "auto":
        settings_to_save = {
            UserSettingsKeys.LANGUAGE: language_code,
            UserSettingsKeys.LANGUAGE_OVERRIDE: "true",
        }
        hstore_settings = _dict_to_hstore_str(settings_to_save)
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
        try:
            await session.execute(save_settings_query, {"settings": hstore_settings, "id": user_id})
        except (DBAPIError, PendingRollbackError) as e:
            logger.error(f"Database error while setting language override for user {user_id}: {e}")
            try:
                await session.rollback()
                logger.info(f"Session rollback successful for language override setting {user_id}")
                # Retry once after rollback
                await session.execute(save_settings_query, {"settings": hstore_settings, "id": user_id})
            except Exception as retry_error:
                logger.error(f"Failed to recover from database error while setting language override for user {user_id}: {retry_error}")
                # Re-raise to let caller handle it
                raise
    else:
        # "auto" or None means we remove the override
        await remove_user_chat_settings(
            session, user_id, [UserSettingsKeys.LANGUAGE_OVERRIDE]
        )
