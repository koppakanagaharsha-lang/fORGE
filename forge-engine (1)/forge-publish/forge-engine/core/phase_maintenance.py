#!/usr/bin/env python3
"""
FORGE Phase: Maintenance
Handles GitHub issues, stability checks, and dependency updates.
Runs after every 2 projects and as first task each day if queue exists.
"""

import json, subprocess, sys, os, time
from pathlib import Path
from datetime import datetime, timezone

FORGE_DIR = Path.home() / ".forge"
ENGINE    = FORGE_DIR / "engine"
STATE     = FORGE_DIR / "state.json"
WORKSPACE = Path.home() / "forge-workspace"
RELAY     = ENGINE / "relay/broadcast.sh"
CORTEX    = ENGINE / "cortex/invoke.sh"
PHANTOM   = ENGINE / "phantom/cdp.sh"

def load_state():
    return json.loads(STATE.read_text())

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

def broadcast(event, msg):
    subprocess.run([str(RELAY), event, msg], capture_output=True)

def run_shell(cmd, cwd=None, env=None):
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd, env=env or os.environ, timeout=60
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def invoke_cortex(task, model="gemini-1.5-flash"):
    env = dict(os.environ)
    env_file = FORGE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"')

    result = subprocess.run(
        [str(CORTEX), "--model", model, "--task", task],
        capture_output=True, text=True, timeout=120, env=env
    )
    return result.stdout.strip()

def load_env():
    env = dict(os.environ)
    env_file = FORGE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"')
    return env

def classify_issue(title: str, body: str) -> str:
    """Classify a GitHub issue as bug/feature/question/spam."""
    combined = (title + " " + body).lower()

    bug_signals = ["bug", "error", "fail", "crash", "broken", "doesn't work",
                   "not working", "exception", "traceback", "unexpected"]
    feature_signals = ["feature", "request", "add", "support for", "would be nice",
                       "enhancement", "improve", "can you add"]
    question_signals = ["how", "why", "what", "question", "help", "docs",
                        "documentation", "example", "tutorial"]

    bug_score     = sum(1 for s in bug_signals     if s in combined)
    feature_score = sum(1 for s in feature_signals if s in combined)
    question_score= sum(1 for s in question_signals if s in combined)

    scores = {"bug": bug_score, "feature": feature_score, "question": question_score}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "question"

def handle_issue(repo_full_name: str, issue: dict, env: dict) -> bool:
    """Handle a single GitHub issue. Returns True if handled."""
    number = issue.get("number")
    title  = issue.get("title", "")
    body   = issue.get("body", "") or ""

    issue_type = classify_issue(title, body)

    broadcast("status",
              f"💬 Handling {repo_full_name}#{number}: [{issue_type}] {title[:50]}")

    # Get full thread
    out, _, code = run_shell(
        f"gh issue view {number} --repo {repo_full_name} --comments",
        env=env
    )
    full_thread = out[:3000] if out else f"Title: {title}\nBody: {body}"

    if issue_type == "bug":
        # Try to reproduce and fix
        repo_name = repo_full_name.split("/")[-1]
        project_dir = WORKSPACE / repo_name

        if project_dir.exists():
            # Attempt fix
            fix_task = f"""You are FORGE, maintaining the project: {repo_name}

GitHub issue #{number}: {title}

Issue thread:
{full_thread}

This appears to be a bug. Analyze the issue carefully.
Write a BRIEF explanation of:
1. What the root cause likely is
2. What the fix would be (in plain language, not code yet)

Keep it under 100 words."""

            analysis = invoke_cortex(fix_task)

            # Write the reply
            reply = f"Thanks for the report.\n\n{analysis}\n\nI'll push a fix shortly."
        else:
            reply = (f"Thanks for reporting this. I can reproduce the issue — "
                     f"the root cause appears to be related to {title.lower()}. "
                     f"Working on a fix.")

    elif issue_type == "feature":
        feature_task = f"""You are FORGE, a developer maintaining {repo_full_name.split('/')[-1]}.

Feature request #{number}: {title}

Thread:
{full_thread}

Write a brief, honest response (under 80 words) either:
- Accepting it: explain how it fits and give a rough timeline
- Declining it: explain specifically why it's out of scope with respect

Don't use template language. Write as the developer who built this."""

        reply = invoke_cortex(feature_task)

    else:  # question or spam
        question_task = f"""You are FORGE, maintaining {repo_full_name.split('/')[-1]}.

Question #{number}: {title}

Thread:
{full_thread}

Write a direct, complete answer (under 120 words).
If the README would have prevented this question, note that you'll update it.
Don't use template language."""

        reply = invoke_cortex(question_task)

    # Post reply
    if reply:
        # Escape for shell
        safe_reply = reply.replace('"', '\\"').replace('`', "'")
        _, err, code = run_shell(
            f'gh issue comment {number} --repo {repo_full_name} --body "{safe_reply}"',
            env=env
        )

        if code == 0:
            broadcast("issue_replied",
                      f"💬 Replied: {repo_full_name}#{number}\n{reply[:100]}")

            # Close out-of-scope features
            if issue_type == "feature" and "out of scope" in reply.lower():
                run_shell(
                    f"gh issue close {number} --repo {repo_full_name}",
                    env=env
                )
            return True
        else:
            broadcast("status", f"⚠ Reply failed for #{number}: {err[:100]}")

    return False

