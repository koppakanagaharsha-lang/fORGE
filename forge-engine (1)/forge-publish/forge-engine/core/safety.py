#!/usr/bin/env python3
"""
FORGE Safety Wall — immutable. Cannot be weakened by Arena mutations.
Called before every publish. Returns pass/fail with specific reason.
"""

import re, sys, subprocess
from pathlib import Path

DANGEROUS_CMDS = [
    "rm -rf /", "rm -rf ~", "mkfs", "dd if=",
    ":(){ :|:& };:", "chmod 777 /", "sudo rm -rf",
]

CREDENTIAL_PATTERNS = [
    r'(api_key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{16,}',
    r'(token|secret)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{16,}',
    r'sk-[a-zA-Z0-9]{32,}',
    r'AIza[0-9A-Za-z\-_]{35}',
]

def check(project_dir: str) -> tuple:
    d = Path(project_dir)
    if not d.exists():
        return False, f"Project directory not found: {project_dir}"

    for fn in [
        _no_credentials, _has_gitignore, _has_env_example,
        _no_dangerous_commands, _audit_clean, _has_readme,
    ]:
        ok, reason = fn(d)
        if not ok:
            return False, reason

    return True, "all checks passed"

def _no_credentials(d):
    for f in d.rglob("*"):
        if not f.is_file():
            continue
        if ".git" in str(f):
            continue
        if f.suffix not in [".py",".js",".ts",".sh",".yaml",".json",".env"]:
            continue
        if ".env.example" in f.name:
            continue
        try:
            content = f.read_text(errors="ignore")
            for pat in CREDENTIAL_PATTERNS:
                if re.search(pat, content, re.I):
                    return False, f"Possible credential in {f.name}"
        except Exception:
            pass
    return True, ""

def _has_gitignore(d):
    gi = d / ".gitignore"
    if not gi.exists():
        return False, ".gitignore missing"
    if ".env" not in gi.read_text():
        return False, ".env not in .gitignore"
    return True, ""

def _has_env_example(d):
    has_env = any(
        f.name in (".env", ".env.local") and f.stat().st_size > 0
        for f in d.glob(".*") if f.is_file()
    )
    if has_env and not (d / ".env.example").exists():
        return False, ".env exists but .env.example missing"
    return True, ""

def _no_dangerous_commands(d):
    for f in d.rglob("*.sh"):
        try:
            content = f.read_text(errors="ignore")
            for cmd in DANGEROUS_CMDS:
                if cmd in content:
                    return False, f"Dangerous command in {f.name}: {cmd}"
        except Exception:
            pass
    return True, ""

def _audit_clean(d):
    if (d / "package.json").exists():
        r = subprocess.run(
            ["npm", "audit", "--audit-level=critical"],
            cwd=str(d), capture_output=True, text=True
        )
        if r.returncode != 0 and "critical" in r.stdout.lower():
            return False, "npm audit: critical CVE"
    return True, ""

def _has_readme(d):
    readme = d / "README.md"
    if not readme.exists():
        return False, "README.md missing"
    if len(readme.read_text().strip()) < 80:
        return False, "README.md too short"
    return True, ""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: safety.py <project_dir>")
        sys.exit(1)
    ok, reason = check(sys.argv[1])
    print(f"{'PASS' if ok else 'FAIL'}: {reason}")
    sys.exit(0 if ok else 1)
