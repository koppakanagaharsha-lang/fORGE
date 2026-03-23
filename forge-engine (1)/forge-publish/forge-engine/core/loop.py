#!/usr/bin/env python3
"""FORGE Core Loop — routes to phase handlers each cycle."""

import json, subprocess, sys, time
from pathlib import Path

FORGE_DIR = Path.home() / ".forge"
ENGINE    = FORGE_DIR / "engine"
STATE     = FORGE_DIR / "state.json"

def load_state():
    return json.loads(STATE.read_text())

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

def broadcast(event, msg):
    subprocess.run([str(ENGINE / "relay/broadcast.sh"), event, msg],
                   capture_output=True)

def run_phase(script):
    result = subprocess.run(
        ["python3", str(script)],
        capture_output=False
    )
    return result.returncode

def main():
    state = load_state()

    if not state.get("setup_complete"):
        print("Setup not complete. Waiting.")
        sys.exit(0)

    phase = state.get("phase", "research")
    print(f"[loop] phase={phase} day={state.get('day',1)} "
          f"projects={state.get('projects_today',0)}/{state.get('daily_target',5)}")

    # Poll for gateway commands first
    poll = ENGINE / "relay/poll.sh"
    if poll.exists():
        subprocess.run(["bash", str(poll)], capture_output=True)

    # Run sentinel check
    sentinel = ENGINE / "sentinel/monitor.sh"
    if sentinel.exists():
        subprocess.run(["bash", str(sentinel)], capture_output=True)

    # Phase routing
    phase_map = {
        "research":    ENGINE / "core/phase_research.py",
        "autoresearch": ENGINE / "core/phase_autoresearch.py",
        "ideate":      ENGINE / "core/phase_ideate.py",
        "design":      ENGINE / "core/phase_build.py",
        "build":       ENGINE / "core/phase_build.py",
        "test":        ENGINE / "core/phase_build.py",
        "safety":      ENGINE / "core/phase_build.py",
        "publish":     ENGINE / "core/phase_build.py",
        "maintenance": ENGINE / "core/phase_maintenance.py",
        "paused":      None,
        "arena":       ENGINE / "arena/race.sh",
    }

    handler = phase_map.get(phase)

    if phase == "paused":
        print("FORGE paused.")
        time.sleep(30)
        sys.exit(0)

    if phase == "arena":
        subprocess.run(["bash", str(ENGINE / "arena/race.sh"),
                        "cortex/invoke.sh", "efficiency improvement"])
        sys.exit(0)

    if handler is None or not handler.exists():
        # Unknown phase — reset
        state["phase"] = "research"
        save_state(state)
        print(f"Unknown phase '{phase}' — resetting to research")
        sys.exit(0)

    # Check if Arena is due (every 10 projects)
    total = len(state.get("project_history", []))
    mutations = state.get("arena", {}).get("mutations", 0)
    if total > 0 and total % 10 == 0 and mutations < total // 10:
        print("Arena race due — scheduling after this cycle")
        state.setdefault("arena", {})["race_pending"] = True
        save_state(state)

    code = run_phase(handler)

    # Track API calls
    state = load_state()
    state["api_call_count"] = state.get("api_call_count", 0) + 1
    if state["api_call_count"] % 8 == 0:
        print("Pacing: 15s pause")
        time.sleep(15)
    save_state(state)

    sys.exit(code if code in [0, 42] else 0)

if __name__ == "__main__":
    main()
