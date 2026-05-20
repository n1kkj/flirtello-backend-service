# AL-144: Технические находки

## New Relic: Анализ логов ошибок

**Проблема:** При анализе логов через New Relic MCP обнаружена основная причина ошибок.

**Найденные паттерны в логах:**

1. **429 Too Many Requests от Telegram API:**
   ```
   ERROR - An unexpected error occurred in send_animation_placeholder: 
   Client error '429 Too Many Requests' for url 
   'https://api.telegram.org/bot.../sendAnimation'
   ```

2. **Последующая ошибка отправки placeholder:**
   ```
   ERROR - Failed to send placeholder message to user ... in chat ...
   ```

3. **Частота ошибок:**
   - Ошибки происходили регулярно, особенно в периоды высокой нагрузки
   - Несколько ошибок подряд для одного пользователя (11:50:43, 11:50:52, 11:50:57, 11:51:27)
   - Ошибки возникали при отправке анимации placeholder перед генерацией иллюстрации

**Вывод:** Основная причина - превышение лимита запросов к Telegram API при отправке placeholder анимации.

## Telegram API: Обработка 429 ошибок

**Проблема:** Telegram API возвращает 429 ошибку с заголовком `Retry-After`, но код не использовал этот заголовок.

**Решение:**

```python
# Для 429 используем Retry-After заголовок, если он есть
retry_delay = fixed_delay_seconds
if e.response.status_code == 429:
    retry_after = e.response.headers.get("Retry-After")
    if retry_after:
        try:
            retry_delay = float(retry_after)
        except (ValueError, TypeError):
            # Fallback на экспоненциальную задержку
            retry_delay = min(fixed_delay_seconds * (2 ** attempt), 60.0)
```

**Принципы:**
1. Всегда проверяем заголовок `Retry-After` от Telegram API
2. Если заголовок отсутствует, используем экспоненциальную задержку
3. Максимальная задержка ограничена 60 секундами

## Fallback стратегия для placeholder сообщений

**Проблема:** При ошибке отправки placeholder анимации процесс генерации иллюстрации полностью прерывался.

**Решение:** Многоуровневый fallback:

1. **Первый уровень:** Попытка отправить анимацию/видео placeholder
2. **Второй уровень (fallback):** Если анимация не удалась, отправка текстового сообщения
3. **Третий уровень (ошибка):** Только если и текстовое сообщение не удалось, отправка ошибки пользователю

**Код:**

```python
if not placeholder_message_data or "result" not in placeholder_message_data:
    logger.warning("Failed to send placeholder animation/video. Trying text fallback...")
    try:
        placeholder_response = await send_tg_message(
            sender_chat_id,
            _("Your illustration is being generated... 👨‍🎨"),
            token,
        )
        placeholder_message_data = await placeholder_response.json()
        # ... обработка успешного fallback
    except Exception as fallback_error:
        # ... обработка ошибки fallback
```

**Преимущества:**
- Процесс генерации иллюстрации продолжается даже при ошибке отправки анимации
- Пользователь видит индикатор процесса (текстовое сообщение)
- Ошибка отправляется только в критических случаях

## Локализация: Добавление новых сообщений

**Проблема:** Сообщение "Something went wrong while preparing your request. Please try again. ❤️" использовалось в коде, но отсутствовало в файлах локализации.

**Решение:**
1. Добавить `msgid` и `msgstr` в оба файла локализации (en и ru)
2. Использовать функцию `_()` для перевода в коде
3. После изменений в `.po` файлах нужно скомпилировать их в `.mo` файлы

**Важно:** После добавления переводов в `.po` файлы необходимо:
- Скомпилировать их в `.mo` файлы (обычно через `msgfmt` или систему сборки)
- Перезапустить приложение для применения изменений

## Выводы

1. **Мониторинг через New Relic:** Анализ логов через New Relic MCP помогает быстро находить корневые причины проблем
2. **Обработка rate limiting:** Всегда использовать заголовки `Retry-After` от API, если они предоставляются
3. **Fallback стратегии:** Многоуровневые fallback механизмы повышают надежность системы
4. **Локализация:** Все пользовательские сообщения должны быть в файлах локализации, даже сообщения об ошибках
5. **Graceful degradation:** Система должна продолжать работать даже при частичных сбоях (например, ошибка отправки анимации не должна прерывать генерацию иллюстрации)

