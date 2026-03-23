#!/usr/bin/env python3
"""FORGE Arena Builder
Dynamically generates a task suite (arena) based on a user's request.
"""
import os, sys, json, subprocess
from pathlib import Path

FORGE_DIR = Path.home() / ".forge"
ENGINE    = FORGE_DIR / "engine"
TASKS_FILE = ENGINE / "arena/task_suite.json"

def build_arena(request: str):
    prompt = (
        "You are the FORGE Arena Builder. The user needs the following capability tested and built: "
        f"'{request}'\n"
        "Generate a JSON array of 3-5 tasks to test this capability thoroughly. Each task must have:\n"
        '- "id": string identifier\n'
        '- "type": string (e.g. "python_function", "javascript", "shell_script")\n'
        '- "prompt": string describing the specific coding task\n'
        '- "expect_contains": array of strings that MUST be in the correct output code.\n'
        "Output ONLY the JSON array inside a ```json block."
    )
    
    print(f"Building custom arena for request: {request}")
    res = subprocess.run(
        [str(ENGINE / "cortex/invoke.sh"), "--task", prompt, "--model", "gemini-3.1-flash-lite"],
        capture_output=True, text=True
    )
    
    import re
    block = re.search(r"```(?:json)?\n(.*?)\n```", res.stdout, re.DOTALL)
    if block:
        try:
            tasks = json.loads(block.group(1).strip())
            # overwrite tasks file
            TASKS_FILE.write_text(json.dumps(tasks, indent=2))
            print(f"Successfully generated {len(tasks)} tasks.")
            return True
        except json.JSONDecodeError:
            print("Failed to parse JSON")
            return False
    else:
        print("Failed to get JSON block from Cortex")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: builder.py 'user request'")
        sys.exit(1)
    
    success = build_arena(sys.argv[1])
    sys.exit(0 if success else 1)
