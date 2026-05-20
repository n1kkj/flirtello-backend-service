# AL-139: Посмотреть ошибки с БД

## Описание задачи

Исправление критических ошибок с пулом соединений к базе данных. Ошибки `TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out` возникали из-за:

1. **Дублирования сессий** - в `write_to_current_chat()` создавалась новая сессия, хотя сессия уже была открыта в dispatcher
2. **Недостаточного размера пула** - пул был слишком маленьким (5+10=15 соединений) для текущей нагрузки
3. **Отсутствия мониторинга** - ошибки пула не отправлялись в Sentry

## Чеклист

- [x] Понял задачу
- [x] Изучил код
- [x] Реализовал решение
  - [x] Увеличил размер пула соединений (20+30=50 вместо 5+10=15)
  - [x] Исправил дублирование сессий в `write_to_current_chat()`
  - [x] Добавил отправку ошибок пула в Sentry
  - [x] Добавил `pool_recycle` для переиспользования соединений
- [ ] Протестировал
- [x] Создал Result.md
- [x] Создал Findings.md
- [x] Организовал артефакты (если были)
- [ ] Обновил руководства (если нужно)

## Заметки

### Проблема

Ошибки `QueuePool limit of size 5 overflow 10 reached` возникали при высокой нагрузке. Проблема была в том, что:

- В `dispatcher.py` открывалась сессия через `get_async_session()`
- Эта сессия передавалась в `process_regular_message()`
- `process_regular_message()` вызывал `write_to_current_chat()`
- `write_to_current_chat()` создавала **еще одну** сессию через `async with AsyncSession(async_engine)`
- Итого: **2 сессии на запрос** вместо 1

### Решение

1. **Исправлено дублирование сессий**: `write_to_current_chat()` теперь принимает сессию как параметр
2. **Увеличен пул соединений**:
   - `pool_size`: 5 → 20
   - `max_overflow`: 10 → 30
   - Итого: до 50 соединений (было 15)
3. **Добавлен мониторинг**: ошибки пула теперь отправляются в Sentry с тегом `database_pool_timeout`
4. **Добавлен `pool_recycle=3600`**: переиспользование соединений каждый час

### Измененные файлы

- `src/telegram/dependecies.py` - увеличен пул соединений
- `src/telegram/config.py` - увеличен пул для синхронного engine
- `src/telegram/dispatcher.py` - добавлена обработка TimeoutError с отправкой в Sentry
- `src/telegram/chat_logic.py` - исправлено дублирование сессий
- `src/telegram/handlers/messages.py` - обновлен вызов `write_to_current_chat()`
- `src/telegram/use_cases/generate_illustration_task.py` - добавлена обработка TimeoutError
