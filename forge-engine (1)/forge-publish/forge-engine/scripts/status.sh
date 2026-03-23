#!/usr/bin/env bash
# FORGE Status

FORGE_DIR="$HOME/.forge"
STATE="$FORGE_DIR/state.json"

get() {
  python3 -c "
import json
from pathlib import Path
try:
    d = json.loads(Path('$STATE').read_text())
    val = d
    for k in '$1'.split('.'):
        val = val.get(k, '—') if isinstance(val, dict) else '—'
    print(val)
except: print('—')
" 2>/dev/null
}

SVC=$(systemctl --user is-active forge 2>/dev/null || echo "unknown")
case $SVC in
  active)  SVC_LINE="✓ running (systemd)" ;;
  *)
    PID=$(cat "$FORGE_DIR/runner.pid" 2>/dev/null || echo "")
    [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null && \
      SVC_LINE="✓ running (pid $PID)" || SVC_LINE="✗ not running"
    ;;
esac

MUTATIONS=$(get "arena.mutations")
RACES=$(get "arena.races_won")

echo "⚡ FORGE Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Service       $SVC_LINE"
echo "Phase         $(get phase)"
echo "Day           $(get day)"
echo "Today         $(get projects_today)/$(get daily_target) shipped"
echo "Total         $(python3 -c "
import json
from pathlib import Path
try:
  print(len(json.loads(Path('$STATE').read_text()).get('project_history',[])))
except: print('—')
" 2>/dev/null)"
echo ""
echo "Arena"
echo "  Mutations   $MUTATIONS applied"
echo "  Races won   $RACES"
echo ""
echo "Recent log:"
tail -5 "$FORGE_DIR/logs/forge.log" 2>/dev/null | sed 's/^/  /' || echo "  no log yet"
echo ""
