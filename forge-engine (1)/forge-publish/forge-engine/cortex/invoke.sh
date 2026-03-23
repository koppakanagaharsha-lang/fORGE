#!/usr/bin/env bash
# FORGE Cortex — invoke opencode with model selection and context
# Usage: invoke.sh --model [model] --task [task] --context [file] --output [file]

set -euo pipefail

FORGE_DIR="$HOME/.forge"
LOG="$FORGE_DIR/logs/cortex.log"
KEYRING="$FORGE_DIR/engine/keyring/keyring.py"
RELAY="$FORGE_DIR/engine/relay/broadcast.sh"

MODEL=""
TASK=""
CONTEXT_FILE=""
OUTPUT_FILE=""
TIMEOUT="${FORGE_OPENCODE_TIMEOUT:-300}"
MAX_RETRIES=3

while [[ $# -gt 0 ]]; do
  case $1 in
    --model)    MODEL="$2";        shift 2 ;;
    --task)     TASK="$2";         shift 2 ;;
    --context)  CONTEXT_FILE="$2"; shift 2 ;;
    --output)   OUTPUT_FILE="$2";  shift 2 ;;
    --timeout)  TIMEOUT="$2";      shift 2 ;;
    *)          TASK="$1";         shift   ;;
  esac
done

source "$FORGE_DIR/.env" 2>/dev/null || true

[ -z "$MODEL" ] && MODEL=$(python3 "$FORGE_DIR/engine/cortex/model_select.py" "$TASK")

log() { echo "[CORTEX $(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

FULL_PROMPT="$TASK"
if [ -n "$CONTEXT_FILE" ] && [ -f "$CONTEXT_FILE" ]; then
  FULL_PROMPT="Context from $(basename "$CONTEXT_FILE"):
$(cat "$CONTEXT_FILE")

---
Task:
$TASK"
fi

# ── Key-rotating invocation loop ─────────────────────────────────────────────
for attempt in $(seq 1 $MAX_RETRIES); do

  # Get next available Gemini key from keyring
  CURRENT_KEY=$(python3 "$KEYRING" get gemini 2>/dev/null | \
    python3 - << 'PY'
import sys
sys.path.insert(0, __import__('os').path.expanduser('~') + '/.forge/engine/keyring')
from keyring import get_keyring
print(get_keyring().get_key('gemini') or '')
PY
  )

  if [ -z "$CURRENT_KEY" ]; then
    # All keys on cooldown — check how long to wait
    WAIT=$(python3 "$KEYRING" cooldown gemini 2>/dev/null | grep -oP '[\d.]+(?=s)' | head -1 || echo "60")
    log "All Gemini keys on cooldown. Waiting ${WAIT}s."
    "$RELAY" "rate_limit" "⏸ All Gemini keys cooling — waiting ${WAIT}s then resuming" 2>/dev/null &
    sleep "${WAIT:-60}"
    continue
  fi

  export GEMINI_API_KEY="$CURRENT_KEY"
  export OPENCODE_MODEL="$MODEL"

  log "Attempt $attempt: model=$MODEL key=${CURRENT_KEY:0:8}..."

  if [ -n "$OUTPUT_FILE" ]; then
    timeout "$TIMEOUT" opencode "$FULL_PROMPT" > "$OUTPUT_FILE" 2>>"$LOG"
    EXIT=$?
  else
    timeout "$TIMEOUT" opencode "$FULL_PROMPT" 2>>"$LOG"
    EXIT=$?
  fi

  # Handle exit codes
  if [ $EXIT -eq 0 ]; then
    log "Cortex success on attempt $attempt"
    exit 0
  elif [ $EXIT -eq 124 ]; then
    log "Timeout on attempt $attempt"
    exit 1
  else
    # Check if error was rate limit
    LAST_LINES=$(tail -5 "$LOG" 2>/dev/null || echo "")
    if echo "$LAST_LINES" | grep -qiE "rate.?limit|quota|429|resource.?exhausted"; then
      log "Rate limit on key ${CURRENT_KEY:0:8}... — rotating"
      python3 "$KEYRING" report gemini "$CURRENT_KEY" 2>/dev/null || true
      "$RELAY" "rate_limit" "⏸ Key rotated (rate limit). Continuing with next key." 2>/dev/null &
      # Immediately retry with next key
      continue
    else
      log "opencode error (exit $EXIT) on attempt $attempt"
      [ $attempt -ge $MAX_RETRIES ] && exit $EXIT
    fi
  fi

  sleep 3
done

log "All $MAX_RETRIES attempts failed"
exit 1
