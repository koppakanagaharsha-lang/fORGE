#!/usr/bin/env python3
"""FORGE Boot — reads state, checks day rollover, returns current context."""

import json, sys
from datetime import datetime, timezone
from pathlib import Path

FORGE_DIR = Path.home() / ".forge"
STATE_FILE = FORGE_DIR / "state.json"
CONFIG_FILE = FORGE_DIR / "config.json"

def load_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

def boot():
    state = load_json(STATE_FILE)
    config = load_json(CONFIG_FILE)

    now_iso  = datetime.now(timezone.utc).isoformat()
    now_date = datetime.now(timezone.utc).date().isoformat()

    # Day rollover
    last_active = state.get("last_active", "")
    last_date   = last_active[:10] if last_active else ""
    if last_date and last_date < now_date:
        state["projects_today"] = 0
        state["day"]   = state.get("day", 1) + 1
        state["notes"] = []

    state["last_active"] = now_iso

    # Maintenance urgency check
    queue  = state.get("maintenance_queue", [])
    urgent = []
    for item in queue:
        created = item.get("created_at", "")
        if created:
            try:
                age = (datetime.now(timezone.utc) -
                       datetime.fromisoformat(
                           created.replace("Z", "+00:00")
                       )).total_seconds() / 3600
                if age > 48:
                    urgent.append(item)
            except Exception:
                pass

    if urgent and state.get("phase") not in ["maintenance", "paused"]:
        state["phase"] = "maintenance"
        state["maintenance_urgent"] = len(urgent)

    save_json(STATE_FILE, state)

    result = {
        "phase":            state.get("phase", "research"),
        "cycle":            state.get("cycle", 0),
        "day":              state.get("day", 1),
        "projects_today":   state.get("projects_today", 0),
        "daily_target":     state.get("daily_target", 5),
        "operator_name":    state.get("operator_name", ""),
        "setup_complete":   state.get("setup_complete", False),
        "maintenance_urgent": len(urgent),
        "arena_mutations":  state.get("arena", {}).get("mutations", 0),
    }
    print(json.dumps(result))
    return result

if __name__ == "__main__":
    boot()
