#!/usr/bin/env bash
# FORGE Phantom — start headless Chromium

FORGE_DIR="$HOME/.forge"
BINARY=$(cat "$FORGE_DIR/engine/.browser_binary" 2>/dev/null || echo "chromium")

pkill -f "remote-debugging-port=9222" 2>/dev/null || true
sleep 1

$BINARY \
  --headless \
  --remote-debugging-port=9222 \
  --no-sandbox \
  --disable-gpu \
  --disable-dev-shm-usage \
  --user-data-dir=/tmp/forge-phantom \
  >> "$FORGE_DIR/logs/phantom.log" 2>&1 &

echo "Phantom started: PID $! binary=$BINARY"
