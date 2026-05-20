"""
Proof of concept: отправка метрик в Grafana Cloud через Prometheus Remote Write API
Использует prometheus-remote-writer library с правильным форматом данных
"""

import os
import random
import time

from prometheus_remote_writer import RemoteWriter

# Учетные данные Grafana Cloud (заполните своими):
url = os.getenv(
    "GRAFANA_PROMETHEUS_URL", "https://your-instance.grafana.net/api/prom/push"
)
username = os.getenv("GRAFANA_USERNAME", "")
password = os.getenv("GRAFANA_PASSWORD", "")

# Создаём клиента для отправки метрик
client = RemoteWriter(
    url=url,
    auth={
        "username": username,
        "password": password,
    },
)

# Тестовый цикл
print("Starting metrics POC with prometheus-remote-writer...")
print(f"Sending to: {url}")
print(f"Username: {username}")
print()
print("📊 Отправляем метрики каждые 10 секунд...")
print("🎯 В Grafana Cloud они появятся через 1-2 минуты")
print("🔍 Проверь в Grafana: Explore → request_operation_duration_seconds")
print()

iteration = 0
while True:
    iteration += 1

    # Текущее время в секундах (библиотека автоматически конвертирует в миллисекунды)
    now = int(time.time())

    # Рандомизируем значения для красивых графиков
    # Симулируем реальные вариации времени выполнения
    translate_time_ru = random.uniform(0.8, 2.5)  # перевод на русский: 0.8-2.5 сек
    translate_time_en = random.uniform(0.5, 1.5)  # перевод на английский: быстрее
    llm_time = random.uniform(2.0, 5.0)  # LLM вызов: 2-5 сек

    # Симулируем разные операции с разным временем
    # Настройка отображения делается в Grafana, а не тут
    metrics = [
        {
            "metric": {
                "__name__": "request_operation_duration_seconds",
                "operation": "translate_user_message",
                "language": "ru",
            },
            "values": [translate_time_ru],
            "timestamps": [now],
        },
        {
            "metric": {
                "__name__": "request_operation_duration_seconds",
                "operation": "llm_send_and_get_response",
                "language": "ru",
            },
            "values": [llm_time],
            "timestamps": [now],
        },
        {
            "metric": {
                "__name__": "request_operation_duration_seconds",
                "operation": "translate_user_message",
                "language": "en",
            },
            "values": [translate_time_en],
            "timestamps": [now],
        },
    ]

    print(
        f"[Iteration {iteration}] 📤 Sending: ru_translate={translate_time_ru:.2f}s, llm={llm_time:.2f}s, en_translate={translate_time_en:.2f}s"
    )

    # Отправляем в Grafana
    try:
        result = client.send(metrics)
        print(f"✅ [Iteration {iteration}] Metrics sent successfully!")
        print(
            f"   Requests sent: {result.requests_sent}, Series: {result.series_sent}, Samples: {result.samples_sent}"
        )
    except Exception as e:
        print(f"❌ [Iteration {iteration}] Error sending metrics: {e}")
        import traceback

        traceback.print_exc()

    print(f"[Iteration {iteration}] Waiting 10 seconds before next batch...")
    print()
    time.sleep(10)
