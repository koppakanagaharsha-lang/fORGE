#!/usr/bin/env python3
"""FORGE Telegram Native Config Poller.
Integrates the Telegram bot natively to execute incoming user commands directly
through cortex or opencode, syncing perfectly with the OpenClaw logic.
"""
import sys, time, json, os, subprocess
import urllib.request
from pathlib import Path

FORGE_DIR = Path.home() / ".forge"
STATE = FORGE_DIR / "state.json"
ENGINE = FORGE_DIR / "engine"

def load_state():
    try: return json.loads(STATE.read_text())
    except Exception: return {}

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

def poll_telegram():
    env_file = FORGE_DIR / ".env"
    if not env_file.exists(): return

    env = {}
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip("'\"")

    bot_token = env.get("TELEGRAM_API_TOKEN")
    if not bot_token: return

    state = load_state()
    offset = state.get("telegram_offset", 0)

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=5"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
            
        for update in data.get("result", []):
            offset = max(offset, update["update_id"] + 1)
            msg = update.get("message", {})
            text = msg.get("text", "")
            
            if text:
                print(f"Received telegram command: {text}")
                # Invoke opencode/cortex on the command natively!
                subprocess.Popen(
                    [str(ENGINE / "cortex/invoke.sh"), "--task", text],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

        if data.get("result"):
            state["telegram_offset"] = offset
            save_state(state)
            
    except Exception as e:
        print(f"Telegram poll error: {e}")

if __name__ == "__main__":
    while True:
        poll_telegram()
        time.sleep(10)