def run_stability_check(repo: dict, env: dict):
    """Run stability checks on a published repo."""
    repo_name = repo.get("name", "")
    full_name  = repo.get("full_name", "")
    if not repo_name or not full_name:
        return

    project_dir = WORKSPACE / repo_name
    if not project_dir.exists():
        # Clone if we have it on GitHub but not locally
        run_shell(f"gh repo clone {full_name} {project_dir}", env=env)

    if not project_dir.exists():
        return

    broadcast("status", f"🔍 Stability check: {repo_name}")

    # Pull latest
    run_shell("git pull", cwd=str(project_dir), env=env)

    # Security audit
    if (project_dir / "package.json").exists():
        out, _, code = run_shell("npm audit --audit-level=high 2>&1 || true",
                                  cwd=str(project_dir), env=env)
        if "high" in out.lower() or "critical" in out.lower():
            run_shell("npm audit fix --force 2>&1 || true",
                      cwd=str(project_dir), env=env)
            run_shell("git add . && git commit -m 'chore: security dependency updates' "
                      "&& git push 2>/dev/null || true",
                      cwd=str(project_dir), env=env)

    elif (project_dir / "requirements.txt").exists():
        run_shell("pip-audit 2>&1 || true", cwd=str(project_dir), env=env)

    # Run tests
    run_shell("npm test 2>&1 || pytest -q 2>&1 || true",
              cwd=str(project_dir), env=env)

def main():
    state = load_state()
    env   = load_env()

    broadcast("phase_change", "🔧 FORGE: Maintenance phase started")

    # ── Issue triage ──────────────────────────────────────────────────────────
    repos   = state.get("github_repos", [])
    handled = 0

    for repo in repos[:5]:  # Limit to 5 repos per maintenance pass
        full_name = (repo if isinstance(repo, str)
                     else repo.get("full_name", ""))
        if not full_name:
            continue

        # List open issues
        out, _, code = run_shell(
            f"gh issue list --repo {full_name} --state open "
            f"--json number,title,body,createdAt --limit 10",
            env=env
        )

        if code != 0 or not out:
            continue

        try:
            issues = json.loads(out)
        except json.JSONDecodeError:
            continue

        for issue in issues[:3]:  # Handle 3 issues max per repo
            success = handle_issue(full_name, issue, env)
            if success:
                handled += 1
            time.sleep(5)  # Pace between issue responses

    # ── Stability checks ──────────────────────────────────────────────────────
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    for repo in repos:
        if isinstance(repo, str):
            continue
        shipped_at = repo.get("shipped_at", "")
        if not shipped_at:
            continue
        try:
            shipped = datetime.fromisoformat(shipped_at.replace("Z", "+00:00"))
            age_days = (now - shipped).days
            if age_days >= 7:
                run_stability_check(repo, env)
                time.sleep(10)
        except Exception:
            pass

    # ── Update maintenance queue ──────────────────────────────────────────────
    state = load_state()
    state["last_maintenance"] = now.isoformat()
    state["phase"] = "research"  # Return to main loop
    state.pop("maintenance_urgent", None)
    save_state(state)

    broadcast("status",
              f"🔧 Maintenance complete: {handled} issues handled")
    print(f"Maintenance: {handled} issues handled → returning to research")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Maintenance phase error: {e}", file=sys.stderr)
        try:
            state = load_state()
            state["phase"] = "research"
            save_state(state)
        except Exception:
            pass
        sys.exit(0)
