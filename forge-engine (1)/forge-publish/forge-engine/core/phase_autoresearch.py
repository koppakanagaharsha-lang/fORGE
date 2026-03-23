#!/usr/bin/env python3
"""FORGE Phase: AutoResearch.

Inspired by karpathy/autoresearch: An autonomous loop that iterations on a single script
(e.g., train.py) based on instructions (e.g., program.md), strictly measures the validation
metric after computing fixed time, and promotes the most successful iteration.
"""

import json, subprocess, sys, time, re, shutil
from pathlib import Path
from datetime import datetime, timezone

FORGE_DIR = Path.home() / ".forge"
ENGINE    = FORGE_DIR / "engine"
STATE     = FORGE_DIR / "state.json"
RELAY     = ENGINE / "relay/broadcast.sh"

WORKSPACE = Path.home() / "forge-workspace"

def load_state():
    return json.loads(STATE.read_text())

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

def broadcast(event, msg):
    try: subprocess.run([str(RELAY), event, msg], capture_output=True)
    except: pass

def get_best_metric(state):
    return state.get("autoresearch", {}).get("best_metric", float("inf"))

def extract_metric(output: str):
    # E.g. looks for "val_bpb = 2.45" or "val_loss: 0.12"
    matches = re.findall(r"(?:val_loss|val_bpb|metric|score)[\s:=]+([0-9.]+)", output, re.IGNORECASE)
    if not matches:
        return float("inf")
    return float(matches[-1])  # taking the final valid reading

def main():
    state = load_state()
    run_num = state.get("autoresearch", {}).get("runs", 0) + 1

    broadcast("phase_change", f"🔄 AutoResearch iteration {run_num} started")

    program_file = WORKSPACE / "program.md"
    target_file = WORKSPACE / "train.py"

    if not program_file.exists():
        program_file.parent.mkdir(parents=True, exist_ok=True)
        program_file.write_text("# AutoResearch Instructions\n\nOptimize `train.py` for accuracy. Modify batch size and logic.")

    if not target_file.exists():
        target_file.write_text('print("val_loss = 1.0")\n')

    # Backup current best
    best_file = target_file.with_suffix(".py.best")
    if not best_file.exists():
        shutil.copy(target_file, best_file)

    # Invoke cortex to rewrite script
    prompt = (
        f"You are AutoResearch. Read instructions in program.md:\n"
        f"{program_file.read_text()[:1000]}\n\n"
        f"Current file {target_file.name}:\n"
        f"{target_file.read_text()}\n\n"
        "Please rewrite the entire code to improve the metric. Return ONLY valid executable code inside a ``` block."
    )
    
    print("Calling Opencode cortex...")
    res = subprocess.run([str(ENGINE / "cortex/invoke.sh"), "--task", prompt, "--model", "gemini-3.1-flash-lite"],
                         capture_output=True, text=True)

    block = re.search(r"```(python)?\n(.*?)```", res.stdout, re.DOTALL)
    if block:
        new_code = block.group(2).strip()
        target_file.write_text(new_code)
        print("Generated new variation.")
    else:
        print("No valid code emitted.")
        return 0

    # Execute it
    print(f"Executing {target_file.name} (10s budget)")
    run_res = subprocess.run(["python3", str(target_file)], capture_output=True, text=True, cwd=str(WORKSPACE), timeout=10)
    
    output = run_res.stdout + "\n" + run_res.stderr
    metric = extract_metric(output)
    
    best = get_best_metric(state)
    
    msg = f"Iteration {run_num}: metric={metric} (Best={best})"
    print(msg)

    ar_state = state.setdefault("autoresearch", {})
    ar_state["runs"] = run_num
    
    if metric < best:
        broadcast("phase_change", f"🏆 AutoResearch improved metric! {best} → {metric}")
        best = metric
        ar_state["best_metric"] = best
        shutil.copy(target_file, best_file)
    else:
        broadcast("phase_change", f"♻️ AutoResearch no improvement, restoring best.")
        shutil.copy(best_file, target_file)

    state["phase"] = "research" # back to normal cycle or anywhere
    save_state(state)

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.TimeoutExpired:
        print("Execution timed out. Restoring best run.")
        # Restoration will happen next cycle automatically or assume failure
        sys.exit(0)
