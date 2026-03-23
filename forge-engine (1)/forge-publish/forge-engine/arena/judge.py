#!/usr/bin/env python3
"""FORGE Arena Judge — scores original vs fork, declares winner."""

import json, sys
from pathlib import Path

FORGE_DIR = Path.home() / ".forge"
ARENA_DIR = FORGE_DIR / "arena"

def judge(timestamp: str) -> dict:
    original_file = ARENA_DIR / f"results/original_{timestamp}.json"
    fork_file = ARENA_DIR / f"results/fork_{timestamp}.json"

    if not original_file.exists() or not fork_file.exists():
        # No results yet — default to original
        return {"winner": "original", "margin": 0,
                "reason": "results not found"}

    original = json.loads(original_file.read_text())
    fork = json.loads(fork_file.read_text())

    def score(r: dict) -> float:
        quality   = r.get("quality_score", 5.0)    # 0–10
        speed     = r.get("avg_task_seconds", 60)   # lower is better
        errors    = r.get("error_rate", 0.5)        # 0–1, lower is better

        # Normalize speed: 0s=10, 120s=0
        speed_score = max(0, 10 - (speed / 12))

        # Error score: 0 errors=10, all errors=0
        error_score = (1 - errors) * 10

        # Weighted composite
        return (quality * 0.5) + (speed_score * 0.3) + (error_score * 0.2)

    original_score = score(original)
    fork_score = score(fork)

    if original_score == 0:
        return {"winner": "original", "margin": 0,
                "reason": "could not score original"}

    margin = ((fork_score - original_score) / original_score) * 100

    result = {
        "winner": "fork" if fork_score > original_score else "original",
        "margin": round(abs(margin), 2),
        "original_score": round(original_score, 3),
        "fork_score": round(fork_score, 3),
        "reason": (
            f"fork scored {fork_score:.2f} vs original {original_score:.2f}"
        )
    }

    return result

if __name__ == "__main__":
    timestamp = sys.argv[1] if len(sys.argv) > 1 else ""
    if not timestamp:
        print(json.dumps({"winner": "original", "margin": 0,
                          "reason": "no timestamp provided"}))
        sys.exit(0)
    result = judge(timestamp)
    print(json.dumps(result))
