#!/usr/bin/env bash
# FORGE Keyring — Interactive setup wizard
# Called during first-run setup and via: forge keys add
# Guides user to add multiple keys for rotation

FORGE_DIR="$HOME/.forge"
KEYRING_PY="$FORGE_DIR/engine/keyring/keyring.py"
ENV_FILE="$FORGE_DIR/.env"

source "$FORGE_DIR/engine/keyring/rotate.sh"

echo ""
echo "⚡ FORGE Keyring Setup"
echo "═══════════════════════"
echo ""
echo "FORGE rotates between multiple API keys automatically."
echo "When one hits a rate limit, it switches to the next — no interruption."
echo ""
echo "You can add as many keys as you want. More keys = longer uninterrupted runtime."
echo "At minimum, one key per service is required."
echo ""

add_keys_for_service() {
  local service="$1"
  local prompt="$2"
  local env_prefix="$3"
  local validate_cmd="$4"

  echo "── $service ───────────────────────────────────────"

  # Show existing keys
  local existing=$(python3 "$KEYRING_PY" counts "$service" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['total'])" 2>/dev/null || echo "0")
  echo "  Current keys: $existing"
  echo ""

  local key_num=$((existing + 1))
  while true; do
    read -rp "  $prompt (key $key_num, or Enter to skip): " KEY
    KEY=$(echo "$KEY" | tr -d '[:space:]')
    [ -z "$KEY" ] && break

    # Validate
    if [ -n "$validate_cmd" ]; then
      echo -n "  Validating... "
      RESULT=$(eval "$validate_cmd '$KEY'" 2>/dev/null || echo "error")
      if echo "$RESULT" | grep -q "valid\|ok\|found"; then
        echo "✓"
      else
        echo "✗ ($RESULT)"
        read -rp "  Add anyway? [y/N] " FORCE
        [[ "$FORCE" =~ ^[Yy]$ ]] || continue
      fi
    fi

    # Add to keyring
    python3 "$KEYRING_PY" add "$service" "$KEY" "${service}-${key_num}" 2>/dev/null
    echo "  ✓ Added ${service}-${key_num}"
    key_num=$((key_num + 1))

    read -rp "  Add another $service key? [y/N] " MORE
    [[ "$MORE" =~ ^[Yy]$ ]] || break
  done
  echo ""
}

# Gemini keys
add_keys_for_service \
  "gemini" \
  "Gemini API key (from aistudio.google.com)" \
  "GEMINI_API_KEY" \
  "python3 $FORGE_DIR/engine/scripts/validate_key.py gemini"

# GitHub tokens
add_keys_for_service \
  "github" \
  "GitHub token (from github.com/settings/tokens)" \
  "GITHUB_TOKEN" \
  "python3 $FORGE_DIR/engine/scripts/validate_key.py github"

# ClawHub tokens
add_keys_for_service \
  "clawhub" \
  "ClawHub token (from clawhub.dev dashboard)" \
  "CLAWHUB_TOKEN" \
  ""

# Print final status
echo ""
python3 "$KEYRING_PY" status
echo ""
echo "✓ Keyring configured. FORGE will rotate keys automatically."
echo ""
echo "To add more keys later: forge keys add"
