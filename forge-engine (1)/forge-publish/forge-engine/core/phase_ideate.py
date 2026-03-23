#!/usr/bin/env python3
"""FORGE Phase: Ideate — generates and scores project candidates."""

import json, re, subprocess, sys, os
from pathlib import Path

FORGE_DIR = Path.home() / ".forge"
ENGINE    = FORGE_DIR / "engine"
STATE     = FORGE_DIR / "state.json"
RELAY     = ENGINE / "relay/broadcast.sh"

DISQUALIFIED = [
    "todo", "weather app", "note-taking", "chatgpt wrapper",
    "blog", "portfolio", "calculator", "quiz app",
]

def load_state():
    return json.loads(STATE.read_text())

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

def broadcast(event, msg):
    subprocess.run([str(RELAY), event, msg], capture_output=True)

def load_env():
    env = os.environ.copy()
    env_file = FORGE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"')
    return env

def invoke_cortex(task):
    result = subprocess.run(
        ["bash", str(ENGINE / "cortex/invoke.sh"),
         "--model", "gemini-2.0-flash", "--task", task],
        capture_output=True, text=True, env=load_env(), timeout=120
    )
    return result.stdout.strip()

def score(idea):
    keys = ["intellectual_depth","confirmed_demand","free_tier_viable",
            "novelty","opencode_delegatable"]
    return sum(idea.get(k, 5) for k in keys) / len(keys)

def disqualified(idea):
    text = (idea.get("name","") + " " + idea.get("description","")).lower()
    return any(kw in text for kw in DISQUALIFIED)

def main():
    state = load_state()

    # Check for gateway-forced build
    forced = state.pop("forced_build", None)
    if forced:
        state["current_project"] = {
            "name": forced.lower().replace(" ","-"),
            "idea": forced, "domain": "C", "scores": {}, "forced": True
        }
        state["phase"] = "design"
        save_state(state)
        broadcast("phase_change", f"⚡ Forced build: {forced}")
        return 0

    notes = state.get("notes", [])
    summary = "\n".join(
        f"- [{n['source']}] {n.get('content','')[:150]}"
        for n in notes[-12:]
    )

    task = (
        "Generate exactly 5 software project ideas as a valid JSON array. "
        "Each element has: name(kebab-case string), description(one precise sentence), "
        "domain(string: A/B/C/D/E), intellectual_depth(int 1-10), "
        "confirmed_demand(int 1-10), free_tier_viable(int 1-10), "
        "novelty(int 1-10), opencode_delegatable(int 1-10).\n"
        "Domains: A=AI agents, B=LLM utilities, C=Coding automation, "
        "D=OpenClaw skills, E=Data/knowledge tools.\n"
        "No todo/weather/note/chatbot-wrapper/blog/portfolio projects.\n"
        "Must run on Gemini free tier, no GPU needed.\n"
        f"Research notes:\n{summary}\n\n"
        "Output ONLY a valid JSON array. No markdown, no explanation."
    )

    raw = invoke_cortex(task)
    match = re.search(r'\[.*?\]', raw, re.DOTALL)

    fallback = [{"name":"forge-prompt-lab","description":
        "Browser-based LLM prompt testing tool with diff view across models",
        "domain":"B","intellectual_depth":7,"confirmed_demand":8,
        "free_tier_viable":9,"novelty":6,"opencode_delegatable":8}]

    try:
        ideas = json.loads(match.group()) if match else fallback
    except Exception:
        ideas = fallback

    valid = [i for i in ideas if not disqualified(i)]
    if not valid:
        state["phase"] = "research"
        save_state(state)
        broadcast("phase_change", "⚠ No valid ideas — retrying research")
        return 0

    # Avoid recent domain repetition
    recent_domains = [
        p.get("domain") for p in state.get("project_history",[])[-3:]
    ]
    winner = max(valid, key=score)
    if winner.get("domain") in recent_domains:
        alts = [i for i in valid if i.get("domain") not in recent_domains]
        if alts:
            winner = max(alts, key=score)

    state["current_project"] = {
        "name": winner["name"],
        "idea": winner.get("description",""),
        "domain": winner.get("domain","A"),
        "scores": {k: winner.get(k) for k in [
            "intellectual_depth","confirmed_demand",
            "free_tier_viable","novelty","opencode_delegatable"]},
        "build_tasks_done": [],
    }
    state["phase"] = "design"
    save_state(state)

    broadcast("project_start",
        f"⚡ FORGE selected: {winner['name']}\n"
        f"{winner.get('description','')}\n"
        f"Score: {round(score(winner),1)}/10")
    print(f"Idea: {winner['name']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
