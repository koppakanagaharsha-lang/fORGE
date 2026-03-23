#!/usr/bin/env bash
# FORGE Relay — broadcast to Telegram AND OpenClaw simultaneously
# Usage: broadcast.sh [event_type] [message]

EVENT="${1:-status}"
MESSAGE="${2:-FORGE update}"
FORGE_DIR="$HOME/.forge"
KEYRING="$FORGE_DIR/engine/keyring/keyring.py"

source "$FORGE_DIR/.env" 2>/dev/null || true

# ── Get active Telegram token from keyring ────────────────────────────────────
TGTOKEN=$(python3 - << 'PY' 2>/dev/null
import sys, os
sys.path.insert(0, os.path.expanduser('~') + '/.forge/engine/keyring')
try:
    from keyring import get_keyring
    key = get_keyring().get_key('telegram')
    print(key or '')
except Exception:
    print(os.environ.get('TELEGRAM_BOT_TOKEN', ''))
PY
)
# Fallback to env var
TGTOKEN="${TGTOKEN:-$TELEGRAM_BOT_TOKEN}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# ── Telegram ─────────────────────────────────────────────────────────────────
if [ -n "${TGTOKEN:-}" ] && [ -n "${CHAT_ID:-}" ]; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    "https://api.telegram.org/bot${TGTOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${MESSAGE}" \
    --data-urlencode "parse_mode=Markdown" 2>/dev/null || echo "0")

  # If rate limited, cool this token and retry with next
  if [ "$HTTP_CODE" = "429" ]; then
    python3 "$KEYRING" report telegram "$TGTOKEN" 2>/dev/null || true
    TGTOKEN2=$(python3 - << 'PY' 2>/dev/null
import sys, os
sys.path.insert(0, os.path.expanduser('~') + '/.forge/engine/keyring')
try:
    from keyring import get_keyring
    print(get_keyring().get_key('telegram') or '')
except Exception:
    print('')
PY
)
    if [ -n "$TGTOKEN2" ]; then
      curl -s "https://api.telegram.org/bot${TGTOKEN2}/sendMessage" \
        --data-urlencode "chat_id=${CHAT_ID}" \
        --data-urlencode "text=${MESSAGE}" \
        --data-urlencode "parse_mode=Markdown" \
        > /dev/null 2>&1 &
    fi
  fi
fi &

# ── OpenClaw callback ─────────────────────────────────────────────────────────
OPENCLAW_CALLBACK="${OPENCLAW_CALLBACK_URL:-}"
if [ -n "$OPENCLAW_CALLBACK" ]; then
  curl -s -X POST "$OPENCLAW_CALLBACK" \
    -H "Content-Type: application/json" \
    -d "{\"event\":\"$EVENT\",\"message\":$(echo "$MESSAGE" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))'),\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
    > /dev/null 2>&1 &
fi

# ── Local event log ───────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$EVENT] $MESSAGE" >> "$FORGE_DIR/logs/events.log"

wait
