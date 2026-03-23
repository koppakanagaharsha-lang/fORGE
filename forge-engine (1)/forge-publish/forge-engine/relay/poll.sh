#!/usr/bin/env bash
# FORGE Relay — poll Telegram for commands, execute them
# Called each cycle from scripts/start.sh

FORGE_DIR="$HOME/.forge"
STATE="$FORGE_DIR/state.json"
CMD_FILE="$FORGE_DIR/pending_command"
LAST_UPDATE_FILE="$FORGE_DIR/.telegram_last_update"
KEYRING="$FORGE_DIR/engine/keyring/keyring.py"

source "$FORGE_DIR/.env" 2>/dev/null || true

# ── Poll Telegram ─────────────────────────────────────────────────────────────
# Get active token from keyring
TGTOKEN=$(python3 - 2>/dev/null << 'PY'
import sys, os
sys.path.insert(0, os.path.expanduser('~') + '/.forge/engine/keyring')
try:
    from keyring import get_keyring
    print(get_keyring().get_key('telegram') or '')
except Exception:
    print(os.environ.get('TELEGRAM_BOT_TOKEN', ''))
PY
)
TGTOKEN="${TGTOKEN:-$TELEGRAM_BOT_TOKEN}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"

if [ -n "$TGTOKEN" ] && [ -n "$CHAT_ID" ]; then
  LAST_UPDATE=$(cat "$LAST_UPDATE_FILE" 2>/dev/null || echo "0")
  UPDATES=$(curl -s \
    "https://api.telegram.org/bot${TGTOKEN}/getUpdates?offset=$((LAST_UPDATE+1))&timeout=0" \
    2>/dev/null || echo '{"ok":false}')

  python3 - "$CHAT_ID" "$CMD_FILE" "$LAST_UPDATE_FILE" << 'PY' 2>/dev/null
import sys, json, os

expected_chat = sys.argv[1]
cmd_file      = sys.argv[2]
last_id_file  = sys.argv[3]

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if not data.get('ok'):
    sys.exit(0)

results = data.get('result', [])
if not results:
    sys.exit(0)

last_id = max(r['update_id'] for r in results)
with open(last_id_file, 'w') as f:
    f.write(str(last_id))

for update in results:
    msg  = update.get('message', {})
    text = msg.get('text', '').strip()
    chat = str(msg.get('chat', {}).get('id', ''))
    if chat != expected_chat:
        continue

    t = text.lower()

    # Map to internal command tokens
    cmd = None
    if   t in ('forge status', '/status'):         cmd = 'status'
    elif t in ('forge pause',  '/pause'):           cmd = 'pause'
    elif t in ('forge resume', '/resume'):          cmd = 'resume'
    elif t in ('forge mutate', '/mutate'):          cmd = 'mutate'
    elif t in ('forge why',    '/why'):             cmd = 'why'
    elif t in ('forge keys status', '/keys status'): cmd = 'keys_status'
    elif t in ('forge keys add',    '/keys add'):   cmd = 'keys_add'
    elif t in ('forge keys rotate', '/keys rotate'):cmd = 'keys_rotate'
    elif t.startswith('forge build '):              cmd = 'build:' + text[12:]
    elif t.startswith('/build '):                   cmd = 'build:' + text[7:]
    elif t.startswith('forge focus '):              cmd = 'focus:' + text[12:]
    elif t.startswith('forge log'):
        parts = text.split(); n = parts[2] if len(parts) > 2 else '20'
        cmd = f'log:{n}'
    elif t.startswith('forge issue '):
        parts = text.split()
        if len(parts) >= 4: cmd = f'issue:{parts[2]}:{parts[3]}'

    if cmd:
        with open(cmd_file, 'w') as f:
            f.write(cmd)
        print(f'Command queued: {cmd}', file=sys.stderr)
PY
  echo "$UPDATES" | python3 - "$CHAT_ID" "$CMD_FILE" "$LAST_UPDATE_FILE"
fi

# ── Execute pending command ───────────────────────────────────────────────────
[ -f "$CMD_FILE" ] || exit 0
CMD=$(cat "$CMD_FILE")
rm -f "$CMD_FILE"

broadcast() {
  "$FORGE_DIR/engine/relay/broadcast.sh" "$1" "$2" 2>/dev/null || true
}

