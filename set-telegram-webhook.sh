#!/usr/bin/env bash
set -euo pipefail

# This script configures the Telegram bot webhook and menu button using URLs from environment variables.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

cd "$REPO_ROOT"

# Загружаем переменные из .env, если он существует
if [ -f "src/.env" ]; then
  echo "Загрузка переменных из src/.env"
  source "src/.env"
fi

# Проверяем наличие необходимых переменных
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "TELEGRAM_BOT_TOKEN не найден. Укажите токен в src/.env" >&2
  exit 1
fi

if [[ -z "${TELEGRAM_WEBHOOK_URL:-}" ]]; then
  echo "TELEGRAM_WEBHOOK_URL не найден. Укажите URL вебхука в переменных окружения или в src/.env" >&2
  exit 1
fi

if [[ -z "${TELEGRAM_WEBAPP_URL:-}" ]]; then
  echo "TELEGRAM_WEBAPP_URL не найден. Укажите URL веб-приложения в переменных окружения или в src/.env" >&2
  exit 1
fi

# --- 1. Настройка Webhook ---
echo "Удаляю старый вебхук..."
curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/deleteWebhook"

echo
echo "Устанавливаю новый вебхук на ${TELEGRAM_WEBHOOK_URL}"
curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${TELEGRAM_WEBHOOK_URL}\",
    \"allowed_updates\": [\"message\", \"edited_message\", \"channel_post\", \"edited_channel_post\", \"inline_query\", \"chosen_inline_result\", \"callback_query\", \"shipping_query\", \"pre_checkout_query\", \"poll\", \"poll_answer\", \"my_chat_member\", \"chat_member\", \"chat_join_request\"]
  }"

echo
echo "Проверяю информацию о вебхуке..."
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
echo
echo "--- Вебхук настроен ---"
echo

# --- 2. Настройка Menu Button (WebApp) ---

# # Сохраняем публичный URL веб‑приложения для локального переопределения в коде
# echo "${TELEGRAM_WEBAPP_URL}" > src/telegram/.webappurl
# echo "Сохранил URL веб-приложения в src/telegram/.webappurl"

# Формируем payload для setChatMenuButton c MenuButtonWebApp
read -r -d '' PAYLOAD <<EOF || true
{
  "menu_button": {
    "type": "web_app",
    "text": "Open App",
    "web_app": {"url": "${TELEGRAM_WEBAPP_URL}"}
  }
}
EOF

echo "Устанавливаю MenuButtonWebApp на ${TELEGRAM_WEBAPP_URL}"
curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setChatMenuButton" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"

echo
echo "Проверяю текущее меню..."
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getChatMenuButton"
echo
echo "--- Кнопка меню настроена ---"
echo
echo "Готово."
