#!/usr/bin/env bash
# ⚡ FORGE — Engine Installer
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/$FORGE_GITHUB_USER/forge/main/install.sh | bash
#   bash install.sh   (from cloned repo)

set -euo pipefail

FORGE_DIR="$HOME/.forge"
ENGINE="$FORGE_DIR/engine"
GITHUB_USER="${FORGE_GITHUB_USER:-}"
REPO="https://raw.githubusercontent.com/${GITHUB_USER}/forge/main"

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-install.sh}")" 2>/dev/null && pwd || echo "")"
if [ -f "${SELF_DIR}/core/boot.py" ] 2>/dev/null; then
  MODE="local"; SRC="$SELF_DIR"
else
  MODE="remote"; SRC=""
  if [ -z "$GITHUB_USER" ]; then
    echo "Set your GitHub username: export FORGE_GITHUB_USER=your-username"
    exit 1
  fi
fi

echo ""; echo "⚡ FORGE Engine Installer"; echo "══════════════════════════"; echo ""

# ── Directories ───────────────────────────────────────────────────────────────
mkdir -p "$ENGINE"/{core,arena,cortex,keyring,phantom,relay,sentinel,scripts}
mkdir -p "$FORGE_DIR"/{logs,arena} "$HOME/forge-workspace"
echo "✓ Directories"

# ── System dependencies ───────────────────────────────────────────────────────
echo "Checking dependencies..."

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null || \
  sudo apt-get install -y python3.11 python3-pip -qq
PY=$(python3 --version | awk '{print $2}'); echo "  ✓ Python $PY"

pip3 install websocket-client --break-system-packages -q 2>/dev/null || true
echo "  ✓ websocket-client"

if ! node --version 2>/dev/null | grep -qE "v(18|19|20|21|22)"; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - -q
  sudo apt-get install -y nodejs -qq
fi
echo "  ✓ Node $(node --version)"

command -v gh &>/dev/null || (
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
  sudo apt-get update -qq && sudo apt-get install gh -y -qq
)
echo "  ✓ gh"

command -v claw &>/dev/null || npm install -g clawhub-cli -q 2>/dev/null || true
command -v claw &>/dev/null && echo "  ✓ claw" || echo "  ⚠ claw — install from ClawHub dashboard"

command -v opencode &>/dev/null || npm install -g opencode-ai -q 2>/dev/null || true
command -v opencode &>/dev/null && echo "  ✓ opencode" || echo "  ⚠ opencode: npm install -g opencode-ai"

command -v jq &>/dev/null || sudo apt-get install -y jq -qq 2>/dev/null || true

BROWSER=""
for b in chromium chromium-browser google-chrome chrome; do
  command -v $b &>/dev/null && BROWSER=$b && break
done
[ -z "$BROWSER" ] && sudo apt-get install -y chromium-browser -qq 2>/dev/null || true
for b in chromium-browser chromium; do command -v $b &>/dev/null && BROWSER=$b && break; done
[ -n "$BROWSER" ] && echo "  ✓ $BROWSER" || echo "  ⚠ Chromium not found"
echo "$BROWSER" > "$ENGINE/.browser_binary"

# ── Install engine modules ────────────────────────────────────────────────────
echo "Installing engine modules..."

install_file() {
  local rel="$1"
  local dest="$ENGINE/$rel"
  mkdir -p "$(dirname "$dest")"
  if [ "$MODE" = "local" ]; then
    cp "$SRC/$rel" "$dest" 2>/dev/null || { echo "  ⚠ missing: $rel"; return 0; }
  else
    curl -fsSL "$REPO/engine/$rel" -o "$dest" 2>/dev/null || { echo "  ⚠ download failed: $rel"; return 0; }
  fi
  [[ "$dest" == *.sh || "$dest" == *.py ]] && chmod +x "$dest" || true
}

# Core
for f in core/boot.py core/loop.py core/safety.py core/error_recovery.py \
          core/phase_research.py core/phase_ideate.py \
          core/phase_build.py core/phase_maintenance.py; do
  install_file "$f"
done

# Keyring
for f in keyring/keyring.py keyring/rotate.sh keyring/setup_wizard.sh; do
  install_file "$f"
done

# Arena
for f in arena/race.sh arena/judge.py arena/test_harness.sh \
          arena/task_suite.json arena/edge_suite.json; do
  install_file "$f"
done

# Cortex
for f in cortex/invoke.sh cortex/model_select.py \
          cortex/configure.sh cortex/verify.sh; do
  install_file "$f"
done

# Phantom
for f in phantom/cdp.py phantom/cdp.sh phantom/start.sh phantom/detect.sh; do
  install_file "$f"
done

# Relay
for f in relay/broadcast.sh relay/send.sh relay/poll.sh \
          relay/configure_openclaw.sh relay/ping_openclaw.sh; do
  install_file "$f"
done

# Sentinel
for f in sentinel/monitor.sh sentinel/safety_check.py; do
  install_file "$f"
done

# Scripts
for f in scripts/start.sh scripts/stop.sh scripts/status.sh \
          scripts/validate_key.py scripts/install_dep.sh \
          scripts/validate_gemini.py scripts/verify_opencode.sh; do
  install_file "$f"
done

echo "  ✓ Engine modules ($MODE)"

# ── systemd service ───────────────────────────────────────────────────────────
echo "Installing systemd service..."
mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/forge.service" << SERVICE
[Unit]
Description=FORGE — Autonomous AI Developer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$ENGINE/scripts/start.sh
Restart=on-failure
RestartSec=30
StandardOutput=append:$FORGE_DIR/logs/forge.log
StandardError=append:$FORGE_DIR/logs/forge.log

[Install]
WantedBy=default.target
SERVICE

if systemctl --user daemon-reload 2>/dev/null && \
   systemctl --user enable forge.service 2>/dev/null; then
  echo "  ✓ systemd service enabled"
else
  echo "  ⚠ systemd unavailable — cron fallback"
  (crontab -l 2>/dev/null | grep -v "forge/engine"; \
   echo "@reboot $ENGINE/scripts/start.sh >> $FORGE_DIR/logs/forge.log 2>&1") \
   | crontab - 2>/dev/null || true
fi

# ── .env template ─────────────────────────────────────────────────────────────
[ -f "$FORGE_DIR/.env" ] || cat > "$FORGE_DIR/.env" << 'ENV'
# FORGE credentials — filled by setup wizard
# Add multiple keys for rotation: GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.
GEMINI_API_KEY=""
GITHUB_TOKEN=""
GITHUB_USERNAME=""
CLAWHUB_TOKEN=""
CLAWHUB_USERNAME=""
TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHAT_ID=""
OPENCLAW_CALLBACK_URL=""
OPENCODE_MODEL="gemini-2.0-flash"
ENV

# Shell profile
grep -q "forge" ~/.bashrc 2>/dev/null || \
  echo '[ -f ~/.forge/.env ] && source ~/.forge/.env' >> ~/.bashrc
[ -f ~/.zshrc ] && grep -q "forge" ~/.zshrc || \
  echo '[ -f ~/.forge/.env ] && source ~/.forge/.env' >> ~/.zshrc 2>/dev/null || true

# ── Mark installed ─────────────────────────────────────────────────────────────
date -u > "$ENGINE/.installed"

echo ""
echo "⚡ FORGE engine installed."
echo ""
echo "Next:"
echo "  1. Install the FORGE skill from ClawHub"
echo "  2. In OpenClaw or Telegram, say: forge start"
echo ""
echo "Or run key setup now:"
echo "  bash ~/.forge/engine/keyring/setup_wizard.sh"
echo ""
