#!/usr/bin/env bash
# FORGE — Main Runner
# The persistent loop. Kept alive by systemd.
# Sources the kernel. Starts all subsystems. Runs indefinitely.

set -euo pipefail

FORGE_DIR="$HOME/.forge"
ENGINE_DIR="$FORGE_DIR/engine"
LOG="$FORGE_DIR/logs/forge.log"

mkdir -p "$FORGE_DIR/logs"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [FORGE] $*" | tee -a "$LOG"; }

# Source environment and kernel
[ -f "$FORGE_DIR/.env" ] && source "$FORGE_DIR/.env"
source "$ENGINE_DIR/core/kernel.sh"

log "FORGE igniting. PID: $$"
log "Generation: $(forge_get evolution_generation)"

# ── Start subsystems ─────────────────────────────────────────────────────────

# Bellows — headless browser
bash "$ENGINE_DIR/bellows/start.sh" >> "$FORGE_DIR/logs/bellows.log" 2>&1 &
log "Bellows (browser) started"

# Herald — Telegram command poller
bash "$ENGINE_DIR/herald/poll_commands.sh" >> "$FORGE_DIR/logs/herald.log" 2>&1 &
HERALD_PID=$!
log "Herald (commands) started PID $HERALD_PID"

# Trap for clean shutdown
cleanup() {
  log "FORGE shutting down cleanly..."
  forge_set phase "\"$(forge_get phase)\""  # persist current phase
  kill $HERALD_PID 2>/dev/null || true
  pkill -f "remote-debugging-port=9222" 2>/dev/null || true
  log "Shutdown complete. State preserved."
  exit 0
}
trap cleanup SIGTERM SIGINT

# ── Check setup completion ────────────────────────────────────────────────────
SETUP=$(forge_get setup_complete)
if [ "$SETUP" != "true" ]; then
  log "Setup not complete. Waiting for wizard..."
  while [ "$(forge_get setup_complete)" != "true" ]; do
    sleep 10
  done
  log "Setup complete. Beginning main loop."
fi

# ── Main loop ────────────────────────────────────────────────────────────────
CYCLE_COUNT=0

while true; do
  PHASE=$(forge_get phase)
  PROJECTS=$(forge_get projects_today)
  DAY=$(forge_get day)
  GEN=$(forge_get evolution_generation)

  log "Cycle $CYCLE_COUNT — Gen:$GEN Day:$DAY Phase:$PHASE Projects:$PROJECTS/$(forge_get daily_target)"

  # Check if paused
  if [ "$PHASE" = "paused" ]; then
    log "Paused. Polling for /resume..."
    sleep 15
    continue
  fi

  # Update timestamp
  forge_set last_active "\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\""

  # Check mutation schedule (every 10 cycles)
  if (( CYCLE_COUNT > 0 && CYCLE_COUNT % 10 == 0 )); then
    log "Scheduled mutation check (cycle $CYCLE_COUNT)..."
    # Pick least-recently-mutated tier-1 component
    bash "$ENGINE_DIR/crucible/mutate.sh" \
      "bellows/research.sh" "scheduled_evolution" \
      >> "$FORGE_DIR/logs/crucible.log" 2>&1 &
  fi

  # Invoke OpenClaw for one work cycle
  EXIT_CODE=0
  if command -v openclaw &>/dev/null; then
    openclaw run forge --headless --cycle >> "$LOG" 2>&1 || EXIT_CODE=$?
  elif command -v claw &>/dev/null; then
    claw agent run forge --cycle >> "$LOG" 2>&1 || EXIT_CODE=$?
  else
    log "OpenClaw CLI not found. Sleeping 60s."
    sleep 60
    continue
  fi

  case $EXIT_CODE in
    0)   log "Cycle $CYCLE_COUNT complete." ;;
    42)  log "Rate limit. Sleeping 60s."
         bash "$ENGINE_DIR/herald/report.sh" "rate_limit" \
           "⏸ Rate limit — pausing 60s. Resuming: $(forge_get phase)"
         sleep 60 ;;
    130) log "Interrupted."; break ;;
    *)   log "Cycle exit $EXIT_CODE. Sleeping 30s."; sleep 30 ;;
  esac

  CYCLE_COUNT=$((CYCLE_COUNT + 1))

  # Steady pace
  sleep 8
done
