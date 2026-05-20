
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from src.translator.dto import TranslationRequest
from src.translator.in_memory import (
    DummyLLMClient,
    InMemoryCache,
    InMemoryEmbeddingService,
    InMemoryGlossary,
)
from src.translator.sql_tm import SQLTranslationMemory
from src.translator.translator import Translator

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.mark.asyncio
async def test_sql_translation_memory_add_and_get(db_session: AsyncSession):
    tm = SQLTranslationMemory(session=db_session)
    key = "test_key"
    lang = "ru"
    source = "Hello"
    translated = "Привет"

    await tm.add(key=key, language=lang, source_text=source, translated_text=translated)

    entry = await tm.get_by_key(key=key, language=lang)
    assert entry is not None
    assert entry.key == key
    assert entry.language == lang
    assert entry.source_text == source
    assert entry.translated_text == translated
    assert not entry.is_verified_by_human


@pytest.mark.asyncio
async def test_translator_l1_cache(db_session: AsyncSession):
    tm = SQLTranslationMemory(session=db_session)
    translator = Translator(
        tm=tm,
        glossary=InMemoryGlossary(),
        cache=InMemoryCache(),
        embedder=InMemoryEmbeddingService(),
        llm=DummyLLMClient(),
    )
    request = TranslationRequest(source_text="Hello", target_lang="ru", context_key="greeting")
    
    # First call, should go to LLM and populate caches
    result1 = await translator.translate(request)
    assert result1.translated_text == "Hello [ru]"

    # Manually update the DB to simulate a better translation
    entry = await tm.get_by_key(key="greeting", language="ru")
    entry.translated_text = "Правильный Привет"
    db_session.add(entry)
    await db_session.commit()

    # Second call, should hit L1 cache and return the old result
    result2 = await translator.translate(request)
    assert result2.translated_text == "Hello [ru]"


@pytest.mark.asyncio
async def test_translator_l2_cache(db_session: AsyncSession):
    tm = SQLTranslationMemory(session=db_session)
    translator = Translator(
        tm=tm,
        glossary=InMemoryGlossary(),
        cache=InMemoryCache(),
        embedder=InMemoryEmbeddingService(),
        llm=DummyLLMClient(),
    )
    request = TranslationRequest(source_text="Hello", target_lang="ru", context_key="greeting")
    
    # Pre-populate L2 cache (DB)
    await tm.add(key="greeting", language="ru", source_text="Hello", translated_text="Привет из БД")

    # First call, should get from L2 and populate L1
    result = await translator.translate(request)
    assert result.translated_text == "Привет из БД"

    # Check that L1 is populated
    assert translator._local_cache.get("greeting") == "Привет из БД"


@pytest.mark.asyncio
async def test_translator_verified_flag(db_session: AsyncSession):
    tm = SQLTranslationMemory(session=db_session)
    translator = Translator(
        tm=tm,
        glossary=InMemoryGlossary(),
        cache=InMemoryCache(),
        embedder=InMemoryEmbeddingService(),
        llm=DummyLLMClient(prefix="LLM: "),
    )
    request = TranslationRequest(source_text="Hello", target_lang="ru", context_key="greeting")

    # Pre-populate L2 with a verified entry
    entry = await tm.add(key="greeting", language="ru", source_text="Hello", translated_text="Проверенный Привет")
    entry.is_verified_by_human = True
    db_session.add(entry)
    await db_session.commit()

    # This call should return the verified translation without calling LLM
    result = await translator.translate(request)
    assert result.translated_text == "Проверенный Привет"
    assert "LLM" not in result.translated_text
