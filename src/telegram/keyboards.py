from typing import Optional  # Для Python 3.8 Tuple, для 3.9+ tuple
from urllib.parse import urljoin

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import text

from src.translator import TranslationRequest

from .api import (
    send_tg_message,  # send_tg_message нужен для send_response_with_keyboard
)

# Импортируем необходимые объекты из других модулей, если они нужны
# Например, WEB_APP_FULL_LIST_URL из config.py, если он используется напрямую в функциях клавиатур
# и send_tg_message из api module для send_response_with_keyboard
from .config import (  # WEB_APP_FULL_LIST_URL нужен для клавиатур
    WEB_APP_FULL_LIST_URL,
    logger,
)
from .context import RequestContext
from .lib.i18n import get_gettext_for_language


# Функции, перенесенные из bot.py
def create_get_tokens_keyboard(language_code: Optional[str] = "en"):
    """Create an inline keyboard markup with a 'Get Tokens' button that opens web app"""
    _ = get_gettext_for_language(language_code or "en")
    base_url = WEB_APP_FULL_LIST_URL or ""
    web_app_url = urljoin(base_url, "tg-payments")
    logger.info(f"Web app url: {web_app_url}")
    return {
        "inline_keyboard": [
            [
                {
                    "text": _("Get Tokens 💝"),
                    "web_app": {"url": web_app_url},
                }
            ]
        ]
    }


def create_context_keyboard(language_code: Optional[str] = "en"):
    """Create a regular keyboard markup with context action buttons: 'Get Image' and 'Continue'"""
    _ = get_gettext_for_language(language_code or "en")
    return {
        "keyboard": [[
            {"text": _("Get Image ❤️‍🔥")},
            {"text": _("Continue 💬")}
        ]],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "persistent": True,
    }


async def create_character_selection_keyboard(
    session: AsyncSession,
    include_descriptions_in_message: bool = False,
    web_app_url: Optional[str] = None,
    language_code: Optional[str] = None,
    context: Optional[RequestContext] = None,
) -> tuple[str, dict]:  # Python 3.9+ можно использовать tuple
    query_str = "SELECT id, name, traits FROM public.characters WHERE status = 'published' ORDER BY sort ASC NULLS LAST LIMIT 8;"
    result = await session.execute(text(query_str))

    _ = get_gettext_for_language((language_code or "en"))
    # character_details_text = "Выберите вашу спутницу:\n\n"
    character_details_text = f"{_('Choose your companion')}:\n\n"

    keyboard_rows = []
    current_row = []

    raw_characters_data = result.mappings().all()

    if include_descriptions_in_message:
        for char_data in raw_characters_data:
            char_name = char_data["name"]
            # Переводим только если целевой язык НЕ английский (по умолчанию имена на английском)
            if language_code != "en":
                char_name_result = await context.translator.translate(
                    TranslationRequest(
                        source_text=char_data["name"],
                        source_lang="en",  # Имена персонажей обычно на английском
                        target_lang=language_code,
                        context_key=f"character_name:{char_data['id']}",
                    )
                )
                char_name = char_name_result.translated_text
            char_traits_list = char_data["traits"]
            description_str = ""
            if char_traits_list:
                valid_traits = []
                for trait in char_traits_list:
                    if trait is not None:
                        trait_text = trait
                        # Переводим только если целевой язык НЕ английский
                        if language_code != "en":
                            trait_result = await context.translator.translate(
                                TranslationRequest(
                                    source_text=trait,
                                    source_lang="en",  # Трейты персонажей обычно на английском
                                    target_lang=language_code,
                                    context_key=f"character_trait:f:{trait}",
                                )
                            )
                            trait_text = trait_result.translated_text
                        valid_traits.append(trait_text)
                description_str = ", ".join(valid_traits)

            character_details_text += f"{char_name.strip()} – {description_str.strip()}\n"
        character_details_text += "\n"

    for char_data in raw_characters_data:
        char_id = char_data["id"]
        button_text = char_data["name"]
        # Переводим только если целевой язык НЕ английский
        if language_code != "en":
            button_text_result = await context.translator.translate(
                TranslationRequest(
                    source_text=char_data["name"],
                    source_lang="en",  # Имена персонажей обычно на английском
                    target_lang=language_code,
                    context_key=f"character_name:{char_data['id']}",
                )
            )
            button_text = button_text_result.translated_text

        current_row.append({"text": button_text, "callback_data": f"/start {char_id}"})
        if len(current_row) == 2:
            keyboard_rows.append(current_row)
            current_row = []

    if current_row:
        keyboard_rows.append(current_row)

    if web_app_url:
        lang_param = f"?lang={language_code}" if language_code else ""
        final_web_app_url = f"{web_app_url}{lang_param}"
        keyboard_rows.append(
            [{"text": _("✨ Open all characters"), "web_app": {"url": final_web_app_url}}]
        )

    reply_markup = {"inline_keyboard": keyboard_rows}

    return character_details_text, reply_markup


