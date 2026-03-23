#!/usr/bin/env bash
# FORGE Sentinel — monitors arena forks and runaway processes
# Runs as a background check each cycle

FORGE_DIR="$HOME/.forge"
ARENA_DIR="$FORGE_DIR/arena"
LOG="$FORGE_DIR/logs/sentinel.log"

log() { echo "[SENTINEL $(date '+%H:%M:%S')] $*" >> "$LOG"; }

# Kill arena forks older than 30 minutes (race hung)
if [ -d "$ARENA_DIR" ]; then
  find "$ARENA_DIR" -maxdepth 1 -name "fork_*" -type d -mmin +30 | while read fork; do
    log "Killing stale fork: $fork"
    rm -rf "$fork"
    "$FORGE_DIR/engine/relay/broadcast.sh" "sentinel" \
      "🛡 Sentinel: stale arena fork removed ($(basename $fork))" &
  done
fi

# Check runner memory (kill if > 2GB RSS)
RUNNER_PID=$(pgrep -f "forge/engine/scripts/start.sh" | head -1 || echo "")
if [ -n "$RUNNER_PID" ]; then
  RSS=$(ps -o rss= -p "$RUNNER_PID" 2>/dev/null || echo "0")
  RSS_MB=$((RSS / 1024))
  if [ "$RSS_MB" -gt 2048 ]; then
    log "Runner memory $RSS_MB MB exceeds limit — restarting"
    systemctl --user restart forge 2>/dev/null || \
      kill "$RUNNER_PID" 2>/dev/null || true
    "$FORGE_DIR/engine/relay/broadcast.sh" "sentinel" \
      "🛡 Sentinel: runner restarted (memory limit)" &
  fi
fi

# Ensure only one runner is active
RUNNER_COUNT=$(pgrep -fc "forge/engine/scripts/start.sh" 2>/dev/null || echo "0")
if [ "$RUNNER_COUNT" -gt 1 ]; then
  log "Multiple runners detected ($RUNNER_COUNT) — killing extras"
  pgrep -f "forge/engine/scripts/start.sh" | tail -n +2 | xargs kill 2>/dev/null || true
fi

log "Sentinel check complete"
