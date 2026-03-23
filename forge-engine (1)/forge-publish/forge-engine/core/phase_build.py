#!/usr/bin/env python3
"""FORGE Phase: Build orchestrator — design, build, test, safety, publish.
Uses MCP agentic workflow so opencode runs in a loop with tool use,
exactly like Claude Code does.
"""

import json, re, subprocess, sys, os
from pathlib import Path
from datetime import datetime, timezone

FORGE_DIR  = Path.home() / ".forge"
ENGINE     = FORGE_DIR / "engine"
STATE      = FORGE_DIR / "state.json"
RELAY      = ENGINE / "relay/broadcast.sh"
WORKSPACE  = Path.home() / "forge-workspace"
MCP_DIR    = ENGINE / "mcp"

# Make MCP modules importable
sys.path.insert(0, str(MCP_DIR))

def load_state():
    return json.loads(STATE.read_text())

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

def broadcast(event, msg):
    subprocess.run([str(RELAY), event, msg], capture_output=True)

def load_env():
    env = os.environ.copy()
    ef = FORGE_DIR / ".env"
    if ef.exists():
        for line in ef.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"')
    return env

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True,
                       text=True, cwd=str(cwd) if cwd else None)
    return r.stdout.strip() + r.stderr.strip(), r.returncode

def cortex(task, model="gemini-2.0-flash", cwd=None, use_mcp=False,
           context_files=None):
    """
    Invoke opencode. When use_mcp=True, runs in full agentic loop
    with MCP tool use — just like Claude Code.
    """
    if use_mcp:
        try:
            # Import MCP bridge for agentic execution
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "opencode_bridge",
                str(MCP_DIR / "opencode_bridge.py")
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.run_agentic(
                task,
                cwd=str(cwd) if cwd else None,
                model=model,
                context_files=context_files or []
            )
            return result.get("output", ""), 0 if result.get("success") else 1
        except Exception as e:
            broadcast("status", f"⚠ MCP bridge error: {e} — falling back to direct")

    # Direct cortex invocation (non-agentic)
    r = subprocess.run(
        ["bash", str(ENGINE / "cortex/invoke.sh"),
         "--model", model, "--task", task],
        capture_output=True, text=True,
        env=load_env(), timeout=300,
        cwd=str(cwd) if cwd else None
    )
    return r.stdout.strip(), r.returncode

# ── Design ────────────────────────────────────────────────────────────────────
def phase_design(state, proj, proj_dir):
    broadcast("phase_change", f"📐 Designing: {proj['name']}")
    task = (
        f"You are FORGE designing: {proj['name']}\n"
        f"Description: {proj['idea']}\n\n"
        "Write a complete DESIGN.md with these exact sections:\n"
        "# [Project Name]\n## Problem\n## Solution\n## Architecture\n"
        "## opencode task plan\n## What FORGE writes directly\n"
        "## Interface design\n## Edge cases\n## Success criteria\n\n"
        "The opencode task plan must list 3-5 numbered tasks, each precise enough "
        "that an AI coding agent cannot misinterpret them. Include exact filenames, "
        "function signatures, and which edge cases each task must handle."
    )
    design, _ = cortex(task, cwd=proj_dir)
    (proj_dir / "DESIGN.md").write_text(design)

    state["current_project"]["design_complete"] = True
    state["phase"] = "build"
    save_state(state)
    broadcast("phase_change", f"📐 Design ready: {proj['name']}")
    return 0

# ── Build ─────────────────────────────────────────────────────────────────────
def phase_build(state, proj, proj_dir):
    broadcast("phase_change", f"🔨 Building: {proj['name']}")
    design_file = proj_dir / "DESIGN.md"
    design = design_file.read_text() if design_file.exists() else ""

    match = re.search(
        r'##\s*opencode task plan\s*\n(.*?)(?=\n##|\Z)',
        design, re.DOTALL | re.IGNORECASE
    )
    tasks_raw = match.group(1).strip() if match else ""
    tasks = re.findall(r'\d+[.)]\s*(.+?)(?=\n\d+[.)]|\Z)', tasks_raw, re.DOTALL)
    tasks = [t.strip() for t in tasks if t.strip()] or [
        f"Implement the core functionality of {proj['name']} as described in the design",
        "Write comprehensive tests for the main functionality",
        "Write README.md with installation, usage, and examples",
    ]

    done = state["current_project"].get("build_tasks_done", [])
    for i, task in enumerate(tasks):
        tid = f"t{i}"
        if tid in done:
            continue
        print(f"  [{i+1}/{len(tasks)}] {task[:70]}")
        broadcast("phase_change", f"🔨 [{i+1}/{len(tasks)}] {task[:80]}")

        full = (
            f"Project: {proj['name']}\n"
            f"Description: {proj.get('idea','')}\n\n"
            f"Task: {task}\n\n"
            "Work through this step by step using tool calls.\n"
            "- Use read_file to check existing code before writing\n"
            "- Use write_file to create files\n"
            "- Use shell to run and verify your code\n"
            "- Use edit_file to fix specific issues\n"
            "Write clean, production-quality code. "
            "Self-documenting names. Proper error handling. No dead code."
        )

        # Use MCP agentic mode — opencode loops with tool use
        _, code = cortex(
            full, cwd=proj_dir,
            use_mcp=True,
            context_files=[str(design_file)] if design_file.exists() else []
        )

        if code == 0:
            done.append(tid)
            state["current_project"]["build_tasks_done"] = done
            save_state(state)

    # Ensure git, .gitignore, .env.example exist
    if not (proj_dir / ".git").exists():
        run("git init", cwd=proj_dir)
    gi = proj_dir / ".gitignore"
    if not gi.exists():
        gi.write_text(".env\nnode_modules/\n__pycache__/\n*.pyc\n.DS_Store\n")
    ee = proj_dir / ".env.example"
    if not ee.exists():
        ee.write_text("# Copy to .env and fill in values\n")

    state["phase"] = "test"
    save_state(state)
    broadcast("phase_change", f"🔨 Build complete: {proj['name']}")
    return 0

