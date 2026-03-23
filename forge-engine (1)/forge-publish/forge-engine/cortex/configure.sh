#!/usr/bin/env bash
# cortex/configure.sh — configure opencode to use Gemini

FORGE_DIR="$HOME/.forge"
source "$FORGE_DIR/.env" 2>/dev/null || true

# Write opencode config pointing at Gemini
mkdir -p "$HOME/.config/opencode"
cat > "$HOME/.config/opencode/config.json" << EOF
{
  "provider": "google",
  "model": "gemini-2.0-flash",
  "apiKey": "${GEMINI_API_KEY:-}"
}
EOF

# Also set via env in .env if not already set
grep -q "OPENCODE_MODEL" "$FORGE_DIR/.env" 2>/dev/null || \
  echo 'OPENCODE_MODEL="gemini-2.0-flash"' >> "$FORGE_DIR/.env"

echo "Cortex configured: opencode → gemini-2.0-flash"
