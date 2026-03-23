#!/usr/bin/env bash
# FORGE — Main Runner (systemd entry point)

set -euo pipefail

FORGE_DIR="$HOME/.forge"
ENGINE="$FORGE_DIR/engine"
LOG="$FORGE_DIR/logs/forge.log"
STATE="$FORGE_DIR/state.json"

mkdir -p "$FORGE_DIR/logs"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

source "$FORGE_DIR/.env" 2>/dev/null || true

log "⚡ FORGE starting. PID: $$"

# Start Phantom browser
"$ENGINE/phantom/start.sh" >> "$FORGE_DIR/logs/phantom.log" 2>&1 &
log "Phantom browser start requested"
sleep 3

# Boot sequence
BOOT=$(python3 "$ENGINE/core/boot.py" 2>>"$LOG")
log "Boot: $BOOT"

# Broadcast online
"$ENGINE/relay/broadcast.sh" "boot" "⚡ FORGE online.
Phase: $(echo $BOOT | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()); print(d[\"phase\"])' 2>/dev/null || echo 'research')
Day: $(echo $BOOT | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()); print(d[\"day\"])' 2>/dev/null || echo '1')" &

# ── Main loop ─────────────────────────────────────────────────────────────────
while true; do
  # Poll for commands first
  "$ENGINE/relay/poll.sh" >> "$LOG" 2>&1 || true

  # Run one work cycle
  EXIT=0
  python3 "$ENGINE/core/loop.py" >> "$LOG" 2>&1 || EXIT=$?

  case $EXIT in
    0)   log "Cycle complete" ;;
    42)  log "Rate limit. Sleeping 60s."
         "$ENGINE/relay/broadcast.sh" "rate_limit" \
           "⏸ Rate limit — 60s pause. Resuming after." &
         sleep 60 ;;
    130) log "FORGE interrupted. Exiting cleanly."
         exit 0 ;;
    *)   log "Cycle error: exit $EXIT. Sleeping 30s."
         sleep 30 ;;
  esac

  # Inter-cycle pace
  sleep 8
done
