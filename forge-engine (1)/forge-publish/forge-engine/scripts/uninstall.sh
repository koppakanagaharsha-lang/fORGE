#!/usr/bin/env bash
echo "⚒ FORGE Uninstaller"
systemctl --user stop forge 2>/dev/null || true
systemctl --user disable forge 2>/dev/null || true
pkill -f "remote-debugging-port=9222" 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/forge.service"
systemctl --user daemon-reload 2>/dev/null || true
(crontab -l 2>/dev/null | grep -v "forge") | crontab - 2>/dev/null || true
rm -rf "$HOME/.forge/engine"
echo ""
read -rp "Remove all state, workspace, and credentials? [y/N] " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] && rm -rf "$HOME/.forge" && echo "Removed." || \
  echo "State preserved. Re-install engine to resume."
echo "Done."
