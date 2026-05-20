# AL-142: Технические находки

## prometheus-remote-writer: Формат данных MetricItem

**Проблема:** Библиотека `prometheus-remote-write` (рекомендуемая в документации Prometheus) удалена из PyPI. Попытки реализовать Remote Write API вручную приводили к ошибкам сериализации protobuf.

**Решение:** Использовать библиотеку `prometheus-remote-writer==0.1.2`, которая имеет простой формат данных:

```python
metric_item = {
    "metric": {
        "__name__": "metric_name",
        "label1": "value1",
        "label2": "value2",
    },
    "values": [123.45],  # список значений
    "timestamps": [1732704000000],  # timestamp в миллисекундах
}

client = RemoteWriter(
    url="https://...",
    auth={"username": "...", "password": "..."}
)
client.send([metric_item])  # отправка списка метрик
```

**Важно:**
- Timestamps должны быть в **миллисекундах**, иначе библиотека выдаст warning и конвертирует автоматически
- Используется метод `send()`, а не `write()`
- Библиотека автоматически обрабатывает protobuf сериализацию и Snappy компрессию

## PromQL: Gauge метрики vs Histogram

**Проблема:** Изначально планировалось использовать `histogram_quantile()` для расчета P95/P99, но для этого нужны histogram buckets.

**Что обнаружено:** Мы отправляем простые значения (gauge), а не histogram с buckets. Для gauge метрик нужны другие функции:

```promql
# ❌ НЕ РАБОТАЕТ для gauge
histogram_quantile(0.95, rate(request_operation_duration_ms[5m]))

# ✅ РАБОТАЕТ для gauge
quantile_over_time(0.95, request_operation_duration_ms[5m])
```

**Принцип:** 
- `histogram_quantile()` - для histogram метрик с buckets
- `quantile_over_time()` - для gauge метрик (вычисляет квантили из точек за период)

## PromQL: Подсчет количества запросов

**Что обнаружено:** Каждая отправленная метрика = один datapoint. Можем считать количество запросов через `count_over_time()`:

```promql
# Количество запросов за 1 час по операциям
count_over_time(request_operation_duration_ms{env="prod"}[1h]) by (operation)

# RPS (запросов в секунду)
rate(request_operation_duration_ms{env="prod"}[5m]) * 60

# Топ-5 персонажей по количеству запросов
topk(5, count_over_time(request_operation_duration_ms[1h]) by (char_id))
```

**Применение:**
- Трафик аналитика без дополнительных метрик
- Динамика нагрузки
- Распределение запросов по измерениям (язык, персонаж, операция)

## Grafana: Переменные окружения для разделения test/prod

**Проблема:** Метрики из test и prod окружений смешиваются в одной базе.

**Решение:** Добавить label `env` с значением из переменной окружения `GRAFANA_ENVIRONMENT`:

```python
"env": config.GRAFANA_ENVIRONMENT  # "test", "prod", "ww"
```

**В Grafana:**
- Создать template variable `$env` с query: `label_values(request_operation_duration_ms, env)`
- Использовать в запросах: `{env="$env"}`
- Позволяет переключаться между окружениями в UI

## Grafana MCP: Подключение и создание дашбордов

**Проблема:** MCP сервер для Grafana не подключался из-за неправильной конфигурации.

**Решение:**
1. URL должен быть базовым URL Grafana (не endpoint `/api/prom/push`)
2. Использовать `GRAFANA_SERVICE_ACCOUNT_TOKEN` вместо username/password
3. Service Account должен иметь права `datasources:read` и другие необходимые разрешения

**Конфигурация MCP:**
```json
{
  "grafana": {
    "command": "mcp-grafana",
    "args": [],
    "env": {
      "GRAFANA_URL": "https://aikolounge.grafana.net/",
      "GRAFANA_SERVICE_ACCOUNT_TOKEN": "glsa_..."
    }
  }
}
```

**Создание дашбордов через MCP:**
- Использовать `mcp_grafana_update_dashboard` с полным JSON дашборда
- Сначала создать папку через `mcp_grafana_create_folder`
- Указать `folderUid` при создании дашборда

## PromQL: Исправление ошибок в дашбордах

**Проблемы обнаружены:**
1. Двойная агрегация: `avg(avg_over_time(...))` → должно быть просто `avg_over_time(...)`
2. Двойной quantile: `quantile(0.95, quantile_over_time(0.95, ...))` → должно быть `quantile_over_time(0.95, ...)`
3. Неправильное использование `increase()` для gauge метрик

**Исправления:**
- Для gauge метрик использовать `count_over_time()` для подсчета запросов (считает точки данных)
- `increase()` работает только для counter метрик
- Убрать лишние агрегации - `avg_over_time` и `quantile_over_time` уже возвращают агрегированные значения

**Правильные запросы:**
```promql
# ✅ Подсчет запросов для gauge
sum(count_over_time(request_operation_duration_ms{env="$env"}[1h]))

# ✅ Среднее время (без двойной агрегации)
avg_over_time(request_operation_duration_ms{env="$env"}[5m])

# ✅ P95 (без двойного quantile)
quantile_over_time(0.95, request_operation_duration_ms{env="$env"}[5m])
```

## Grafana: Настройка datasource в дашбордах

**Проблема:** Дашборды использовали строку "Prometheus" вместо UID datasource.

**Решение:** Использовать объект datasource с UID:
```json
{
  "datasource": {
    "type": "prometheus",
    "uid": "grafanacloud-prom"
  }
}
```

**Для template variables:**
- Также использовать объект datasource, а не строку
- Это позволяет дашборду работать в любом Grafana instance с правильным datasource

## Grafana: Динамический фильтр по окружениям

**Настройка:**
```json
{
  "name": "env",
  "type": "query",
  "label": "Environment",
  "datasource": {
    "type": "prometheus",
    "uid": "grafanacloud-prom"
  },
  "query": "label_values(request_operation_duration_ms, env)",
  "includeAll": true,
  "multi": true,
  "sort": 1
}
```

**Возможности:**
- Автоматическое обновление списка доступных окружений
- Множественный выбор (можно выбрать prod и ww одновременно)
- Опция "All" для просмотра всех окружений

## Выводы

1. **prometheus-remote-writer** - надежная альтернатива удаленной `prometheus-remote-write`
2. **Timestamps в миллисекундах** обязательны для корректной работы
3. **Gauge метрики** требуют `quantile_over_time()`, а не `histogram_quantile()`
4. **count_over_time()** позволяет считать количество запросов без дополнительных counter метрик
5. **Label `env`** критичен для разделения данных разных окружений
6. **Fire-and-forget** отправка метрик обеспечивает minimal overhead на production
7. **MCP Grafana** требует Service Account Token и правильный базовый URL
8. **Избегать двойных агрегаций** в PromQL - `avg_over_time` и `quantile_over_time` уже агрегируют
9. **Использовать UID datasource** в дашбордах для переносимости
10. **Динамические фильтры** с `includeAll` и `multi` улучшают UX дашбордов
