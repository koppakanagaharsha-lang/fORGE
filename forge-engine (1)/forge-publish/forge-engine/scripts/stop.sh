#!/usr/bin/env bash
# FORGE — Stop
systemctl --user stop forge 2>/dev/null || \
  pkill -f "forge/engine/scripts/start.sh" 2>/dev/null || true
pkill -f "remote-debugging-port=9222" 2>/dev/null || true
echo "FORGE stopped."
