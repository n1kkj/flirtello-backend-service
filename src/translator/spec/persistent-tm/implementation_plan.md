# План внедрения Сервиса Переводов

Этот документ описывает пошаговый план по созданию и интеграции нового сервиса переводов с персистентной Памятью переводов (Translation Memory) во все необходимые компоненты проекта.

---

### Фаза 1: Создание фундамента и ядра сервиса

*   [x] **1.1. Создать структуру модуля:**
    *   Создать директорию `src/translator/migrations/`.
    *   Создать файл `src/translator/models.py`.
    *   Создать файл `src/translator/sql_tm.py` для реализации `BaseTranslationMemory`.

*   [x] **1.2. Определить модель данных:**
    *   В `models.py` определить `SQLModel` `Translation` со всеми необходимыми полями (`key`, `language`, `source_text`, `translated_text`, `is_verified_by_human`, `created_at`, `updated_at`) и привязкой к схеме `translator`.

*   [x] **1.3. Создать миграцию БД:**
    *   В `migrations/` создать SQL-скрипт для создания схемы `translator` и таблицы `translator.translations` со всеми индексами и триггерами.

*   [x] **1.4. Реализовать `SQLTranslationMemory`:**
    *   В `sql_tm.py` написать класс `SQLTranslationMemory`, который реализует интерфейс `BaseTranslationMemory`, но для взаимодействия с нашей новой таблицей.

*   [x] **1.5. Модифицировать `Translator.py`:**
    *   Добавить в класс `Translator` логику L1-кэширования (in-memory `TTLCache`).
    *   Изменить метод `translate`, чтобы он оркестрировал весь флоу: L1-кэш -> L2-кэш (наша новая `SQLTranslationMemory`) -> LLM.
    *   Доработать интерфейс `BaseTranslationMemory`, чтобы он поддерживал поиск по ключу, а не только по вектору.

*   [x] **1.6. Настроить Dependency Injection:**
    *   Создать/обновить файл `dependencies.py` в модуле `translator`, чтобы он корректно предоставлял `SQLTranslationMemory` и `Translator` для всего приложения.

*   [x] **1.7. Написать и запустить тесты:**
    *   Создать файл `src/translator/test_persistent_tm.py`.
    *   Написать тесты для `SQLTranslationMemory` и новой логики `Translator`.
    *   Успешно запустить тесты.

---

### Фаза 2: Интеграция в Telegram-бот (`flirtello-backend-service`) (Конкретизированный план)

*   [ ] **2.1. Клавиатуры (`src/telegram/keyboards.py`):**
    *   **МОДИФИЦИРОВАТЬ:**
        *   `create_character_selection_keyboard`: Перевести `char_name` и `char_traits` через `Translator`.
        *   `create_all_configs_selection_keyboard`: Перевести `config_public_name` и `config_short_name` через `Translator`.
        *   `create_config_selection_keyboard`: Перевести `char_name` и `char_traits` через `Translator`.
    *   **НЕ ТРОГАТЬ:**
        *   `create_get_tokens_keyboard`: Текст кнопки `Get Tokens 💝` — статичный, остается в `gettext`.
        *   `create_get_image_keyboard`: Текст кнопки `Get Image ❤️‍🔥` — статичный, остается в `gettext`.

*   [ ] **2.2. Обработчики Команд (`src/telegram/handlers/commands.py`):**
    *   **МОДИФИЦИРОВАТЬ:**
        *   `process_start_command`: Необходимо получить `Translator` через DI и передать его в `create_character_selection_keyboard` и `create_all_configs_selection_keyboard`.
    *   **НЕ ТРОГАТЬ:**
        *   `process_gift_command`: Все ответы (`"Congratulations!"`, `"code doesn't exist"`) — это статические UI-строки. Они остаются в `gettext`.
        *   `process_lang_command`: Все ответы (`"Usage:..."`, `"Language successfully set"`) — это статические UI-строки. Они остаются в `gettext`.

*   [ ] **2.3. Обработчики Коллбэков (`src/telegram/handlers/callbacks.py`):**
    *   **МОДИФИЦИРОВАТЬ:**
        *   `handle_callback_query`: После вызова `start_new_chat_tg` и получения **английского** первого сообщения от `flirtello-chats`, необходимо использовать `Translator` для перевода текста этого сообщения перед отправкой пользователю.
    *   **НЕ ТРОГАТЬ:**
        *   Часть, отвечающая за `get_free_tokens`. Все ответы — статические UI-строки.
        *   Все сообщения об ошибках (`"Error: invalid character data"`, `"User error"`) — статические, остаются в `gettext`.

*   [ ] **2.4. Обработчики Сообщений (`src/telegram/handlers/messages.py`):**
    *   **МОДИФИЦИРОВАТЬ:**
        *   `process_regular_message`: После получения ответа от `write_to_current_chat` (т.е. от `flirtello-chats`), необходимо получить `Translator` через DI. Текстовое поле каждого сообщения (`message_dto.message`) из ответа `flirtello-chats` должно быть переведено с помощью `translator.translate()` перед отправкой пользователю.
    *   **НЕ ТРОГАТЬ:**
        *   Все сообщения об ошибках (`"Error: could not find image data"`) — статические, остаются в `gettext`.
        *   Сообщение `TemplateMessages.NO_TOKENS.value` — это специальная строка-шаблон, она также переводится через `gettext`.

---

### Фаза 3: Интеграция в API (`flirtello-backend-service`)

*   [ ] **3.1. Роутеры (`src/routers/`):**
    *   Проанализировать все роутеры (`characters.py`, `chat.py` и др.) на предмет возврата текстовых данных, предназначенных для отображения пользователю.
    *   Для всех таких эндпоинтов добавить зависимость от `Translator` и переводить соответствующие поля в DTO перед отправкой ответа.

---

### Фаза 4: Развертывание и финализация

*   [ ] **4.1. Применить миграции:**
    *   На всех окружениях (staging, production) необходимо будет применить новую SQL-миграцию вручную.

*   [ ] **4.2. Обновить конфигурацию:**
    *   **Шаг 4.2.1:** Модифицировать файл `src/telegram/dependecies.py`, добавив асинхронный движок и провайдер сессий:
        ```python
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlmodel import Session, create_engine
        
        from src.lib.config import config
        
        engine = create_engine(config.database_url)
        # ДОБАВИТЬ ЭТИ ДВЕ СТРОКИ
        async_engine = create_async_engine(config.database_url_async) # Убедиться, что async URL есть в конфиге
        
        def get_session():
            session = Session(engine)
            try:
                yield session
            finally:
                session.close()

        # ДОБАВИТЬ ЭТУ ФУНКЦИЮ
        async def get_async_session() -> AsyncSession:
            async with AsyncSession(async_engine) as session:
                yield session
        ```
    *   **Шаг 4.2.2:** В файле `src/translator/dependencies.py` (который мы создадим на Фазе 1), написать функцию для DI, которая будет использовать новую асинхронную сессию.
        ```python
        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        
        from src.telegram.dependecies import get_async_session # Точный импорт
        from src.translator.sql_tm import SQLTranslationMemory
        from src.translator.interfaces import BaseTranslationMemory
        
        def get_translation_memory(
            session: AsyncSession = Depends(get_async_session),
        ) -> BaseTranslationMemory:
            return SQLTranslationMemory(session)
        ```
    *   **Шаг 4.2.3:** При развертывании убедиться, что в переменных окружения (`.env` или аналогах) для `staging` и `production` добавлена переменная `DATABASE_URL_ASYNC` с корректным DSN для асинхронного драйвера (например, `postgresql+asyncpg://...`).
