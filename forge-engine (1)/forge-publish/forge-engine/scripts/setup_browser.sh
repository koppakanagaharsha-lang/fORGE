#!/usr/bin/env bash
FORGE_DIR="$HOME/.forge"
for b in chromium chromium-browser google-chrome chrome; do
  if command -v $b &>/dev/null; then
    echo "$b" > "$FORGE_DIR/engine/.browser_binary"
    echo "Browser: $b"
    exit 0
  fi
done
sudo apt-get install -y chromium-browser -qq 2>/dev/null || \
  sudo snap install chromium 2>/dev/null || true
for b in chromium-browser chromium; do
  command -v $b &>/dev/null && echo "$b" > "$FORGE_DIR/engine/.browser_binary" && exit 0
done
echo "No browser found" >&2; exit 1
