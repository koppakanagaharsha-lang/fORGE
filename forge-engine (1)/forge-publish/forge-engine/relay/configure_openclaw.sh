#!/usr/bin/env bash
# relay/configure_openclaw.sh — set up OpenClaw callback URL

FORGE_DIR="$HOME/.forge"
source "$FORGE_DIR/.env" 2>/dev/null || true

# Try to detect OpenClaw's local API
OPENCLAW_PORT="${OPENCLAW_PORT:-7823}"
CALLBACK_URL="http://localhost:${OPENCLAW_PORT}/api/forge/event"

# Test if OpenClaw is listening
if curl -s --max-time 2 "http://localhost:${OPENCLAW_PORT}/api/health" \
   > /dev/null 2>&1; then
  grep -q "OPENCLAW_CALLBACK_URL" "$FORGE_DIR/.env" 2>/dev/null || \
    echo "OPENCLAW_CALLBACK_URL=\"$CALLBACK_URL\"" >> "$FORGE_DIR/.env"
  echo "OpenClaw bridge configured: $CALLBACK_URL"
else
  echo "OpenClaw not detected on port $OPENCLAW_PORT — bridge will retry on next boot"
  echo "OPENCLAW_CALLBACK_URL=\"$CALLBACK_URL\"" >> "$FORGE_DIR/.env"
fi
