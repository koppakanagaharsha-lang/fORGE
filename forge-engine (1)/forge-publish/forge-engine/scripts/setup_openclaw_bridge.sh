#!/usr/bin/env bash
FORGE_DIR="$HOME/.forge"
# Create named pipe for OpenClaw bridge
PIPE="$FORGE_DIR/.openclaw_pipe"
[ -p "$PIPE" ] || mkfifo "$PIPE"
echo "OpenClaw bridge pipe: $PIPE"
# Configure OpenClaw to read from this pipe
if command -v openclaw &>/dev/null; then
  openclaw config set forge.bridge_pipe "$PIPE" 2>/dev/null || true
fi
echo "bridge_pipe=\"$PIPE\"" >> "$FORGE_DIR/.env"
echo "OpenClaw bridge configured"
