# AL-143: Технические находки

## SQLAlchemy: Работа с NULL значениями

**Проблема:** В SQL сравнение `NULL = NULL` возвращает `NULL` (не `TRUE`), поэтому обычное сравнение через `==` не работает для NULL значений.

**Пример проблемы:**
```python
# ❌ Неправильно - не найдет канал, если config_id = NULL
Channel.config_id == current_config_id_from_settings  # NULL = NULL → NULL (не TRUE)
```

**Решение:**
```python
# ✅ Правильно - явная проверка на NULL
config_condition = (
    (Channel.config_id == current_config_id_from_settings)
    if current_config_id_from_settings is not None
    else Channel.config_id.is_(None)
)
```

**Когда использовать:**
- При сравнении полей, которые могут быть `NULL`
- Когда нужно найти записи, где поле равно `NULL`
- При работе с опциональными полями в условиях WHERE

## База данных: Структура каналов

**Что обнаружено:**
- Таблица `channels` содержит каналы между пользователями и персонажами
- Канал идентифицируется комбинацией: `user_id`, `char_id`, `config_id`
- `config_id` может быть `NULL` для обычных чатов (не сюжетных)
- `config_id` указывает на конфигурацию сюжетной истории (`content.character_configs`)

**Связи:**
- `channels.user_id` → `users.id`
- `channels.char_id` → `content_characters.id`
- `channels.config_id` → `character_configs.id` (может быть NULL)

**Как использовать:**
- При поиске канала нужно учитывать, что `config_id` может быть `NULL`
- Нельзя полагаться на простое сравнение `==` для NULL значений
- Нужно явно проверять `is_(None)` для NULL значений

## Telegram: Команда /me333

**Назначение:** Отладочная команда для просмотра информации о текущем пользователе.

**Отображаемые поля:**
- `tg_id` - Telegram chat ID
- `id` - UUID пользователя в системе
- `active_char_id` - ID текущего активного персонажа (из настроек)
- `config_id` - ID текущей конфигурации истории (из настроек, может быть NULL)
- `channel_id` - ID текущего канала (найден по char_id, user_id, config_id)
- `sb_id` - Supabase ID пользователя

**Логика получения channel_id:**
1. Получаем `active_char_id` из настроек пользователя
2. Получаем `config_id` из настроек пользователя (может быть NULL)
3. Ищем канал по комбинации `char_id`, `user_id`, `config_id`
4. Если `config_id` NULL, используем `Channel.config_id.is_(None)`

## Выводы

1. **Всегда проверяйте NULL значения явно** при работе с SQLAlchemy - используйте `.is_(None)` вместо `== None`
2. **Учитывайте опциональные поля** в условиях WHERE - они могут быть NULL
3. **Тестируйте edge cases** - особенно случаи с NULL значениями в базе данных
4. **Используйте условную логику** для построения запросов с учетом возможных NULL значений

