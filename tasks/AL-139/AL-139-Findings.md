# AL-139: Технические находки при исправлении ошибок пула соединений БД

## SQLAlchemy: Пул соединений

### 1. Дублирование сессий в async контексте

**Проблема:**

- В async коде легко случайно создать несколько сессий для одного запроса
- Сессия, открытая через `get_async_session()`, может быть не передана в дочерние функции
- Функции создают новые сессии через `async with AsyncSession(async_engine)`, дублируя соединения

**Пример проблемы:**

```python
# dispatcher.py
async for session in get_async_session():
    # Сессия открыта
    await process_regular_message(..., session, ...)

# handlers/messages.py
async def process_regular_message(..., session, ...):
    await write_to_current_chat(...)  # Сессия не передана!

# chat_logic.py
async def write_to_current_chat(...):
    async with AsyncSession(async_engine) as session:  # ❌ НОВАЯ СЕССИЯ!
        # Работа с БД
```

**Решение:**

- Всегда передавать сессию как параметр в дочерние функции
- Не создавать новые сессии, если сессия уже передана
- Использовать dependency injection для сессий

**Правильный паттерн:**

```python
# dispatcher.py
async for session in get_async_session():
    await process_regular_message(..., session, ...)

# handlers/messages.py
async def process_regular_message(..., session: AsyncSession, ...):
    await write_to_current_chat(..., session, ...)  # ✅ Передаем сессию

# chat_logic.py
async def write_to_current_chat(..., session: AsyncSession, ...):
    # ✅ Используем переданную сессию
    result = await session.execute(...)
```

### 2. Настройка пула соединений для asyncpg

**Проблема:**

- Дефолтные значения пула слишком маленькие для production
- `pool_size=5`, `max_overflow=10` = всего 15 соединений
- При высокой нагрузке все соединения быстро заканчиваются

**Рекомендуемые настройки:**

```python
async_engine = create_async_engine(
    database_url,
    pool_pre_ping=True,  # Проверка соединений перед использованием
    pool_size=20,  # Базовый размер пула (не слишком большой)
    max_overflow=30,  # Дополнительные соединения при нагрузке
    pool_recycle=3600,  # Переиспользование соединений каждый час
    pool_timeout=30,  # Таймаут ожидания соединения
)
```

**Расчет размера пула:**

- Базовый размер: `pool_size` = количество concurrent запросов в среднем
- Overflow: `max_overflow` = пиковая нагрузка - базовая
- Итого: `pool_size + max_overflow` должно покрывать пиковую нагрузку

**Важно:**

- Не делать пул слишком большим - каждое соединение занимает ресурсы БД
- Мониторить использование пула через логи и метрики
- Увеличивать постепенно, отслеживая эффект

### 3. Обработка ошибок пула в Sentry

**Проблема:**

- Ошибки `TimeoutError` от пула не отправлялись в Sentry
- Невозможно было отслеживать проблему в реальном времени
- Нет контекста для диагностики

**Решение:**

```python
from sqlalchemy.exc import TimeoutError as SQLTimeoutError

try:
    # Работа с БД
    ...
except SQLTimeoutError as e:
    await session.rollback()
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("error_type", "database_pool_timeout")
        scope.set_context("pool_info", {
            "error": str(e),
            "user_id": str(context.user_id) if hasattr(context, 'user_id') else None,
            "request_id": context.request_id if hasattr(context, 'request_id') else None,
        })
        scope.level = "error"
        sentry_sdk.capture_exception(e)
    logger.error(f"⚠️ DATABASE POOL TIMEOUT: {e}")
```

**Почему это важно:**

- Позволяет отслеживать частоту ошибок пула
- Контекст помогает понять, при каких условиях возникает проблема
- Тег `database_pool_timeout` позволяет фильтровать ошибки в Sentry

## Telegram Bot: Архитектура сессий

### 1. Паттерн использования сессий в dispatcher

**Обнаружено:**

- `dispatcher.py` открывает сессию через `get_async_session()` на все время обработки запроса
- Сессия должна передаваться во все дочерние функции
- Нельзя создавать новые сессии в дочерних функциях

**Правильный паттерн:**

```python
# dispatcher.py
async for session in get_async_session():
    try:
        # Вся обработка запроса использует одну сессию
        await process_regular_message(..., session, ...)
        await session.commit()
    except Exception as e:
        await session.rollback()
        # Обработка ошибок
```

**Антипаттерн:**

```python
# ❌ НЕПРАВИЛЬНО
async for session in get_async_session():
    await some_function(...)  # Сессия не передана

async def some_function(...):
    async with AsyncSession(async_engine) as new_session:  # ❌ Дублирование!
        # Работа с БД
```

### 2. Фоновые задачи и сессии

**Проблема:**

- Фоновые задачи (background tasks) не могут использовать сессию из основного запроса
- Нужно создавать новую сессию для фоновых задач

**Решение:**

```python
# Для фоновых задач создаем новую сессию
async def background_task(...):
    async for session in get_async_session():
        # Работа с БД в фоновой задаче
        ...
```

**Важно:**

- Фоновые задачи должны создавать свои сессии
- Не передавать сессию из основного запроса в фоновую задачу
- Фоновая задача должна быть независимой от основного запроса

## Выводы

1. **Всегда передавайте сессию как параметр** - не создавайте новые сессии в дочерних функциях
2. **Настраивайте пул под нагрузку** - `pool_size + max_overflow` должно покрывать пиковую нагрузку
3. **Мониторьте ошибки пула** - отправляйте их в Sentry с контекстом для диагностики
4. **Используйте `pool_recycle`** - переиспользование соединений предотвращает проблемы с "мертвыми" соединениями
5. **Проверяйте соединения** - `pool_pre_ping=True` проверяет соединения перед использованием
6. **Фоновые задачи = новые сессии** - не передавайте сессию из основного запроса в фоновую задачу