async def create_all_configs_selection_keyboard(
    session: AsyncSession,
    web_app_url: Optional[str] = None,
    language_code: Optional[str] = None,
    context: Optional[RequestContext] = None,
) -> tuple[str, dict]:  # Python 3.9+ можно использовать tuple
    """
    Создает клавиатуру выбора конфигурации из всех доступных персонажей и их конфигов.
    Формирует reply_markup как словарь, аналогично create_character_selection_keyboard.
    """
    query_str = """
        SELECT 
            ch.id AS character_id,
            ch.name AS character_name,
            cfg.id AS config_id,
            cfg.public_name AS config_public_name,
            cfg.short_name AS config_short_name
        FROM 
            content.content_characters ch
        JOIN 
            content.character_configs cfg ON ch.id = cfg.character_id
        WHERE 
            ch.status = 'published' AND cfg.status = 'published'
        ORDER BY 
            ch.sort ASC NULLS LAST, ch.name ASC, cfg.public_name ASC;
    """

    result = await session.execute(text(query_str))
    all_configs_data = result.mappings().all()
    _ = get_gettext_for_language((language_code or "en"))

    if not all_configs_data:
        message_text = _("No configurations available yet.")
        keyboard_rows = []
        if web_app_url:
            keyboard_rows.append(
                [{"text": _("✨ Open web app"), "web_app": {"url": web_app_url}}]
            )

        reply_markup = {"inline_keyboard": keyboard_rows} if keyboard_rows else {}
        return message_text, reply_markup

    message_text = _("Choose your story:\n\n")
    for config_data in all_configs_data:
        config_public_name = config_data.get("config_public_name", "Unknown config")
        # Переводим только если целевой язык НЕ английский
        if language_code != "en":
            config_public_name_result = await context.translator.translate(
                TranslationRequest(
                    source_text=config_data.get("config_public_name", "Unknown config"),
                    source_lang="en",  # Названия конфигов обычно на английском
                    target_lang=language_code,
                    context_key=f"config_public_name:{config_data['config_id']}",
                )
            )
            config_public_name = config_public_name_result.translated_text
        message_text += f"{config_public_name}\n"

    keyboard_rows = []
    current_row = []

    for config_data in all_configs_data:
        short_name = config_data.get("config_short_name", "Config")
        # Переводим только если целевой язык НЕ английский
        if language_code != "en":
            short_name_result = await context.translator.translate(
                TranslationRequest(
                    source_text=config_data.get("config_short_name", "Config"),
                    source_lang="en",  # Короткие названия конфигов обычно на английском
                    target_lang=language_code,
                    context_key=f"config_short_name:{config_data['config_id']}",
                )
            )
            short_name = short_name_result.translated_text
        character_id = config_data.get("character_id")
        config_id = config_data.get("config_id")

        if not character_id or not config_id:
            logger.warning(
                f"Пропущен конфиг из-за отсутствия character_id или config_id: {config_data}"
            )
            continue

        callback_data = f"/start {character_id} {config_id}"
        current_row.append({"text": short_name, "callback_data": callback_data})

        if len(current_row) == 2:
            keyboard_rows.append(current_row)
            current_row = []

    if current_row:
        keyboard_rows.append(current_row)

    if web_app_url:
        lang_param = f"?lang={language_code}" if language_code else ""
        final_web_app_url = f"{web_app_url}{lang_param}"
        keyboard_rows.append([{"text": _("✨ Open all characters"), "web_app": {"url": final_web_app_url}}])

    reply_markup = {"inline_keyboard": keyboard_rows} if keyboard_rows else {}
    return message_text, reply_markup


