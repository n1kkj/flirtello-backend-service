#!/usr/bin/env bash
set -euo pipefail

# This script starts ngrok for the Telegram bot webhook and then configures the webhook
# using the existing script at src/telegram/install-ngrok-webhook.
# It keeps ngrok running in the foreground (via wait) and cleans it up on Ctrl+C.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
TELEGRAM_DIR="$REPO_ROOT/src/telegram"

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok не найден в $PATH. Установите ngrok и попробуйте снова." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl не найден. Установите curl и попробуйте снова." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq не найден. Установите jq (например, brew install jq) и попробуйте снова." >&2
  exit 1
fi

cd "$TELEGRAM_DIR"

echo "Запускаю ngrok: ngrok start --config ngrok.yml botwebhook webapp"
ngrok start --config ngrok.yml botwebhook webapp &
NGROK_PID=$!

cleanup() {
  echo "Останавливаю ngrok (PID $NGROK_PID)..."
  kill "$NGROK_PID" >/dev/null 2>&1 || true
  wait "$NGROK_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "Жду поднятия туннелей ngrok (botwebhook, webapp)..."
BOTWEBHOOK_URL=""
WEBAPP_URL=""
for i in {1..60}; do
  if curl -sf localhost:4040/api/tunnels >/dev/null 2>&1; then
    BOTWEBHOOK_URL=$(curl -s localhost:4040/api/tunnels | jq -r '.tunnels[] | select(.name=="botwebhook") | .public_url') || true
    WEBAPP_URL=$(curl -s localhost:4040/api/tunnels | jq -r '.tunnels[] | select(.name=="webapp") | .public_url') || true
    if [[ -n "${BOTWEBHOOK_URL}" && "${BOTWEBHOOK_URL}" != "null" && -n "${WEBAPP_URL}" && "${WEBAPP_URL}" != "null" ]]; then
      echo "Туннели готовы: botwebhook=${BOTWEBHOOK_URL}, webapp=${WEBAPP_URL}"
      break
    fi
  fi
  sleep 1
done

if [[ -z "${BOTWEBHOOK_URL}" || "${BOTWEBHOOK_URL}" == "null" ]]; then
  echo "Не удалось дождаться запуска туннеля ngrok botwebhook." >&2
  exit 1
fi
if [[ -z "${WEBAPP_URL}" || "${WEBAPP_URL}" == "null" ]]; then
  echo "Не удалось дождаться запуска туннеля ngrok webapp." >&2
  exit 1
fi

echo "Настраиваю Telegram webhook..."
cd "$REPO_ROOT"
"$REPO_ROOT/src/telegram/install-ngrok-webhook"

echo "Готово. Нажмите Ctrl+C для остановки ngrok."

# Убираем EXIT из ловушки, чтобы не убивать ngrok дважды, и ждём процесс
trap - EXIT
wait "$NGROK_PID"


