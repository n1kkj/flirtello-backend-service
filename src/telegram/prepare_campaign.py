import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))


# --- КОНФИГУРАЦИЯ ---

# 1. Вставьте сюда ваш SQL-запрос для выборки данных.
#    Запрос ДОЛЖЕН возвращать следующие колонки:
#    - user_id (str или int): Telegram ID или @username.
#    - user_uuid (str): Внутренний UUID пользователя для трекинга.
SQL_QUERYz = """
-- ПРИМЕР: Выбрать всех пользователей, которым еще не отправляли кампанию 'welcome_2'
-- ЗАМЕНИТЕ ЭТОТ ЗАПРОС НА СВОЙ
SELECT
    u.telegram_id AS user_id,
    u.id AS user_uuid
FROM
    users u
LEFT JOIN
    marketing_events me ON u.id = me.user_id AND me.action = 'campaign_welcome_2_sent'
WHERE
    u.telegram_id IS NOT NULL
    AND me.id IS NULL;
"""

SQL_QUERY = """



"""

# 2. Укажите данные для поста. Они будут одинаковыми для всех пользователей в файле.
POST_URL = "https://t.me/c/2620006618/56"  # URL поста для отправки
BUTTON_TEXT = "Перейти к боту"  # Текст кнопки (оставьте пустым, если не нужна)
BUTTON_URL = "https://t.me/my_bot"  # URL кнопки (оставьте пустым, если не нужна)
CAMPAIGN_TAG = "version_A"  # Метка для A/B тестов или версионирования внутри кампании

# 3. Укажите имя выходного файла.
# Рекомендуется создавать отдельную папку для данных, например, 'data/'
# Убедитесь, что папка существует, или создайте ее.
OUTPUT_FILENAME = "data/campaign_A_data.csv"


def main():
    """
    Инструмент для формирования CSV-файла кампании на основе SQL-запроса.
    """
    # --- Загрузка .env и подключение к БД ---
    load_dotenv(project_root / "src/telegram/.env.telegram")
    load_dotenv(project_root / "src/.env.dev")
    db_url = os.environ.get("DB_URL")
    if not db_url:
        print("Ошибка: DB_URL не найден в переменных окружения.")
        print(f"Убедитесь, что в файле .env.dev в {project_root}/src/ указана переменная DB_URL.")
        return

    # Проверяем, что основной запрос не пустой
    if not SQL_QUERY or SQL_QUERY.isspace():
        print("Ошибка: SQL_QUERY не может быть пустым. Вставьте SQL-запрос в переменную.")
        return

    try:
        engine = create_engine(db_url)
        print("Успешное подключение к базе данных.")
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return

    # --- Шаг 1: Выборка пользователей ---
    print("\n--- Шаг 1: Выборка пользователей ---")
    try:
        with engine.connect() as connection:
            result = connection.execute(text(SQL_QUERY))
            db_rows = result.fetchall()
            db_keys = result.keys()
            print(f"Найдено {len(db_rows)} пользователей для выгрузки.")

            # Проверка, что обязательные колонки есть в запросе
            if "user_id" not in db_keys or "user_uuid" not in db_keys:
                print(
                    "Ошибка: SQL-запрос должен содержать колонки 'user_id' и 'user_uuid'."
                )
                return

            # Формирование заголовков и данных для CSV
            header = ["user_id", "user_uuid", "post_url", "button_text", "button_url", "campaign_tag"]
            csv_rows = []
            for row in db_rows:
                csv_rows.append(
                    [
                        row.user_id,
                        row.user_uuid,
                        POST_URL,
                        BUTTON_TEXT,
                        BUTTON_URL,
                        CAMPAIGN_TAG,
                    ]
                )

            # Сохранение в CSV
            output_path = project_root / OUTPUT_FILENAME
            # Убедимся, что директория для сохранения файла существует
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)  # Записываем заголовки
                writer.writerows(csv_rows)
            print(f"Данные успешно сохранены в: {output_path}")

    except Exception as e:
        print(f"Ошибка при выполнении запроса на выборку: {e}")
        return


if __name__ == "__main__":
    main() 