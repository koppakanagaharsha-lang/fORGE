#!/usr/bin/env python3
"""FORGE Phase: Research — reads sources, writes observations to state."""

import json, subprocess, sys, time, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone

FORGE_DIR = Path.home() / ".forge"
ENGINE    = FORGE_DIR / "engine"
STATE     = FORGE_DIR / "state.json"
PHANTOM   = ENGINE / "phantom/cdp.sh"
RELAY     = ENGINE / "relay/broadcast.sh"

def load_state():
    return json.loads(STATE.read_text())

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.returncode

def broadcast(event, msg):
    subprocess.run([str(RELAY), event, msg], capture_output=True)

def phantom(cmd, *args):
    full = f"bash {PHANTOM} {cmd} " + " ".join(f"'{a}'" for a in args)
    out, code = run(full)
    return out if code == 0 else None

def ensure_browser():
    if phantom("url") is None:
        run(f"bash {ENGINE}/phantom/start.sh")
        time.sleep(3)

def navigate_and_extract(url):
    if phantom("allowed", url) != "allowed":
        return None
    phantom("navigate", url)
    time.sleep(1)
    text = phantom("text")
    return text[:2000] if text else None

def web_search(query):
    try:
        q = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1"
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read())
            topics = [t.get("Text","") for t in d.get("RelatedTopics",[])[:5]]
            return "\n".join(t for t in topics if t)[:800]
    except Exception:
        return ""

def main():
    state  = load_state()
    notes  = list(state.get("notes", []))

    broadcast("phase_change", "🔬 Research started")
    ensure_browser()

    # Browser sources
    browser_sources = [
        ("github_trending",        "https://github.com/trending"),
        ("github_trending_python", "https://github.com/trending/python"),
        ("github_trending_ts",     "https://github.com/trending/typescript"),
        ("clawhub_new",            "https://clawhub.dev/skills?sort=new"),
        ("clawhub_popular",        "https://clawhub.dev/skills?sort=popular"),
        ("hackernews",             "https://news.ycombinator.com"),
        ("npmjs_agent",            "https://www.npmjs.com/search?q=ai-agent"),
        ("pypi_llm",               "https://pypi.org/search/?q=llm&o=-zscore"),
    ]

    for src_id, url in browser_sources:
        print(f"  [{src_id}]")
        text = navigate_and_extract(url)
        if text:
            notes.append({
                "source": src_id, "url": url,
                "content": text,
                "ts": datetime.now(timezone.utc).isoformat()
            })
        time.sleep(2)

    # Web search supplementary
    for q in [
        "trending AI agent developer tools github 2025",
        "LLM utility library popular npm pypi",
        "openclaw skill ideas missing gap",
    ]:
        result = web_search(q)
        if result:
            notes.append({
                "source": "web_search", "query": q,
                "content": result,
                "ts": datetime.now(timezone.utc).isoformat()
            })
        time.sleep(1)

    # Own open GitHub issues → maintenance queue
    gh_user, _ = run("gh api user --jq '.login' 2>/dev/null")
    for repo in state.get("github_repos", [])[:5]:
        repo_name = repo if isinstance(repo, str) else repo.get("name","")
        if not repo_name or not gh_user:
            continue
        raw, code = run(
            f"gh issue list --repo {gh_user}/{repo_name} "
            f"--state open --json number,title,createdAt --limit 10"
        )
        if code != 0 or not raw:
            continue
        try:
            for issue in json.loads(raw):
                queue = state.setdefault("maintenance_queue", [])
                existing_nums = [i.get("issue_number") for i in queue]
                if issue["number"] not in existing_nums:
                    queue.append({
                        "repo": repo_name,
                        "issue_number": issue["number"],
                        "title": issue["title"],
                        "created_at": issue["createdAt"]
                    })
                notes.append({
                    "source": "own_issue",
                    "repo": repo_name,
                    "issue_number": issue["number"],
                    "title": issue["title"],
                    "ts": datetime.now(timezone.utc).isoformat()
                })
        except Exception:
            pass

    state["notes"] = notes
    state["phase"] = "ideate"
    save_state(state)

    broadcast("phase_change",
        f"🔬 Research complete — {len(notes)} signals. Moving to ideation.")
    print(f"Research complete: {len(notes)} observations")
    return 0

if __name__ == "__main__":
    sys.exit(main())
