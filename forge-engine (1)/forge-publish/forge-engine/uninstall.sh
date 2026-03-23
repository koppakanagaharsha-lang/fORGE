#!/usr/bin/env bash
# FORGE — Uninstaller

set -euo pipefail

echo ""
echo "⚡ FORGE — Uninstaller"
echo "======================="
echo ""

bash "$HOME/.forge/engine/scripts/stop.sh" 2>/dev/null || true

systemctl --user disable forge 2>/dev/null && \
  echo "✓ Service disabled" || true
rm -f "$HOME/.config/systemd/user/forge.service"
systemctl --user daemon-reload 2>/dev/null || true

(crontab -l 2>/dev/null | grep -v "forge/engine") | crontab - 2>/dev/null || true

rm -rf "$HOME/.forge/engine"
echo "✓ Engine removed"

echo ""
read -rp "Remove all FORGE state, logs, and credentials (~/.forge/)? [y/N] " C
if [[ "$C" =~ ^[Yy]$ ]]; then
  rm -rf "$HOME/.forge"
  echo "✓ All FORGE data removed"
else
  echo "— State preserved at ~/.forge/"
  echo "  Re-install engine to resume: curl -fsSL https://raw.githubusercontent.com/$FORGE_GITHUB_USER/forge/main/install.sh | bash"
fi

echo ""
echo "FORGE uninstalled."
echo "Remove the skill from OpenClaw's skill manager to complete removal."
