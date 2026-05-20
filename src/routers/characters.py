import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session

from src.dependencies import get_current_user, get_session
from src.lib.characters import get_characters
from src.lib.config import config
from src.lib.images import get_images_data
from src.lib.verifier import TokenData
from src.schemas.character import Character
from src.telegram.dependecies import get_async_session
from src.translator.dto import TranslationRequest
from src.translator.in_memory import (
    InMemoryCache,
    InMemoryEmbeddingService,
    InMemoryGlossary,
)
from src.translator.llm_client_uri import UriLLMClient
from src.translator.models import Translation
from src.translator.sql_tm import SQLTranslationMemory
from src.translator.translator import Translator

router = APIRouter(tags=["Characters"])

# Поля персонажей, которые требуют перевода
TRANSLATABLE_CHARACTER_FIELDS = ["telegram_description"]


@router.get("/characters")
async def get_characters_info(
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: TokenData = Depends(get_current_user),
) -> list[Character]:
    user_id = UUID(current_user.user_id)
    characters = get_characters(session, limit=limit, offset=offset)
    for character in characters:
        character["profile_images_ids"] = get_images_data(
            character["profile_images_ids"], user_id, session
        )
    return characters


@router.get("/characters/translated")
async def get_translated_characters(
    lang: str = "en",
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """
    Get characters with translated fields based on the specified language.
    
    Args:
        lang: Target language code (default: "en")
        session: Async database session
        
    Returns:
        List of character dictionaries with translated fields
    """
    # Optimization: If English is requested, return directly without translation
    if lang == "en":
        query = text(
            """
            SELECT * FROM public.characters 
            WHERE status = 'published'
            ORDER BY sort ASC NULLS LAST
            """
        )
        result = await session.execute(query)
        return [dict(row._mapping) for row in result]
    
    # 1. Get characters from view
    query = text(
        """
        SELECT * FROM public.characters 
        WHERE status = 'published'
        ORDER BY sort ASC NULLS LAST
        """
    )
    result = await session.execute(query)
    characters = [dict(row._mapping) for row in result]
    
    if not characters:
        return []
    
    # 2. Build translation keys with hashes for each translatable field
    translation_keys = []  # List of (char_id, field_name, key, source_text)
    
    for char in characters:
        for field_name in TRANSLATABLE_CHARACTER_FIELDS:
            source_text = char.get(field_name)
            if source_text:
                text_hash = hashlib.sha256(source_text.encode()).hexdigest()
                key = f"character_{field_name}:char_id:{char['id']}:hash:{text_hash}"
                translation_keys.append((char["id"], field_name, key, source_text))
    
    if not translation_keys:
        return characters
    
    # 3. Batch query for translations
    keys_list = [tk[2] for tk in translation_keys]
    translations_query = text(
        """
        SELECT key, translated_text 
        FROM translator.translations 
        WHERE key = ANY(:keys) AND language = :lang
        """
    )
    translations_result = await session.execute(
        translations_query, {"keys": keys_list, "lang": lang}
    )
    
    # 4. Build existing translations map
    existing_translations = {
        row.key: row.translated_text for row in translations_result
    }
    
    # 5. Determine missing translations
    missing = [tk for tk in translation_keys if tk[2] not in existing_translations]
    
    # 6. Translate missing entries
    if missing:
        # Create Translator instance
        tm = SQLTranslationMemory(session)
        translator = Translator(
            tm=tm,
            glossary=InMemoryGlossary(),
            cache=InMemoryCache(),
            embedder=InMemoryEmbeddingService(),
            llm=UriLLMClient(config.translator_llm_url),
        )
        
        for char_id, field_name, key, source_text in missing:
            try:
                req = TranslationRequest(
                    source_text=source_text,
                    source_lang="en",
                    target_lang=lang,
                    context="Female character's profile description displayed in Telegram Web App. Natural, appealing style for male users.",
                    context_key=key,
                )
                result = await translator.translate(req)
                existing_translations[key] = result.translated_text
            except Exception as e:
                # If translation fails, use original text
                print(f"Translation failed for character {char_id}, field {field_name}: {e}")
                existing_translations[key] = source_text
    
    # 7. Build result with translated fields
    for char in characters:
        for field_name in TRANSLATABLE_CHARACTER_FIELDS:
            if char.get(field_name):
                text_hash = hashlib.sha256(char[field_name].encode()).hexdigest()
                key = f"character_{field_name}:char_id:{char['id']}:hash:{text_hash}"
                char[field_name] = existing_translations.get(key, char[field_name])
    
    return characters
