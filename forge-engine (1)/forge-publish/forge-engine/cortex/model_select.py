#!/usr/bin/env python3
"""
FORGE Cortex — Model Selection
Chooses the optimal Gemini model for each task type.
Balances quality against free-tier quota.
"""

import sys, re

# Model catalog
FLASH_2   = "gemini-2.0-flash"
FLASH_15  = "gemini-1.5-flash"
FLASH_31_LITE = "gemini-3.1-flash-lite"
PRO_15    = "gemini-1.5-pro"

def select(task: str) -> str:
    """Select the best model for a given task description."""
    t = task.lower()

    # High-complexity: use best available
    if any(kw in t for kw in [
        "architect", "design pattern", "algorithm", "system design",
        "security", "performance critical", "concurrent", "distributed",
        "mutation", "evolve", "judge", "evaluate quality", "compare",
        "debug complex", "trace error", "root cause"
    ]):
        return FLASH_2

    # UI and visual reasoning
    if any(kw in t for kw in [
        "ui", "interface", "component", "layout", "design system",
        "css", "animation", "responsive", "accessibility", "ux"
    ]):
        return FLASH_2

    # Standard implementation — quota-efficient
    if any(kw in t for kw in [
        "implement", "create function", "write test", "add method",
        "refactor", "rename", "extract", "boilerplate", "scaffold",
        "crud", "api endpoint", "route", "middleware", "api", "opencode",
        "antigravity", "stitch"
    ]):
        return FLASH_31_LITE

    # Documentation and README
    if any(kw in t for kw in [
        "readme", "documentation", "docstring", "comment", "explain"
    ]):
        return FLASH_15

    # Default: flash-2 for unknown tasks (better to over-qualify)
    return FLASH_2

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    print(select(task))
