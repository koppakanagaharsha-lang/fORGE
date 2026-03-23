#!/usr/bin/env bash
FORGE_DIR="$HOME/.forge"
LOG="$FORGE_DIR/logs/forge.log"
systemctl --user start forge 2>/dev/null && echo "Started via systemd" && exit 0
mkdir -p "$FORGE_DIR/logs"
nohup "$FORGE_DIR/engine/scripts/runner.sh" >> "$LOG" 2>&1 &
echo $! > "$FORGE_DIR/runner.pid"
echo "Started via nohup PID $!"
(crontab -l 2>/dev/null | grep -v "forge"; \
 echo "@reboot $FORGE_DIR/engine/scripts/runner.sh >> $LOG 2>&1") | crontab -
echo "Cron persistence added"
