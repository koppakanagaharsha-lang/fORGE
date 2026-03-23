#!/usr/bin/env python3
"""
FORGE Error Recovery — classifies errors and returns recovery strategy.
Called when a phase exits with a non-zero code.
"""

import re, sys, json
from pathlib import Path

FORGE_DIR = Path.home() / ".forge"

STRATEGIES = {
    "rate_limit": {
        "patterns": [
            r"429", r"rate.?limit", r"quota exceeded",
            r"resource exhausted", r"too many requests"
        ],
        "action": "pause_60",
        "exit_code": 42,
        "message": "Rate limit hit. Pausing 60s."
    },
    "network": {
        "patterns": [
            r"connection refused", r"timeout", r"network unreachable",
            r"name resolution", r"ssl", r"certificate"
        ],
        "action": "retry_3",
        "exit_code": 0,
        "message": "Network error. Retrying up to 3 times."
    },
    "permission": {
        "patterns": [
            r"permission denied", r"access denied", r"not permitted",
            r"operation not allowed"
        ],
        "action": "check_paths",
        "exit_code": 0,
        "message": "Permission denied. Checking paths."
    },
    "not_found": {
        "patterns": [
            r"no such file", r"file not found", r"not found",
            r"command not found", r"module not found"
        ],
        "action": "install_or_create",
        "exit_code": 0,
        "message": "Resource not found. Installing or recreating."
    },
    "syntax": {
        "patterns": [
            r"syntax error", r"unexpected token", r"parse error",
            r"invalid syntax", r"unterminated"
        ],
        "action": "fix_and_retry",
        "exit_code": 0,
        "message": "Syntax error. Reading and fixing."
    },
    "cve": {
        "patterns": [
            r"critical.*vulnerability", r"high.*cve", r"security.*advisory"
        ],
        "action": "update_deps",
        "exit_code": 0,
        "message": "Security vulnerability found. Updating dependencies."
    },
    "opencode": {
        "patterns": [
            r"opencode.*failed", r"opencode.*error", r"cortex.*exit"
        ],
        "action": "rephrase_task",
        "exit_code": 0,
        "message": "opencode failed. Rephrasing task with more context."
    },
    "unknown": {
        "patterns": [],
        "action": "log_and_continue",
        "exit_code": 0,
        "message": "Unknown error. Logging and continuing."
    }
}

def classify(error_text: str) -> dict:
    error_lower = error_text.lower()
    for name, strategy in STRATEGIES.items():
        if name == "unknown":
            continue
        for pattern in strategy["patterns"]:
            if re.search(pattern, error_lower):
                return {"type": name, **strategy}
    return {"type": "unknown", **STRATEGIES["unknown"]}

def record_error(error_text: str, phase: str, attempt: int) -> dict:
    """Record error in state and return recovery strategy."""
    strategy = classify(error_text)

    state_file = FORGE_DIR / "state.json"
    try:
        state = json.loads(state_file.read_text())
        errors = state.setdefault("recent_errors", [])
        errors.append({
            "phase": phase,
            "type": strategy["type"],
            "attempt": attempt,
            "message": error_text[:200]
        })
        # Keep last 20 errors
        state["recent_errors"] = errors[-20:]
        state_file.write_text(json.dumps(state, indent=2))
    except Exception:
        pass

    return strategy

if __name__ == "__main__":
    error = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    result = classify(error)
    print(json.dumps(result))
    sys.exit(result["exit_code"])
