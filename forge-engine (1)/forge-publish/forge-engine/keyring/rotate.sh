#!/usr/bin/env bash
# FORGE Keyring — shell interface
# Usage:
#   source rotate.sh                    # load helpers into current shell
#   rotate.sh get gemini                # print an available Gemini key
#   rotate.sh status                    # print full keyring status
#   rotate.sh add gemini <key> [label]  # add a new key
#   rotate.sh report gemini <key>       # mark key as rate-limited

FORGE_DIR="$HOME/.forge"
KEYRING="$FORGE_DIR/engine/keyring/keyring.py"

# ── Shell functions (used when sourced) ───────────────────────────────────────

forge_get_key() {
  local service="${1:-gemini}"
  python3 "$KEYRING" get "$service" 2>/dev/null | grep -oP 'key:\K[^ ]+' || echo ""
}

forge_get_full_key() {
  # Returns the actual full key value (use carefully — key is printed to stdout)
  local service="${1:-gemini}"
  python3 - "$service" << 'PY'
import sys
sys.path.insert(0, __import__('pathlib').Path.home().__str__() + '/.forge/engine/keyring')
from keyring import get_keyring
kr = get_keyring()
key = kr.get_key(sys.argv[1])
print(key or "")
PY
}

forge_report_ratelimit() {
  local service="${1:-gemini}"
  local key="${2:-}"
  python3 "$KEYRING" report "$service" "$key" 2>/dev/null || true
}

forge_key_available() {
  local service="${1:-gemini}"
  python3 "$KEYRING" get "$service" > /dev/null 2>&1
}

# ── Direct invocation ─────────────────────────────────────────────────────────
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  CMD="${1:-status}"
  shift 2>/dev/null || true
  python3 "$KEYRING" "$CMD" "$@"
fi
