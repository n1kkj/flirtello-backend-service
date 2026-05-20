# Тулза для экспериментов с постпроцессингом сообщений

## Чеклист задач

- [x] Вытащить тестовые сообщения из БД (из длинных чатов, от персонажа, из начала/середины/конца)
- [x] Вытащить фрагменты диалогов из БД (последние 10 сообщений из разных чатов, для определения контекста)
- [x] Создать промпты для определения контекста (rating: safe/questionable/nude/explicit)
- [x] Создать тулзу для запуска экспериментов (чтение experiment.yaml, кэширование, запросы к LLM)
- [x] Создать скрипт для просмотра результатов (view_results.py)
- [ ] Запустить эксперименты и проанализировать результаты
- [ ] Создать промпты для изменения длины сообщений (по типам сцен и целевым длинам)

## Постановка задачи

Универсальная тулза для тестирования любых промптов с LLM моделями. Поддерживает кэширование результатов для избежания повторных запросов.

**Важно**: Все промпты должны быть написаны на английском языке.

### Структура

Каждый класс экспериментов находится в отдельной папке со своими промптами, тестовыми данными и результатами:

```
postprocessing-experiments/
├── README.md                    # Общая инструкция (этот файл)
├── run_experiment.py            # Общий скрипт для запуска экспериментов
├── view_results.py              # Общий скрипт для просмотра результатов
│
├── context_detection/           # Эксперименты по определению контекста (rating)
│   ├── prompts/
│   │   └── context_detection_v3.md
│   ├── test_dialogs/
│   │   ├── dialog_001_start.md
│   │   └── ...
│   ├── experiments/
│   │   └── experiment_010_ministral_v3_full.yaml
│   └── results/
│       ├── cache/
│       └── experiment_*.json
│
├── message_length/              # Эксперименты по изменению длины сообщений
│   ├── prompts/
│   │   ├── make_short.md
│   │   ├── make_medium.md
│   │   └── make_big.md
│   ├── test_messages/
│   │   ├── message_001_start.md
│   │   └── ...
│   ├── experiments/
│   │   └── experiment_012_shorten_dialogue.yaml
│   └── results/
│       ├── cache/
│       └── experiment_*.json
│
└── error_detection/             # Эксперименты по поиску ошибок в диалогах
    ├── prompts/
    │   └── error_detection.md
    ├── test_dialogs/
    │   └── ...
    ├── experiments/
    │   └── experiment_001_errors.yaml
    └── results/
        ├── cache/
        └── experiment_*.json
```

**Преимущества такой структуры:**
- Изоляция разных типов экспериментов
- Собственные промпты и тестовые данные для каждого класса
- Независимые результаты и кэш
- Легко добавлять новые классы экспериментов

### Формат experiment.yaml

Один файл описывает один эксперимент:

```yaml
name: "Test context detection"
parse_field: "category"  # XML field name to parse from LLM response (e.g., <category>nude</category>)
models:
  - "aisuite://openai/gpt-3.5-turbo"
  - "aisuite://openai/gpt-4o-mini"
prompts:
  - "prompts/context_detection.md"
dialogs:
  - "test_dialogs/dialog_001_start.md"
  - "test_dialogs/dialog_002_middle.md"
```

Или для экспериментов с изменением длины:

```yaml
name: "Test message length adjustment"
models:
  - "aisuite://openai/gpt-3.5-turbo"
prompts:
  - "prompts/safe_short.md"
messages:
  - "test_messages/message_001_start.md"
  - "test_messages/message_002_middle.md"
```

### Кэширование

- Результаты кэшируются по хэшу: `hash(prompt_content + message_content + model_url)`
- Кэш хранится в `results/cache/{hash}.json`
- При повторном запуске проверяется кэш перед запросом к LLM
- Это позволяет не ходить к модели по 100 раз с одинаковыми запросами

### Цель экспериментов

Найти оптимальную комбинацию:
- **LLM модель** (несколько вариантов, более простые/дешевые)
- **Промпты** для определения контекста и изменения длины сообщений
- **Результат**: качественное определение контекста и изменение длины с сохранением смысла

### Выходные данные

- JSON файлы с результатами каждого эксперимента
- Таблица результатов с оценками качества
- Примеры измененных сообщений
- Рекомендации по выбору модели и промптов

## Инструкция по запуску экспериментов

### Быстрый старт

1. **Создайте файл эксперимента** в папке `experiments/`:
   ```yaml
   name: "My Experiment"
   parse_field: "category"  # или null, если не нужен парсинг XML
   models:
     - "openrouter://mistralai/ministral-8b"
   prompts:
     - "prompts/my_prompt.md"
   dialogs:
     - "test_dialogs/dialog_001_start.md"
   # или messages:
   #   - "test_messages/message_001_start.md"
   ```

2. **Запустите эксперимент**:
   ```bash
   cd tasks/AL-138/artifacts/postprocessing-experiments
   uv run python run_experiment.py experiment_name.yaml
   ```

3. **Просмотрите результаты**:
   ```bash
   uv run python view_results.py experiment_name_results.json
   ```

### Детальная инструкция

#### Шаг 1: Выбор или создание папки для класса экспериментов

**Если эксперимент относится к существующему классу:**
- Используйте соответствующую папку (например, `context_detection/`, `message_length/`)

**Если создаете новый класс экспериментов:**
- Создайте новую папку (например, `error_detection/`)
- Создайте структуру:
  ```bash
  mkdir -p error_detection/{prompts,test_dialogs,experiments,results/cache}
  ```

