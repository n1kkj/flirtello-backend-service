import time
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
            now = int(time.time() * 1000)
            
            metrics = []
            for timing in context.timings:
                metric_item = {
                    "metric": {
                        "__name__": "request_operation_duration_ms",
                        "operation": timing.label,
                        "language": context.user_language or "unknown",
                        "char_id": str(context.active_char_id) if context.active_char_id else "none",
                        "env": config.GRAFANA_ENVIRONMENT,
                    },
                    "values": [timing.duration_ms],  # миллисекунды напрямую
                    "timestamps": [now],
                }
                metrics.append(metric_item)
            
            # Fire-and-forget отправка
            logger.debug(f"Sending metrics to Grafana: {len(metrics)} items. Env: {config.GRAFANA_ENVIRONMENT}")
            self.client.send(metrics)
            
        except Exception as e:
            logger.warning(f"Failed to export metrics to Grafana: {e}")

# Singleton instance
metrics_exporter = GrafanaMetricsExporter()
