# AL-142: Интеграция метрик Grafana Cloud

## Описание задачи

Интеграция отправки метрик производительности в Grafana Cloud через Prometheus Remote Write API.
Необходимо собирать метрики длительности операций (перевод, LLM запросы) с контекстными метками (язык, персонаж, окружение) для анализа UX и производительности.

**Основные требования:**
- Использовать библиотеку `prometheus-remote-writer`
- Метрика: `request_operation_duration_ms` (Gauge)
- Labels: `operation`, `language`, `char_id`, `env`
- Конфигурация через переменные окружения
- Асинхронная отправка (fire-and-forget)

## Чеклист

- [x] Понял задачу
- [x] Изучил код
- [x] Провел POC (prometheus-remote-writer работает)
- [x] Составил план реализации (implementation_plan.md)
- [x] Реализовал решение
  - [x] Модуль metrics_exporter.py
  - [x] Интеграция в dispatcher.py
  - [x] Конфигурация
- [x] Протестировал
- [x] Создал Result.md
- [x] Создал Findings.md
- [x] Организовал артефакты

## Заметки

**Решения из этапа планирования:**
1. **Библиотека:** `prometheus-remote-writer` (так как `prometheus-remote-write` удалена из PyPI, а ручная реализация сложна).
2. **Формат данных:** `MetricItem` (dict) -> Protobuf + Snappy (делает библиотека).
3. **Метрики:**
   - `request_operation_duration_ms` (значение в миллисекундах).
   - Используем `quantile_over_time` в Grafana для расчета P95/P99 (так как отправляем gauge, а не histogram buckets).
4. **Labels:**
   - `operation`: название операции (из `timing.label`)
   - `language`: язык пользователя
   - `char_id`: ID персонажа
   - `env`: `test` или `prod` (из конфига)
5. **Конфигурация:**
   - `GRAFANA_METRICS_ENABLED`
   - `GRAFANA_PROMETHEUS_URL`
   - `GRAFANA_USERNAME`
   - `GRAFANA_PASSWORD`
   - `GRAFANA_ENVIRONMENT`