#### Шаг 2: Подготовка данных

**Для экспериментов с диалогами:**
- Используйте скрипт `fetch_more_dialogs.py` для извлечения фрагментов диалогов из БД
- Сохраняйте в `{experiment_class}/test_dialogs/` с именами вида `dialog_NNN_position.md`

**Для экспериментов с отдельными сообщениями:**
- Используйте скрипт `fetch_messages_by_length.py` для извлечения сообщений
- Сохраняйте в `{experiment_class}/test_messages/` с именами вида `message_NNN_length_position.md`

#### Шаг 3: Создание промпта

1. Создайте файл в папке `{experiment_class}/prompts/` (например, `context_detection/prompts/my_prompt.md`)
2. Промпт должен быть на **английском языке**
3. Если нужен парсинг XML, используйте формат:
   ```xml
   <rationale>...</rationale>
   <result>...</result>
   ```
   или другой формат с указанным `parse_field`

#### Шаг 4: Создание конфигурации эксперимента

Создайте файл `{experiment_class}/experiments/experiment_XXX_name.yaml`:

```yaml
name: "Experiment Name"
parse_field: "category"  # XML поле для парсинга, или null
models:
  - "openrouter://mistralai/ministral-8b"
  - "openrouter://mistralai/mixtral-8x7b-instruct"
prompts:
  - "prompts/my_prompt.md"  # путь относительно папки класса экспериментов
dialogs:  # для экспериментов с диалогами
  - "test_dialogs/dialog_001_start.md"  # путь относительно папки класса экспериментов
  - "test_dialogs/dialog_002_middle.md"
messages:  # для экспериментов с отдельными сообщениями
  - "test_messages/message_001_start.md"  # путь относительно папки класса экспериментов
  - "test_messages/message_002_middle.md"
```

**Параметры:**
- `name`: Название эксперимента (будет в результатах)
- `parse_field`: Имя XML тега для извлечения (например, "category", "result"). Если `null`, скрипт попытается найти `<result>` автоматически
- `models`: Список моделей в формате URI (OpenRouter, OpenAI и т.д.)
- `prompts`: Список путей к файлам промптов
- `dialogs` или `messages`: Список путей к тестовым данным

#### Шаг 5: Запуск эксперимента

```bash
# Из папки postprocessing-experiments
# Укажите путь к файлу эксперимента относительно папки класса
uv run python run_experiment.py context_detection/experiments/experiment_010_ministral_v3_full.yaml

# С ограничением количества тестов (для быстрой проверки)
uv run python run_experiment.py message_length/experiments/experiment_012_shorten_dialogue.yaml --limit 5
```

**Что происходит:**
- Скрипт определяет папку класса экспериментов из пути к файлу
- Читает конфигурацию из `{experiment_class}/experiments/`
- Загружает промпты и тестовые данные из папки класса
- Проверяет кэш для каждого запроса
- Запускает запросы к LLM моделям (параллельно, до 5 одновременно)
- Измеряет latency и cost
- Сохраняет результаты в `{experiment_class}/results/{experiment_name}_results.json`

#### Шаг 6: Просмотр результатов

```bash
# Показать список всех результатов в конкретной папке класса
cd context_detection
uv run python ../view_results.py

# Открыть конкретный результат (путь относительно папки класса)
cd context_detection
uv run python ../view_results.py results/experiment_010_ministral_v3_full_results.json

# Или из корня postprocessing-experiments
uv run python view_results.py context_detection/results/experiment_010_ministral_v3_full_results.json
```

**В HTML отчете доступно:**
- Таблица с результатами (Detailed View)
- Матрица сравнения моделей (Comparison Matrix)
- Простой список по входным данным (By Input)
- Фильтры по модели, промпту, типу, категории
- Статистика: latency, cost, количество ошибок

### Требования

- Переменная окружения `OPENROUTER_API_KEY` для работы с OpenRouter моделями
- Установленные зависимости через `uv` (автоматически при использовании `uv run`)

### Кэширование

- Результаты кэшируются по хэшу: `hash(prompt_content + input_content + model_url)`
- Кэш хранится в `results/cache/` в иерархической структуре (первые 3 символа хэша)
- При повторном запуске проверяется кэш перед запросом к LLM
- Это позволяет не делать повторные запросы с одинаковыми данными

## Создание нового класса экспериментов

Если вам нужен новый класс экспериментов (например, поиск ошибок в диалогах):

1. **Создайте структуру папок:**
   ```bash
   cd postprocessing-experiments
   mkdir -p new_experiment_class/{prompts,test_dialogs,experiments,results/cache}
   ```

2. **Создайте README для нового класса** (опционально):
   ```bash
   touch new_experiment_class/README.md
   ```
   В этом README опишите специфику этого класса экспериментов.

3. **Используйте общие скрипты** `run_experiment.py` и `view_results.py` - они работают с любой папкой класса экспериментов.

**Пример структуры для нового класса:**
```
error_detection/
├── README.md                    # Специфичная инструкция (опционально)
├── prompts/
│   └── error_detection.md
├── test_dialogs/
│   └── dialog_*.md
├── experiments/
│   └── experiment_001_errors.yaml
└── results/
    ├── cache/
    └── experiment_*.json
```

**Преимущества:**
- Полная изоляция разных классов экспериментов
- Собственные промпты и тестовые данные для каждого класса
- Независимые результаты и кэш
- Легко добавлять новые классы без изменения существующих

