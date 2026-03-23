#!/usr/bin/env bash
# FORGE Core Kernel
# The immortal component. Never directly mutated.
# All other components are evolvable. This one is not.
# It ensures FORGE cannot lose itself during mutation.

FORGE_DIR="$HOME/.forge"
ENGINE_DIR="$FORGE_DIR/engine"
LEDGER="$FORGE_DIR/ledger/state.json"

# ── State operations ──────────────────────────────────────────────────────────

forge_get() {
  python3 -c "
import json, sys
try:
  with open('$LEDGER') as f:
    d = json.load(f)
  keys = '$1'.split('.')
  val = d
  for k in keys:
    val = val[k]
  print(val)
except: print('')
" 2>/dev/null || echo ""
}

forge_set() {
  python3 -c "
import json
with open('$LEDGER') as f: d = json.load(f)
keys = '$1'.split('.')
obj = d
for k in keys[:-1]: obj = obj.setdefault(k, {})
obj[keys[-1]] = $2
with open('$LEDGER', 'w') as f: json.dump(d, f, indent=2)
" 2>/dev/null
}

forge_append() {
  python3 -c "
import json
with open('$LEDGER') as f: d = json.load(f)
key = '$1'
if key not in d: d[key] = []
d[key].append($2)
with open('$LEDGER', 'w') as f: json.dump(d, f, indent=2)
" 2>/dev/null
}

# ── Safety guard — verify core integrity ─────────────────────────────────────

forge_verify_core() {
  local core="$ENGINE_DIR/core/kernel.sh"
  if [ ! -f "$core" ]; then
    echo "[FORGE KERNEL] CRITICAL: Core missing. Cannot proceed." >&2
    exit 99
  fi
  # Verify core has not been modified during a mutation cycle
  local current_hash
  current_hash=$(sha256sum "$core" | cut -d' ' -f1)
  local stored_hash
  stored_hash=$(cat "$FORGE_DIR/.core_hash" 2>/dev/null || echo "")
  if [ -n "$stored_hash" ] && [ "$current_hash" != "$stored_hash" ]; then
    echo "[FORGE KERNEL] WARNING: Core hash mismatch. Restoring from backup." >&2
    cp "$FORGE_DIR/.core_backup/kernel.sh" "$core"
  fi
}

# ── Core backup (runs once after any promotion) ───────────────────────────────

forge_backup_core() {
  mkdir -p "$FORGE_DIR/.core_backup"
  cp "$ENGINE_DIR/core/kernel.sh" "$FORGE_DIR/.core_backup/kernel.sh"
  sha256sum "$ENGINE_DIR/core/kernel.sh" | cut -d' ' -f1 > "$FORGE_DIR/.core_hash"
}

# ── Phase management ──────────────────────────────────────────────────────────

forge_phase() {
  forge_get phase
}

forge_advance() {
  local next_phase="$1"
  forge_set phase "\"$next_phase\""
  echo "[$(date '+%H:%M:%S')] Phase: $next_phase"
}

# ── API call tracking (free tier discipline) ─────────────────────────────────

forge_track_call() {
  local count
  count=$(forge_get api_call_count)
  count=$((count + 1))
  forge_set api_call_count $count
  # After 8 calls: pause 15s
  if (( count % 8 == 0 )); then
    echo "[FORGE] Pacing — 15s rest after $count calls"
    sleep 15
  fi
}

# Initialize core hash on first run
if [ ! -f "$FORGE_DIR/.core_hash" ]; then
  forge_backup_core
fi

forge_verify_core

export -f forge_get forge_set forge_append forge_phase forge_advance forge_track_call
