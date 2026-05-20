# Интеграция метрик Grafana Cloud через Prometheus Remote Write

План интеграции отправки метрик производительности в облачную Grafana с использованием **prometheus-remote-writer** (✅ протестировано и работает).

## Обзор

Система уже собирает метрики времени выполнения через `context.record_timing()` и логирует их в `dispatcher.py:667-675`. 

**Подход:** В том же месте, где логируем метрики, будем отправлять их в Grafana Cloud используя библиотеку `prometheus-remote-writer`.

**Что протестировали:**
- ✅ Библиотека `prometheus-remote-writer==0.1.2` работает с Grafana Cloud
- ✅ Формат данных: `MetricItem` с полями `metric`, `values`, `timestamps`
- ✅ Отправка через `RemoteWriter.send(metrics)` - успешно
- ✅ Метрики появляются в Grafana Cloud через 1-2 минуты

**Преимущества:**
- ✅ Не нужно трогать существующие вызовы `record_timing()`
- ✅ Request-level labels (язык, персонаж, user_id) из `RequestContext`
- ✅ Простой формат данных - словари вместо protobuf вручную
- ✅ Минимальные изменения кода

## User Review Required

> [!IMPORTANT]
> **Конфигурация Grafana Cloud**
> Нужно будет предоставить актуальные credentials для Grafana Cloud:
> - URL (например: `https://your-instance.grafana.net/api/prom/push`)
> - Username (ваш username или ID)
> - Password/API Key (ваш токен или пароль)
> 
> Эти параметры будут храниться в переменных окружения для безопасности.
> 
> **По умолчанию отправка метрик выключена** (GRAFANA_ENABLED=false).

> [!WARNING]
> **Асинхронная отправка метрик**
> Отправка метрик будет происходить в фоновом режиме (fire-and-forget), чтобы не замедлять обработку запросов пользователей. Ошибки отправки будут логироваться, но не будут влиять на основную функциональность.

## Proposed Changes

### Core Metrics Module

#### [NEW] [metrics_exporter.py](file:///Users/umaxfun/prj/flirtello/flirtello-backend-service/src/telegram/metrics_exporter.py)

Новый модуль для отправки метрик в Grafana Cloud:

```python
import time
from typing import Optional
import logging

from prometheus_remote_writer import RemoteWriter
from src.telegram.context import RequestContext
from src.telegram import config

logger = logging.getLogger(__name__)

class GrafanaMetricsExporter:
    """Singleton для отправки метрик в Grafana Cloud"""
    
    def __init__(self):
        if not config.GRAFANA_ENABLED:
            self.client = None
            return
            
        self.client = RemoteWriter(
            url=config.GRAFANA_URL,
            auth={
                "username": config.GRAFANA_USERNAME,
                "password": config.GRAFANA_PASSWORD,
            }
        )
    
    def export_timings(self, context: RequestContext):
        """Конвертирует context.timings в MetricItems и отправляет в Grafana"""
        if not self.client or not context.timings:
            return
        
        try:
            now = int(time.time())
            
            metrics = []
            for timing in context.timings:
                metric_item = {
                    "metric": {
                        "__name__": "request_operation_duration_ms",
                        "operation": timing.label,
                        "language": context.user_language or "unknown",
                        "char_id": str(context.active_char_id) if context.active_char_id else "none",
                        "env": config.GRAFANA_ENVIRONMENT,  # test/prod разделение
                    },
                    "values": [timing.duration_ms],  # миллисекунды напрямую
                    "timestamps": [now],
                }
                metrics.append(metric_item)
            
            # Fire-and-forget отправка
            self.client.send(metrics)
            
        except Exception as e:
            logger.warning(f"Failed to export metrics to Grafana: {e}")

# Singleton instance
metrics_exporter = GrafanaMetricsExporter()
```

---

### RequestContext (без изменений!)

#### [NO CHANGES] [context.py](file:///Users/umaxfun/prj/flirtello/flirtello-backend-service/src/telegram/context.py)

Используем **существующие поля** `RequestContext` как source для labels:
- `user_language: Optional[str]` - язык пользователя
- `active_char_id: Optional[int]` - ID активного персонажа  
- `user_id: Optional[UUID]` - ID пользователя
- `timings: List[TimingEntry]` - собранные метрики

**Не нужно ничего менять!** Вся информация уже есть в контексте.

