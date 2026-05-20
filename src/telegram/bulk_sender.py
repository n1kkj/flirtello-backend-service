import argparse
import asyncio
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

# Добавляем корневую директорию проекта в sys.path
# Это нужно, чтобы можно было импортировать модули из src
# __file__ -> /path/to/flirtello-backend-service/src/telegram/bulk_sender.py
# Path(__file__).resolve().parent.parent.parent -> /path/to/flirtello-backend-service
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv

from src.telegram.lib.sender_utils import send_marketing_event, send_post


def read_tasks_from_csv(file_path: Path) -> list[dict[str, str]]:
    """Читает задачи из CSV файла."""
    if not file_path.exists():
        return []
    tasks = []
    with open(file_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(row)
    return tasks


def write_results_to_csv(
    file_path: Path, results: list[dict[str, Any]], fieldnames: list[str]
):
    """Атомарно записывает результаты в CSV файл."""
    temp_file_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
    with open(temp_file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    os.replace(temp_file_path, file_path)


async def main():
    """
    Главная функция для массовой отправки сообщений в Telegram.
    """
    # --- Загрузка .env ---
    load_dotenv(project_root / "src/telegram/.env.telegram")
    load_dotenv(project_root / "src/.env.dev")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    mkt_collector_url = os.environ.get("MKT_COLLECTOR_URL")
    mkt_collector_api_key = os.environ.get("MKT_COLLECTOR_API_KEY")

    # --- Отладочная информация ---
    print("\n--- Отладочная информация для MKT Collector ---")
    if mkt_collector_url:
        print(f"URL коллектора: {mkt_collector_url}")
    else:
        print("URL коллектора: НЕ НАЙДЕН")
    if mkt_collector_api_key:
        key_preview = f"{mkt_collector_api_key[:4]}...{mkt_collector_api_key[-4:]}"
        print(f"Ключ API: {key_preview} (длина: {len(mkt_collector_api_key)})")
    else:
        print("Ключ API: НЕ НАЙДЕН")
    print("------------------------------------------------\n")

    if not all([bot_token, mkt_collector_url, mkt_collector_api_key]):
        print("Ошибка: Не найдены все необходимые переменные окружения.")
        return

    if not mkt_collector_url or not mkt_collector_api_key:
        print(
            "Внимание: MKT_COLLECTOR_URL или MKT_COLLECTOR_API_KEY не найдены в .env файлах."
        )
        print("События в маркетинговую систему отправляться не будут.")

    parser = argparse.ArgumentParser(
        description="Массово отправляет посты пользователям Telegram по списку из CSV.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "csv_path",
        type=str,
        help="Путь к CSV файлу с задачами.\nОбязательные колонки: telegram_id, user_id, post_url.\nНеобязательные: button_text, button_url, campaign_tag.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1,
        help="Задержка между отправками в секундах (по-умолчанию: 1).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Запустить скрипт в тестовом режиме без реальной отправки сообщений и событий.",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("\n" + "=" * 40)
        print("!!!     РЕЖИМ ТЕСТОВОГО ЗАПУСКА      !!!")
        print("!!! (DRY-RUN) - ОТПРАВКИ НЕ БУДЕТ  !!!")
        print("!!!  ФАЙЛ РЕЗУЛЬТАТОВ ИЗМЕНЕН НЕ БУДЕТ !!!")
        print("=" * 40 + "\n")

    input_file_path = Path(args.csv_path)
    output_file_path = (
        input_file_path.parent / f"{input_file_path.stem}_results.csv"
    )

    if not input_file_path.exists():
        print(f"Ошибка: Входной файл не найден: {input_file_path}")
        return

    # --- Чтение и подготовка задач ---
    # `all_tasks` - это оригинальный список из CSV, который мы не меняем.
    # `tasks_to_process` - это рабочая копия, которую мы будем обновлять статусами.
    all_tasks = read_tasks_from_csv(input_file_path)
    if not all_tasks:
        print(f"Входной файл {input_file_path} пуст или некорректен.")
        return

    # Определяем поля для CSV из первой задачи
    base_fieldnames = list(all_tasks[0].keys())
    # Добавляем поля для статусов, если их еще нет
    result_fieldnames = base_fieldnames[:]
    status_fields = [
        "message_sent_at",
        "message_status",
        "event_sent_at",
        "event_status",
    ]
    for field in status_fields:
        if field not in result_fieldnames:
            result_fieldnames.append(field)

    tasks_to_process = []
    # --- Логика идемпотентности: читаем состояние из файла результатов, если он есть ---
    if output_file_path.exists():
        print(f"Найден файл с результатами: {output_file_path}. Загружаем состояние...")
        processed_tasks = read_tasks_from_csv(output_file_path)
        
        # Для быстрого доступа создаем словарь состояний по user_id (UUID)
        processed_map = {task["user_id"]: task for task in processed_tasks}
        
        for task in all_tasks:
            # Копируем исходную задачу, чтобы не изменять all_tasks
            task_copy = task.copy()
            if task_copy["user_id"] in processed_map:
                # Если задача уже была обработана, переносим ее статусы
                previous_state = processed_map[task_copy["user_id"]]
                task_copy.update(previous_state)
            tasks_to_process.append(task_copy)
        print(f"Загружено {len(tasks_to_process)} задач для проверки.")

    else:
        # Первый запуск: просто копируем все задачи
        tasks_to_process = [task.copy() for task in all_tasks]
        print(f"Файл с результатами не найден. Будет создан новый: {output_file_path}")

    if not tasks_to_process:
        print("В файле нет задач для обработки.")
        return

    print(f"Всего задач для обработки: {len(tasks_to_process)}")

    for i, task in enumerate(tasks_to_process):
        print(f"--- Обработка задачи {i+1}/{len(tasks_to_process)} (ID: {task.get('user_id')}) ---")

        # Пропускаем уже полностью выполненные задачи
        if (
            task.get("message_status") == "ok"
            and task.get("event_status") in ("ok", "skipped")
        ):
            print("-> Статус: Полностью выполнена. Пропуск.")
            continue

        # Шаг 0: Валидация задачи
        user_id = task.get("user_id") # Это UUID
        telegram_id = task.get("telegram_id")
        post_url = task.get("post_url")

        if not all([user_id, telegram_id, post_url]):
            task["message_status"] = "error: missing required fields"
            print("-> Ошибка: в задаче не хватает user_id, telegram_id или post_url.")
            if not args.dry_run:
                write_results_to_csv(output_file_path, tasks_to_process, result_fieldnames)
            continue

        # Безопасно извлекаем опциональные параметры
        button_text = task.get("button_text", "").strip() or None
        button_url = task.get("button_url", "").strip() or None
        campaign_tag = task.get("campaign_tag", "").strip() or None

        # Шаг 1: Отправка поста в Telegram
        if task.get("message_status") != "ok":
            print("-> Попытка отправки поста...")

            if args.dry_run:
                print(f" > [DRY-RUN] Пропуск реальной отправки поста для telegram_id: {telegram_id}.")
                print(f"   - Post URL: {post_url}")
                if button_text:
                    print(f"   - Button: '{button_text}' -> {button_url}")
                if campaign_tag:
                    print(f"   - Campaign Tag: {campaign_tag}")
                msg_success, msg_message = True, "ok (dry-run)"
            else:
                assert bot_token is not None  # Подсказка для mypy
                assert telegram_id is not None  # Подсказка для mypy, т.к. выше есть проверка
                assert post_url is not None  # Подсказка для mypy, т.к. выше есть проверка
                msg_success, msg_message = await send_post(
                    telegram_id, post_url, bot_token, button_text, button_url
                )

            if msg_success:
                print(" > Успешно отправлено.")
                task["message_status"] = "ok"
                task["message_sent_at"] = pd.Timestamp.now(tz="UTC").isoformat()
            else:
                print(f" > Ошибка отправки: {msg_message}")
                # --- Улучшенная обработка ошибок ---
                error_text = str(msg_message)
                if isinstance(msg_message, httpx.HTTPStatusError):
                    try:
                        # Пытаемся извлечь осмысленное описание от Telegram
                        error_data = msg_message.response.json()
                        error_text = error_data.get("description", msg_message.response.text)
                    except json.JSONDecodeError:
                        # Если тело ответа не JSON, используем текстовое представление
                        error_text = msg_message.response.text
                
                task["message_status"] = error_text
                # Если не удалось отправить сообщение, нет смысла отправлять mkt событие
                if not args.dry_run:
                    write_results_to_csv(output_file_path, tasks_to_process, result_fieldnames)
                if i < len(tasks_to_process) - 1:
                    await asyncio.sleep(args.delay)
                continue  # Переходим к следующей задаче

        # Шаг 2: Отправка события в MKT-коллектор
        if task.get("message_status") == "ok" and task.get("event_status") != "ok":
            if not mkt_collector_url or not mkt_collector_api_key:
                task["event_status"] = "skipped"
                print("-> Статус: MKT событие пропущено (нет ключей).")
            elif args.dry_run:
                source_campaign = input_file_path.stem.replace("_results", "")
                mkt_params = {
                    "source_campaign": source_campaign,
                    "post_url": post_url,
                    "button_text": button_text or "",
                    "button_url": button_url or "",
                }
                if campaign_tag:
                    mkt_params["campaign_tag"] = campaign_tag

                print(f"-> [DRY-RUN] Попытка отправки события в MKT для user_id: {user_id}...")
                print("   - Event: tg_post_sent")
                print(f"   - Params: {json.dumps(mkt_params, indent=4)}")
                print(" > MKT событие успешно отправлено (dry-run).")
                task["event_status"] = "ok"
                task["event_sent_at"] = pd.Timestamp.now(tz="UTC").isoformat()
            else:
                print("-> Попытка отправки события в MKT...")
                # Убираем расширение .csv из имени кампании для чистоты данных
                source_campaign = input_file_path.stem.replace("_results", "")

                mkt_params = {
                    "source_campaign": source_campaign,
                    "post_url": post_url,
                    "button_text": button_text or "",
                    "button_url": button_url or "",
                }
                if campaign_tag:
                    mkt_params["campaign_tag"] = campaign_tag

                assert user_id is not None  # Добавляем assert для mypy
                mkt_success, mkt_message = await send_marketing_event(
                    mkt_collector_url,
                    mkt_collector_api_key,
                    user_id,
                    "tg_post_sent",
                    mkt_params,
                    retries=3,  # Можно вынести в аргументы, если нужна гибкость
                    retry_delay=5,
                )
                if mkt_success:
                    print(" > MKT событие успешно отправлено.")
                    task["event_status"] = "ok"
                    task["event_sent_at"] = pd.Timestamp.now(tz="UTC").isoformat()
                else:
                    print(f" > Ошибка MKT события: {mkt_message}")
                    task["event_status"] = str(mkt_message)

        # Атомарно записываем результат после каждой задачи
        if not args.dry_run:
            write_results_to_csv(output_file_path, tasks_to_process, result_fieldnames)

        # Задержка перед следующей задачей
        if i < len(tasks_to_process) - 1:
            await asyncio.sleep(args.delay)

    print("\n--- Рассылка завершена! ---")


if __name__ == "__main__":
    asyncio.run(main()) 