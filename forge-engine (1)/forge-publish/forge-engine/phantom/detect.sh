#!/usr/bin/env bash
# Detect available Chromium binary
for bin in chromium chromium-browser google-chrome chrome; do
  if command -v $bin &>/dev/null; then
    echo "$bin"
    echo "$bin" > "$HOME/.forge/engine/.browser_binary"
    exit 0
  fi
done
echo "missing"
exit 1