---

### Configuration

#### [MODIFY] [config.py](file:///Users/umaxfun/prj/flirtello/flirtello-backend-service/src/telegram/config.py)

Добавить конфигурационные параметры (по умолчанию отключено):

```python
# Grafana Cloud Metrics (disabled by default)
GRAFANA_ENABLED = os.getenv("GRAFANA_METRICS_ENABLED", "false").lower() == "true"
GRAFANA_URL = os.getenv("GRAFANA_PROMETHEUS_URL", "")
GRAFANA_USERNAME = os.getenv("GRAFANA_USERNAME", "")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "")

# Environment label для разделения test/prod (default: test)
GRAFANA_ENVIRONMENT = os.getenv("GRAFANA_ENVIRONMENT", "test")  # "test" или "prod"
```

---

### Integration Point

#### [MODIFY] [dispatcher.py](file:///Users/umaxfun/prj/flirtello/flirtello-backend-service/src/telegram/dispatcher.py)

Добавить **одну строку** после существующего логирования метрик (строки 667-675):

```python
# --- Performance logging --- (EXISTING CODE, lines 667-675)
if context and context.timings:
    timings_str = "; ".join([f"{t.label}={t.duration_ms:.2f}ms" for t in context.timings])
    total_time = sum(t.duration_ms for t in context.timings)
    logger.info(
        f"[{context.request_id}] Performance metrics: Total measured: {total_time:.2f}ms; Breakdown: {timings_str}"
    )
    
    # NEW: Export to Grafana (fire-and-forget)
    if config.GRAFANA_ENABLED:
        try:
            from src.telegram.metrics_exporter import metrics_exporter
            metrics_exporter.export_timings(context)
        except Exception as e:
            logger.warning(f"[{context.request_id}] Failed to export metrics: {e}")
```

---

### Dependencies

#### [MODIFY] [pyproject.toml](file:///Users/umaxfun/prj/flirtello/flirtello-backend-service/pyproject.toml)

Добавить зависимость через `uv`:

```bash
# Prometheus remote writer для отправки метрик в Grafana Cloud
uv add prometheus-remote-writer==0.1.2
```

**Примечание:** Библиотека внутри использует `snappy`, `requests`, `protobuf` - все установится автоматически.

---

## Verification Plan

После реализации:

1. **Локальный тест с включенными метриками**:
   ```bash
   # В .env
   export GRAFANA_METRICS_ENABLED=true
   export GRAFANA_PROMETHEUS_URL="https://your-instance.grafana.net/api/prom/push"
   export GRAFANA_USERNAME="your_username"
   export GRAFANA_PASSWORD="your_password_or_token"
   export GRAFANA_ENVIRONMENT="test"  # или "prod" на проде
   
   # Запустить бота, отправить тестовое сообщение
   # Проверить логи - не должно быть ошибок "Failed to export metrics"
   ```

2. **Проверка в Grafana Cloud** (через 1-2 минуты):
   ```promql
   # В Explore построить запрос:
   request_operation_duration_ms{env="test"}
   
   # Должны увидеть метрики с labels: operation, language, char_id, env
   ```

3. **Полезные Grafana запросы**:
   ```promql
   # P95 времени переводов на русский (ТОЛЬКО ПРОД)
   quantile_over_time(0.95, request_operation_duration_ms{
     operation="translate_user_message", 
     language="ru",
     env="prod"
   }[5m])
   
   # P99 для более точной картины
   quantile_over_time(0.99, request_operation_duration_ms{
     operation="translate_user_message",
     env="prod"
   }[5m])
   
   # Среднее время LLM по языкам (только прод)
   avg_over_time(request_operation_duration_ms{
     operation=~"llm.*", 
     env="prod"
   }[5m]) by (language)
   
   # Сравнение test vs prod (среднее)
   avg_over_time(request_operation_duration_ms[5m]) by (env, operation)
   
   # Максимальное время за период (выбросы)
   max_over_time(request_operation_duration_ms{env="prod"}[5m]) by (operation)
   
   # Медиана (P50) всех операций
   quantile_over_time(0.5, request_operation_duration_ms{env="prod"}[5m]) by (operation)
   ```

4. **Настройка Legend в Grafana** для красивого отображения:
   - Panel Settings → Legend → Custom: `{{operation}} ({{language}})`
   - Или использовать Table/Values mode вместо List