update_state() {
  python3 - "$1" "$2" << 'PY' 2>/dev/null
import sys, json
from pathlib import Path
sf = Path.home() / '.forge/state.json'
s = json.loads(sf.read_text())
s[sys.argv[1]] = sys.argv[2]
sf.write_text(json.dumps(s, indent=2))
PY
}

case "$CMD" in
  status)
    OUT=$(bash "$FORGE_DIR/engine/scripts/status.sh" 2>/dev/null || echo "Status unavailable")
    broadcast "status" "$OUT"
    ;;

  pause)
    PHASE=$(python3 -c "import json; from pathlib import Path; print(json.loads((Path.home()/'.forge/state.json').read_text()).get('phase','research'))" 2>/dev/null || echo "research")
    update_state "_paused_phase" "$PHASE"
    update_state "phase" "paused"
    broadcast "status" "⏸ FORGE paused at phase: $PHASE"
    ;;

  resume)
    PREV=$(python3 -c "import json; from pathlib import Path; print(json.loads((Path.home()/'.forge/state.json').read_text()).get('_paused_phase','research'))" 2>/dev/null || echo "research")
    update_state "phase" "$PREV"
    broadcast "status" "▶ FORGE resumed → $PREV"
    ;;

  mutate)
    broadcast "status" "🔬 Arena: race initiated"
    bash "$FORGE_DIR/engine/arena/race.sh" \
      "cortex/invoke.sh" "general efficiency improvement" &
    ;;

  why)
    INFO=$(python3 - << 'PY' 2>/dev/null
import json
from pathlib import Path
s = json.loads((Path.home()/'.forge/state.json').read_text())
p = s.get('current_project') or {}
name = p.get('name', 'none') if isinstance(p, dict) else str(p)
print(f"Phase: {s.get('phase','?')}\nProject: {name}\nDay {s.get('day',1)} | {s.get('projects_today',0)}/{s.get('daily_target',5)} shipped\nMutations: {s.get('arena',{}).get('mutations',0)}")
PY
)
    broadcast "status" "🔍 FORGE:
$INFO"
    ;;

  keys_status)
    KS=$(python3 "$KEYRING" status 2>/dev/null || echo "Keyring unavailable")
    broadcast "status" "$KS"
    ;;

  keys_add)
    broadcast "status" "To add keys, run in your terminal:
bash ~/.forge/engine/keyring/setup_wizard.sh"
    ;;

  keys_rotate)
    CURR=$(python3 - << 'PY' 2>/dev/null
import sys, os
sys.path.insert(0, os.path.expanduser('~') + '/.forge/engine/keyring')
from keyring import get_keyring
k = get_keyring().get_key('gemini')
print(k or '')
PY
)
    [ -n "$CURR" ] && python3 "$KEYRING" report gemini "$CURR" 2>/dev/null || true
    broadcast "status" "⚡ Keyring: Gemini key rotated"
    ;;

  build:*)
    IDEA="${CMD#build:}"
    python3 - "$IDEA" << 'PY' 2>/dev/null
import sys, json
from pathlib import Path
sf = Path.home() / '.forge/state.json'
s = json.loads(sf.read_text())
s['forced_build'] = sys.argv[1]
s['phase'] = 'ideate'
sf.write_text(json.dumps(s, indent=2))
PY
    broadcast "status" "⚡ Build queued: $IDEA"
    ;;

  focus:*)
    DOMAIN="${CMD#focus:}"
    broadcast "status" "🎯 Domain focus set: $DOMAIN"
    ;;

  log:*)
    N="${CMD#log:}"
    LINES=$(tail -"${N:-20}" "$FORGE_DIR/logs/forge.log" 2>/dev/null || echo "No log yet")
    broadcast "log" "📋 Last $N lines:
$LINES"
    ;;

  issue:*)
    PARTS="${CMD#issue:}"
    REPO="${PARTS%%:*}"
    ISSUE_N="${PARTS#*:}"
    broadcast "status" "💬 Handling $REPO#$ISSUE_N..."
    python3 "$FORGE_DIR/engine/core/phase_maintenance.py" \
      --repo "$REPO" --issue "$ISSUE_N" &
    ;;
esac
