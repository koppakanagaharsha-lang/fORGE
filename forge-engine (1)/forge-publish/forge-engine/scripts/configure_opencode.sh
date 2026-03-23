#!/usr/bin/env bash
source "$HOME/.forge/.env" 2>/dev/null || true
# Configure opencode to use Gemini
mkdir -p "$HOME/.config/opencode"
cat > "$HOME/.config/opencode/config.json" << CONF
{
  "provider": "google",
  "model": "gemini-2.0-flash",
  "apiKey": "${GEMINI_API_KEY}"
}
CONF
echo "opencode configured with Gemini"
# Store available models
opencode models list 2>/dev/null | python3 -c "
import sys, json
models = [l.strip() for l in sys.stdin if l.strip()]
with open('$HOME/.forge/ledger/opencode_models.json','w') as f:
  json.dump(models, f, indent=2)
print(f'{len(models)} models stored')
" 2>/dev/null || echo "[]" > "$HOME/.forge/ledger/opencode_models.json"