# ── Test ──────────────────────────────────────────────────────────────────────
def phase_test(state, proj, proj_dir):
    broadcast("phase_change", f"🧪 Testing: {proj['name']}")
    out, _ = run(
        "npm test 2>&1 || pytest -v --tb=short 2>&1 || echo 'no-test-runner'",
        cwd=proj_dir
    )
    print(out[:400])

    if "failed" in out.lower() and "no-test-runner" not in out:
        # Use full MCP agentic loop to fix failures
        # opencode can read files, edit them, run tests again, iterate
        fix_task = (
            f"Fix all failing tests for {proj['name']}.\n\n"
            f"Test output:\n{out[:1200]}\n\n"
            "Instructions:\n"
            "1. Use read_file to examine the failing code\n"
            "2. Use edit_file or write_file to fix the implementation\n"
            "3. Use shell to run the tests again\n"
            "4. Repeat until all tests pass\n"
            "5. Fix the implementation, never skip or delete tests\n"
            "Say 'Task complete' when all tests pass."
        )
        cortex(fix_task, cwd=proj_dir, use_mcp=True)

    state["phase"] = "safety"
    save_state(state)
    return 0

# ── Safety ────────────────────────────────────────────────────────────────────
def phase_safety(state, proj, proj_dir):
    r = subprocess.run(
        ["python3", str(ENGINE / "core/safety.py"), str(proj_dir)],
        capture_output=True, text=True
    )
    if "PASS" in r.stdout:
        state["phase"] = "publish"
        save_state(state)
        return 0
    else:
        print(f"Safety: {r.stdout.strip()}")
        state["safety_discards"] = state.get("safety_discards", 0) + 1
        state["current_project"] = None
        state["phase"] = "ideate"
        save_state(state)
        return 0

# ── Publish ───────────────────────────────────────────────────────────────────
def phase_publish(state, proj, proj_dir):
    broadcast("phase_change", f"🚀 Publishing: {proj['name']}")
    env = load_env()
    gh_user = env.get("GITHUB_USERNAME", "")
    name = proj["name"]

    run("git add .", cwd=proj_dir)
    commit_msg = f"feat: initial release\n\n{name} — {proj['idea'][:72]}"
    run(f'git commit -m "{commit_msg}"', cwd=proj_dir)

    out, code = run(
        f'gh repo create {name} --public '
        f'--description "{proj["idea"][:98]}" --push 2>&1',
        cwd=proj_dir
    )
    print(out[:300])

    if code == 0:
        run(f"gh repo edit {name} --add-topic forge-built --add-topic ai",
            cwd=proj_dir)

    url = f"https://github.com/{gh_user}/{name}" if gh_user else f"github.com/{name}"

    state["github_repos"].append({
        "name": name, "full_name": f"{gh_user}/{name}",
        "url": url,
        "published_at": datetime.now(timezone.utc).isoformat()
    })
    state["project_history"].append({
        "name": name, "idea": proj["idea"],
        "domain": proj.get("domain","?"),
        "url": url,
        "published_at": datetime.now(timezone.utc).isoformat()
    })
    n = state.get("projects_today", 0) + 1
    state["projects_today"] = n
    state["cycle"] = state.get("cycle", 0) + 1
    state["current_project"] = None
    state["notes"] = []
    target = state.get("daily_target", 5)
    state["phase"] = "research" if n < target else "maintenance"
    save_state(state)

    msg = f"⚡ FORGE shipped {n}/{target}: {name}\n{proj['idea']}\n→ {url}"
    if n >= target:
        msg += f"\n\nDay {state['day']} complete — {n} built and shipped."
    broadcast("project_ship", msg)
    print(f"Shipped: {url}")
    return 0

# ── Router ────────────────────────────────────────────────────────────────────
def main():
    state = load_state()
    phase = state.get("phase","design")
    proj  = state.get("current_project")

    if not proj:
        state["phase"] = "ideate"
        save_state(state)
        return 0

    name = proj.get("name","unnamed")
    proj_dir = WORKSPACE / name
    proj_dir.mkdir(parents=True, exist_ok=True)

    return {
        "design":  phase_design,
        "build":   phase_build,
        "test":    phase_test,
        "safety":  phase_safety,
        "publish": phase_publish,
    }.get(phase, lambda s,p,d: (save_state({**s,"phase":"research"}), 0)[1])(
        state, proj, proj_dir
    )

if __name__ == "__main__":
    sys.exit(main())
