# Дизайн Сервиса Переводов с Персистентной Памятью

## 1. Обзор Архитектуры

Цель — интегрировать персистентную **Память переводов (Translation Memory, TM)** в существующий `Translator` сервис. Это будет достигнуто путем реализации интерфейса `BaseTranslationMemory` с использованием SQL-базы данных и модификации основной логики `Translator` для поддержки многоуровневого кэширования.

### 1.1. Логика получения перевода

Процесс получения перевода будет следовать четкому иерархическому алгоритму для максимальной производительности и минимизации затрат:

1.  **L1 Cache (In-Memory):** `Translator` сначала проверяет наличие перевода в локальном `TTLCache`. При попадании, результат немедленно возвращается.
2.  **L2 Cache (Database TM):** Если в L1 кэше промах, `Translator` обращается к `SQLTranslationMemory` для поиска в таблице `translations` в БД.
    *   При попадании, результат сохраняется в L1 кэш и возвращается.
    *   Особое внимание уделяется записям с флагом `is_verified_by_human = true`. Если такая запись найдена, ее результат считается окончательным и не подлежит дальнейшей обработке.
3.  **LLM Fallback:** Если перевод не найден ни в одном из кэшей, `Translator` обращается к LLM.
4.  **Сохранение:** Полученный от LLM перевод сохраняется в L2 (база данных) с флагом `is_verified_by_human = false`, а затем кэшируется в L1 (in-memory).

## 2. Компоненты

### 2.1. Модификация `Translator` (`translator.py`)

Это центральный компонент, который будет оркестрировать весь процесс.

```python
class Translator:
    def __init__(
        self,
        *,
        tm: BaseTranslationMemory,
        # ... другие зависимости ...
    ):
        self._tm = tm
        # ...
        # L1 Cache
        self._local_cache = TTLCache(maxsize=1024, ttl=60) 

    def translate(self, request: TranslationRequest) -> TranslationResult:
        # 1. Определить ключ (контекстный или текстовый)
        final_key = request.context_key or request.source_text

        # 2. Проверить L1 Cache
        cached_result = self._local_cache.get(final_key)
        if cached_result:
            return TranslationResult(translated_text=cached_result, ...)

        # 3. Проверить L2 Cache (TM в БД)
        # Это потребует модификации. Вместо векторного поиска, 
        # нам нужен поиск по ключу.
        tm_entry = self._tm.get_by_key(final_key, request.target_lang)

        if tm_entry:
            # Если перевод верифицирован, не дергаем LLM
            if tm_entry.is_verified:
                 self._local_cache[final_key] = tm_entry.target_text
                 return TranslationResult(translated_text=tm_entry.target_text, ...)
            # Если не верифицирован, можно использовать как пример для LLM
            # ...

        # 4. Обращение к LLM (с учетом найденных неверифицированных примеров)
        translated_text = self._invoke_llm(...)

        # 5. Сохранение в L2 и L1
        self._tm.add(key=final_key, ..., translated_text=translated_text)
        self._local_cache[final_key] = translated_text
        
        return TranslationResult(translated_text=translated_text, ...)

```
**Ключевое изменение:** Логика `translate` будет расширена для оркестрации L1/L2 кэшей. Также потребуется доработать интерфейс `BaseTranslationMemory` (или логику `Translator`), чтобы добавить метод поиска по ключу (`get_by_key`), а не только по вектору.

### 2.2. SQL-реализация `BaseTranslationMemory` (`sql_tm.py`)

Будет создан класс `SQLTranslationMemory`, реализующий доработанный интерфейс `BaseTranslationMemory`. Он будет отвечать за взаимодействие с таблицей `translations`.

### 2.3. Модель Данных (`models.py`)

Будет создана `SQLModel` `Translation`, полностью соответствующая требованиям. Модель будет привязана к схеме `translator` в базе данных.

**Схема таблицы `translator.translations`:**

| Поле                  | Тип       | Индекс | Описание                                        |
| --------------------- | --------- | ------ | ----------------------------------------------- |
| `id`                  | `Integer` | PK     | Первичный ключ                                  |
| `key`                 | `String`  | Да     | Гибридный ключ (`entity:id` или `source_text`)  |
| `language`            | `String`  | Да     | Код языка ('ru', 'en')                          |
| `source_text`         | `String`  |        | Оригинальный текст                              |
| `translated_text`     | `String`  |        | Переведенный текст                              |
| `is_verified_by_human` | `Boolean` | Да     | `true`, если проверено человеком                |
| `created_at`          | `DateTime`|        | Дата создания                                   |
| `updated_at`          | `DateTime`|        | Дата обновления                                 |

### 2.4. Миграции и DI

*   Миграции для создания схемы `translator` и таблицы `translator.translations` будут храниться в `src/translator/migrations/`.
*   Интеграция будет осуществлена через замену `InMemoryTranslationMemory` на `SQLTranslationMemory` в DI-контейнере.
