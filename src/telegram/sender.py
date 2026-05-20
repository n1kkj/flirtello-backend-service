import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Union

from dotenv import load_dotenv

from src.telegram.lib.sender_utils import send_post

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


async def main():
    """
    Главная функция для отправки сообщения в Telegram.
    """
    # Загружаем переменные окружения для получения токена
    # В config.py загружаются именно эти файлы
    load_dotenv(project_root / "src/telegram/.env.telegram")
    load_dotenv(project_root / "src/.env.dev")

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("Ошибка: Переменная окружения TELEGRAM_BOT_TOKEN не найдена.")
        print(
            "Убедитесь, что файлы .env.telegram и .env.dev находятся в нужных директориях."
        )
        return

    parser = argparse.ArgumentParser(
        description="Отправляет сообщение пользователю Telegram от имени бота."
    )
    parser.add_argument(
        "user_id", type=str, help="Telegram ID или @username пользователя."
    )
    parser.add_argument("post_url", type=str, help="URL поста для отправки.")
    parser.add_argument("--button-text", type=str, help="Текст на кнопке.")
    parser.add_argument(
        "--button-url", type=str, help="URL, который откроется по нажатию на кнопку."
    )

    args = parser.parse_args()

    # API может работать и с числовым ID, и с @username.
    # Преобразуем в int, если похоже на число, для чистоты.
    user_id_arg = args.user_id
    if user_id_arg.lstrip("-").isdigit():
        target_id: Union[int, str] = int(user_id_arg)
    else:
        target_id = user_id_arg

    success, message = await send_post(
        user_id=target_id,
        post_url=args.post_url,
        token=bot_token,
        button_text=args.button_text,
        button_url=args.button_url,
    )

    if success:
        print("Сообщение успешно отправлено.")
        print("Ответ от API:", message)
    else:
        print(f"Не удалось отправить сообщение: {message}")


if __name__ == "__main__":
    # httpx использует asyncio, поэтому запускаем main как асинхронную задачу
    asyncio.run(main())
