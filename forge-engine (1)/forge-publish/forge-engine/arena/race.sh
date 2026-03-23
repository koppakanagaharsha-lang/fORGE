#!/usr/bin/env bash
# FORGE Arena — Fork. Race. Evolve.
# Usage: race.sh [component] [mutation_description]
# The component to mutate and a description of the proposed change.

set -euo pipefail

FORGE_DIR="$HOME/.forge"
ENGINE="$FORGE_DIR/engine"
ARENA_DIR="$FORGE_DIR/arena"
LOG="$FORGE_DIR/logs/arena.log"
STATE="$FORGE_DIR/state.json"

COMPONENT="${1:-cortex/invoke.sh}"
MUTATION="${2:-general improvement}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FORK_DIR="$ARENA_DIR/fork_$TIMESTAMP"

mkdir -p "$ARENA_DIR" "$FORGE_DIR/logs"

log() { echo "[ARENA $TIMESTAMP] $*" | tee -a "$LOG"; }
broadcast() { "$ENGINE/relay/broadcast.sh" "arena_race_start" "$*" 2>/dev/null || true; }

log "Race initiated: component=$COMPONENT mutation='$MUTATION'"
broadcast "🔬 Arena: race started
Mutation: $MUTATION
Target: $COMPONENT"

# ── Step 1: CLONE ─────────────────────────────────────────────────────────────
log "Cloning engine to fork..."
cp -r "$ENGINE" "$FORK_DIR"
log "Fork created: $FORK_DIR"

# ── Step 2: DOCUMENT MUTATION ────────────────────────────────────────────────
cat > "$FORK_DIR/MUTATION.md" << EOF
# Mutation Record

Timestamp: $TIMESTAMP
Component: $COMPONENT
Description: $MUTATION

## Proposed Change
[To be filled by mutation logic]

## Test Results
[Filled by test harness]

## Judge Score
[Filled by judge]
EOF

# ── Step 3: APPLY MUTATION ───────────────────────────────────────────────────
log "Applying mutation to fork..."

# The mutation is applied by invoking opencode on the fork's component
# with the mutation description as the task
source "$FORGE_DIR/.env" 2>/dev/null || true

COMPONENT_FILE="$FORK_DIR/$COMPONENT"
if [ ! -f "$COMPONENT_FILE" ]; then
  log "ERROR: Component file not found: $COMPONENT_FILE"
  rm -rf "$FORK_DIR"
  exit 1
fi

# Use cortex to generate the mutation
MUTATION_PROMPT="You are improving a component of an autonomous developer system.

Current file: $COMPONENT
Mutation goal: $MUTATION

Read the current implementation carefully.
Produce an improved version that achieves the mutation goal.
Preserve all existing interfaces — this must be a drop-in replacement.
Do not break any callers.
Output ONLY the improved file content, nothing else."

if command -v opencode &>/dev/null; then
  opencode "$MUTATION_PROMPT" --files "$COMPONENT_FILE" 2>>"$LOG" || {
    log "opencode mutation failed — aborting race"
    rm -rf "$FORK_DIR"
    exit 1
  }
fi

# ── Step 4: SAFETY CHECK ON FORK ─────────────────────────────────────────────
log "Safety checking fork..."
# Core safety files cannot be weakened
ORIGINAL_SAFETY_LINES=$(wc -l < "$ENGINE/core/safety.py")
FORK_SAFETY_LINES=$(wc -l < "$FORK_DIR/core/safety.py" 2>/dev/null || echo "0")

if [ "$FORK_SAFETY_LINES" -lt "$((ORIGINAL_SAFETY_LINES - 10))" ]; then
  log "DISQUALIFIED: Fork weakened safety.py ($ORIGINAL_SAFETY_LINES → $FORK_SAFETY_LINES lines)"
  rm -rf "$FORK_DIR"
  broadcast "🛡 Arena: fork disqualified — attempted to weaken safety wall"
  exit 0
fi

# ── Step 5: RUN TEST HARNESS ─────────────────────────────────────────────────
log "Running test harness..."
"$ENGINE/arena/test_harness.sh" "$ENGINE" "$FORK_DIR" "$TIMESTAMP" 2>>"$LOG"
HARNESS_EXIT=$?

if [ $HARNESS_EXIT -ne 0 ]; then
  log "Test harness failed — aborting"
  rm -rf "$FORK_DIR"
  exit 0
fi

# ── Step 6: JUDGE ─────────────────────────────────────────────────────────────
log "Judging results..."
JUDGE_RESULT=$(python3 "$ENGINE/arena/judge.py" "$TIMESTAMP" 2>>"$LOG")
WINNER=$(echo "$JUDGE_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['winner'])" 2>/dev/null || echo "original")
MARGIN=$(echo "$JUDGE_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['margin'])" 2>/dev/null || echo "0")

log "Judge result: winner=$WINNER margin=$MARGIN%"

# ── Step 7: APPLY OR DISCARD ─────────────────────────────────────────────────
# Core-mutable threshold: 15%, regular threshold: 5%
IS_CORE=$(echo "$COMPONENT" | grep -q "^core/" && echo "true" || echo "false")
THRESHOLD=$([ "$IS_CORE" = "true" ] && echo "15" || echo "5")

MARGIN_INT=$(echo "$MARGIN" | python3 -c "import sys; print(int(float(sys.stdin.read().strip())))" 2>/dev/null || echo "0")

if [ "$WINNER" = "fork" ] && [ "$MARGIN_INT" -ge "$THRESHOLD" ]; then
  log "Fork wins by ${MARGIN}%. Applying mutation."

  # Backup original component
  cp "$ENGINE/$COMPONENT" "$ARENA_DIR/backup_${TIMESTAMP}_$(basename $COMPONENT)"

  # Apply fork's version
  cp "$FORK_DIR/$COMPONENT" "$ENGINE/$COMPONENT"
  chmod +x "$ENGINE/$COMPONENT" 2>/dev/null || true

  # Update EVOLUTION.md
  cat >> "$FORGE_DIR/EVOLUTION.md" << EOF

## $TIMESTAMP
Component: $COMPONENT
Mutation: $MUTATION
Margin: ${MARGIN}%
Status: APPLIED
EOF

  # Update state
  python3 -c "
import json
from pathlib import Path
s = json.loads(Path('$STATE').read_text())
a = s.setdefault('arena', {})
a['mutations'] = a.get('mutations', 0) + 1
a['last_mutation'] = '$TIMESTAMP'
a['last_component'] = '$COMPONENT'
Path('$STATE').write_text(json.dumps(s, indent=2))
"

  broadcast "⚡ Arena: FORGE evolved
Component: $COMPONENT
Margin: ${MARGIN}% improvement
Mutation: $MUTATION
Applied ✓"

  log "Mutation applied. FORGE evolved."
else
  log "Original holds (margin ${MARGIN}% < threshold ${THRESHOLD}%). Fork discarded."
  broadcast "🔬 Arena: original held
Margin: ${MARGIN}% (threshold: ${THRESHOLD}%)
Fork discarded."
fi

# Cleanup fork
rm -rf "$FORK_DIR"
log "Race complete."
