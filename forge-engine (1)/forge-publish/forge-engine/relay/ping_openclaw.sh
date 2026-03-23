#!/usr/bin/env bash
# relay/ping_openclaw.sh — test OpenClaw bridge
FORGE_DIR="$HOME/.forge"
source "$FORGE_DIR/.env" 2>/dev/null || true

URL="${OPENCLAW_CALLBACK_URL:-}"
if [ -z "$URL" ]; then
  echo "no callback URL configured"
  exit 1
fi

RESULT=$(curl -s --max-time 3 -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d '{"event":"ping","message":"FORGE bridge test","timestamp":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"}' \
  2>/dev/null || echo "failed")

echo "$RESULT" | grep -q "ok" && echo "bridge ok" || echo "bridge not responding — Telegram only"
