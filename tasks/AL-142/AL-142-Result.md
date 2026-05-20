# AL-142: Интеграция метрик Grafana Cloud

## Задача

Интегрировать отправку метрик производительности в Grafana Cloud через Prometheus Remote Write API для анализа UX и производительности системы.

## Что сделано

### 1. Модуль экспорта метрик
- Создан `src/telegram/metrics_exporter.py` с классом `GrafanaMetricsExporter`
- Использует библиотеку `prometheus-remote-writer` для отправки метрик
- Формат: `MetricItem` с полями `metric`, `values`, `timestamps`
- Отправка асинхронная (fire-and-forget) для минимального влияния на производительность

### 2. Интеграция в диспетчер
- Добавлен вызов `metrics_exporter.export_timings(context)` в `src/telegram/dispatcher.py`
- Метрики отправляются после каждого запроса, где есть тайминги
- Graceful error handling - ошибки отправки не влияют на основную функциональность

### 3. Конфигурация
- Добавлены переменные окружения в `src/telegram/config.py`:
  - `GRAFANA_METRICS_ENABLED` (default: false)
  - `GRAFANA_PROMETHEUS_URL`
  - `GRAFANA_USERNAME`
  - `GRAFANA_PASSWORD`
  - `GRAFANA_ENVIRONMENT` (для разделения test/prod/ww)

### 4. Зависимости
- Добавлена библиотека `prometheus-remote-writer==0.1.2` через `uv`
- Автоматически устанавливает необходимые зависимости (snappy, protobuf, requests)

### 5. Готовые дашборды Grafana
- **Overview** - комбинированный дашборд с ключевыми метриками (Total Requests, Average/P95 Response Time, RPS, распределения)
- **Traffic & Usage** - RPS, количество запросов, топ персонажей/языков, рост трафика
- **Performance Metrics** - P95, P99, средние времена операций, производительность по языкам
- Все дашборды созданы в Grafana Cloud через MCP API
- Настроен динамический фильтр по окружениям (env) с множественным выбором

## Верификация

✅ Метрики успешно отправляются в Grafana Cloud (подтверждено логами)
✅ Timestamp warning исправлен (конвертация в миллисекунды)
✅ Debug логирование добавлено для мониторинга отправки
✅ Все PromQL запросы проверены и исправлены через MCP
✅ Дашборды созданы в Grafana Cloud в папке "Aiko Lounge"
✅ Динамический фильтр env работает корректно
✅ Datasource настроен правильно (grafanacloud-prom)

## Результаты

**Метрика:** `request_operation_duration_ms`

**Labels:**
- `operation` - название операции (translate_user_message, llm_send_and_get_response, и т.д.)
- `language` - язык пользователя
- `char_id` - ID персонажа
- `env` - окружение (test/prod/ww)

**Возможности аналитики:**
- P95/P99 времени отклика по операциям
- Количество запросов и RPS
- Распределение по языкам
- Топ самых активных персонажей
- Сравнение производительности test vs prod

## Файлы изменены

- `src/telegram/metrics_exporter.py` - новый модуль экспорта метрик
- `src/telegram/config.py` - добавлена конфигурация Grafana
- `src/telegram/dispatcher.py` - интеграция отправки метрик
- `pyproject.toml` - добавлена зависимость prometheus-remote-writer

## Документация

- `tasks/AL-142/AL-142-Findings.md` - технические находки и решения
- `tasks/AL-142/artifacts/implementation_plan.md` - детальный план реализации
- `tasks/AL-142/artifacts/grafana-dashboard-*.json` - готовые дашборды (проверены и исправлены)
- `tasks/AL-142/artifacts/prom.py` - POC скрипт для тестирования

## Созданные дашборды в Grafana

Все дашборды находятся в папке **"Aiko Lounge"**:

1. **Aiko Lounge - Overview** (UID: `b701b37d-24b4-41b9-83bc-824e6a21a4b2`)
2. **Aiko Lounge - Traffic & Usage** (UID: `77f9c5dd-01e8-4b13-bac0-0e471aae67bd`)
3. **Aiko Lounge - Performance Metrics** (UID: `761978fb-9a59-400f-94f4-d25a7b48e148`)
