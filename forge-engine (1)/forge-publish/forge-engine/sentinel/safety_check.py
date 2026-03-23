#!/usr/bin/env python3
"""
FORGE Sentinel — Safety Check for Arena Forks
Ensures no mutation weakens the safety wall or introduces dangerous patterns.
Called by arena/race.sh before judging.
"""
import sys, json
from pathlib import Path

ENGINE = Path.home() / ".forge/engine"

IMMUTABLE_FILES = [
    "core/safety.py",
    "sentinel/safety_check.py",
]

FORBIDDEN_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    ":(){ :|:& };:",
    "mkfs",
    "DROP TABLE",
    "os.system('rm",
    "subprocess.run(['rm', '-rf'",
]

def check_fork(fork_dir: str) -> tuple[bool, str]:
    fork = Path(fork_dir)

    for immutable in IMMUTABLE_FILES:
        original = ENGINE / immutable
        forked   = fork / immutable

        if not original.exists():
            continue

        if not forked.exists():
            return False, f"Immutable file removed: {immutable}"

        orig_lines = len(original.read_text().splitlines())
        fork_lines = len(forked.read_text().splitlines())

        # Safety files cannot shrink by more than 5%
        threshold = int(orig_lines * 0.95)
        if fork_lines < threshold:
            return False, (
                f"Safety file {immutable} shrank: "
                f"{orig_lines} → {fork_lines} lines"
            )

    # Scan for forbidden patterns in any modified file
    for f in fork.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix not in [".py", ".sh", ".js", ".ts"]:
            continue
        try:
            content = f.read_text(errors="ignore")
            for pat in FORBIDDEN_PATTERNS:
                if pat in content:
                    return False, f"Forbidden pattern in {f.name}: {pat}"
        except Exception:
            pass

    return True, "fork passed safety check"

if __name__ == "__main__":
    fork_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    if not fork_dir:
        print("FAIL: no fork directory provided")
        sys.exit(1)
    passed, reason = check_fork(fork_dir)
    print(f"{'PASS' if passed else 'FAIL'}: {reason}")
    sys.exit(0 if passed else 1)
