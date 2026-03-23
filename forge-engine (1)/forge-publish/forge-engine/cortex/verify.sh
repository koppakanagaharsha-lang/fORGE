#!/usr/bin/env bash
# cortex/verify.sh — verify opencode is installed and working
VERSION=$(opencode --version 2>/dev/null | head -1 || echo "")
if [ -n "$VERSION" ]; then
  echo "found:$VERSION"
  exit 0
else
  echo "missing"
  exit 1
fi
