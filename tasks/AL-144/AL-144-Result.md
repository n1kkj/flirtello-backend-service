# AL-144: Исправление непереведенного сообщения об ошибке и улучшение обработки 429 ошибок

## Задача

Исправить непереведенное сообщение об ошибке при запросе картинки и улучшить обработку ошибок 429 (Too Many Requests) от Telegram API.

## Что сделано

### 1. Добавлены переводы для сообщения об ошибке

**Проблема:** Сообщение "Something went wrong while preparing your request. Please try again. ❤️" отсутствовало в файлах локализации.

**Решение:**
- Добавлен перевод в английский файл локализации (`messages.po`)
- Добавлен перевод в русский файл локализации (`messages.po`)
- Русский перевод: "Что-то пошло не так при подготовке твоего запроса. Пожалуйста, попробуй еще раз. ❤️"

### 2. Реализован fallback на текстовое сообщение

**Проблема:** При ошибке отправки placeholder анимации (например, из-за 429) процесс генерации иллюстрации полностью прерывался.

**Решение:**
- Добавлен fallback на текстовое сообщение "Your illustration is being generated... 👨‍🎨"
- Процесс генерации иллюстрации продолжается даже при ошибке отправки анимации
- Ошибка отправляется пользователю только если и текстовое сообщение не удалось отправить

### 3. Улучшена обработка 429 ошибок

**Проблема:** При получении 429 от Telegram API не использовался заголовок `Retry-After`, использовалась фиксированная задержка.

**Решение:**
- Добавлена обработка заголовка `Retry-After` от Telegram API
- Если заголовок отсутствует, используется экспоненциальная задержка (максимум 60 секунд)
- Это снижает вероятность повторных 429 ошибок

## Верификация

✅ Переводы добавлены в оба файла локализации (en и ru)
✅ Fallback на текстовое сообщение работает корректно
✅ Обработка 429 ошибок использует Retry-After заголовок
✅ Процесс генерации иллюстрации продолжается даже при ошибке отправки анимации
✅ Пользователи видят переведенные сообщения на своем языке

## Отладка: Что искать в логах

### Успешный сценарий (placeholder анимация отправлена)

**В логах должно быть:**
```
INFO - Scheduled illustration generation task for user {user_id} and message {message_id}
```

**Если placeholder анимация отправлена успешно, НЕ должно быть:**
- `WARNING - Failed to send placeholder animation/video`
- `ERROR - Failed to send placeholder message`

### Fallback сценарий (анимация не удалась, используется текст)

**В логах должно быть:**
```
WARNING - Failed to send placeholder animation/video to user {user_id} in chat {sender_chat_id}. Trying text fallback...
INFO - Scheduled illustration generation task for user {user_id} and message {message_id}
```

**Причины fallback могут быть:**
- `ERROR - An unexpected error occurred in send_animation_placeholder: Client error '429 Too Many Requests'`
- `ERROR - Failed to send animation placeholder to {chat_id}: {"ok":false,"error_code":403,"description":"Forbidden: bot was blocked by the user"}`

### Ошибка (оба способа не удались)

**В логах будет:**
```
ERROR - Failed to send placeholder message to user {user_id} in chat {sender_chat_id}
```

**После этого пользователю отправляется сообщение об ошибке (переведенное).**

### Поиск в New Relic

**Запрос для поиска ошибок placeholder:**
```sql
SELECT * FROM Log 
WHERE message LIKE '%Failed to send placeholder%' 
   OR message LIKE '%send_animation_placeholder%'
   OR message LIKE '%429 Too Many Requests%'
SINCE 24 HOURS AGO 
LIMIT 50
```

**Запрос для поиска успешных fallback:**
```sql
SELECT * FROM Log 
WHERE message LIKE '%Trying text fallback%'
SINCE 24 HOURS AGO 
LIMIT 50
```

**Запрос для статистики ошибок:**
```sql
SELECT count(*) FROM Log 
WHERE message LIKE '%Failed to send placeholder message%' 
SINCE 7 DAYS AGO 
TIMESERIES
```

### Ключевые индикаторы

✅ **Все работает:** Нет ошибок, есть `Scheduled illustration generation task`
⚠️ **Fallback сработал:** Есть `Trying text fallback`, но есть `Scheduled illustration generation task`
❌ **Ошибка:** Есть `Failed to send placeholder message` БЕЗ `Scheduled illustration generation task`

## Результаты

- **Исправлено:** Непереведенное сообщение об ошибке теперь переводится на язык пользователя
- **Улучшено:** Процесс генерации иллюстрации не прерывается при ошибке отправки placeholder анимации
- **Оптимизировано:** Обработка 429 ошибок использует рекомендации Telegram API (Retry-After)

## Файлы изменены

- `flirtello-backend-service/src/telegram/locales/en/LC_MESSAGES/messages.po` - добавлен перевод
- `flirtello-backend-service/src/telegram/locales/ru/LC_MESSAGES/messages.po` - добавлен перевод
- `flirtello-backend-service/src/telegram/handlers/media.py` - добавлен fallback на текстовое сообщение
- `flirtello-backend-service/src/telegram/api/core.py` - улучшена обработка 429 ошибок

## Документация

- `AL-144-Findings.md` - технические детали и анализ проблемы через New Relic
- `AL-144-task.md` - исходная задача с обновленным статусом