async def create_config_selection_keyboard(
    session: AsyncSession,
    character_id: int,
    web_app_url: Optional[str] = None,
    language_code: Optional[str] = None,
    context: Optional[RequestContext] = None,
) -> tuple[str, dict]:  # Python 3.9+ можно использовать tuple
    query_str = "SELECT id, name, traits FROM public.characters WHERE status = 'published' ORDER BY sort ASC NULLS LAST LIMIT 8;"  # Этот запрос кажется неверным для "config_selection"
    result = await session.execute(text(query_str))
    _ = get_gettext_for_language((language_code or "en"))

    # character_details_text = "Выберите вашу спутницу:\n\n"
    character_details_text = _("Choose your story:\n\n")
    keyboard_rows = []
    current_row = []

    raw_characters_data = result.mappings().all()

    if character_id in [char_data["id"] for char_data in raw_characters_data]:
        for char_data in raw_characters_data:
            if char_data["id"] == character_id:
                char_name = char_data["name"]
                # Переводим только если целевой язык НЕ английский
                if language_code != "en":
                    char_name_result = await context.translator.translate(
                        TranslationRequest(
                            source_text=char_data["name"],
                            source_lang="en",  # Имена персонажей обычно на английском
                            target_lang=language_code,
                            context_key=f"character_name:{char_data['id']}",
                        )
                    )
                    char_name = char_name_result.translated_text
                char_traits_list = char_data["traits"]
                description_str = ""
                if char_traits_list:
                    valid_traits = []
                    for trait in char_traits_list:
                        if trait is not None:
                            trait_text = trait
                            # Переводим только если целевой язык НЕ английский
                            if language_code != "en":
                                trait_result = await context.translator.translate(
                                    TranslationRequest(
                                        source_text=trait,
                                        source_lang="en",  # Трейты персонажей обычно на английском
                                        target_lang=language_code,
                                        context_key=f"character_trait:{char_data['id']}:{trait}",
                                    )
                                )
                                trait_text = trait_result.translated_text
                            valid_traits.append(trait_text)
                    description_str = ", ".join(valid_traits)

                character_details_text += f"{char_name} – {description_str}\n"
        character_details_text += "\n"

    for char_data in raw_characters_data:
        char_id_btn = char_data[
            "id"
        ]  # Используем новую переменную, чтобы не конфликтовать с аргументом character_id
        button_text = char_data["name"]
        # Переводим только если целевой язык НЕ английский
        if language_code != "en":
            button_text_result = await context.translator.translate(
                TranslationRequest(
                    source_text=char_data["name"],
                    source_lang="en",  # Имена персонажей обычно на английском
                    target_lang=language_code,
                    context_key=f"character_name:{char_data['id']}",
                )
            )
            button_text = button_text_result.translated_text

        # Логика колбека здесь должна быть другой для выбора конфига, а не персонажа
        # callback_data = f"/start {char_id_btn}" # Это для выбора персонажа
        # TODO: Изменить callback_data для выбора конфига, например f"/select_config {char_id_btn} {config_id_here}"
        current_row.append(
            {"text": button_text, "callback_data": f"/start {char_id_btn}"}
        )  # Пока оставляем так
        if len(current_row) == 2:
            keyboard_rows.append(current_row)
            current_row = []

    if current_row:
        keyboard_rows.append(current_row)

    if web_app_url:
        lang_param = f"?lang={language_code}" if language_code else ""
        final_web_app_url = f"{web_app_url}{lang_param}"
        keyboard_rows.append(
            [{"text": _("✨ Open all characters"), "web_app": {"url": final_web_app_url}}]
        )

    reply_markup = {"inline_keyboard": keyboard_rows}

    return character_details_text, reply_markup


async def send_response_with_keyboard(
    chat_id: int, text: str, token: str, language_code: Optional[str] = "en"
):
    keyboard = create_context_keyboard(language_code)
    await send_tg_message(chat_id, text, token, reply_markup=keyboard)
