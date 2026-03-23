#!/usr/bin/env bash
# relay/send.sh — send a Telegram message
# Usage: send.sh [bot_token] [chat_id] [message]
TOKEN="${1:-$TELEGRAM_BOT_TOKEN}"
CHAT="${2:-$TELEGRAM_CHAT_ID}"
MSG="${3:-}"
curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT}" \
  --data-urlencode "text=${MSG}" \
  --data-urlencode "parse_mode=Markdown" \
  > /dev/null
