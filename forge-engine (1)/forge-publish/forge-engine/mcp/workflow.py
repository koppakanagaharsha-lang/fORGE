#!/usr/bin/env python3
"""
FORGE Workflow Engine — Autonomous agentic execution loop.

This is what makes FORGE act like Claude Code rather than a code generator.
After opencode produces output, the workflow engine:
  1. Parses tool calls from the output
  2. Executes each tool via MCP
  3. Feeds results back into the next step
  4. Keeps looping until the task is done or it hits an error it can't solve
  5. Never stops to ask the human unless truly blocked

The loop mirrors Claude's agentic workflow:
  Think → Act (tool call) → Observe (result) → Think → Act → ...
"""

import json, re, sys, time, subprocess, os
from pathlib import Path
from typing import Optional
from mcp_client import call, log, _load_forge_env

FORGE_DIR = Path.home() / ".forge"
MAX_STEPS = 50      # Hard limit on steps per workflow
MAX_RETRIES = 3     # Retries per failing step before trying different approach

# Patterns to detect tool calls in opencode/LLM output
TOOL_CALL_PATTERNS = [
    # JSON block: ```json\n{"tool": "...", "args": {...}}\n```
    re.compile(r'```(?:json)?\s*\n(\{[^`]+\})\s*\n```', re.DOTALL),
    # XML-style: <tool_call>{"tool": "..."}</tool_call>
    re.compile(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', re.DOTALL),
    # Direct JSON on its own line
    re.compile(r'^(\{"tool":\s*"[^"]+".+\})\s*$', re.MULTILINE),
    # MCP format: <use_mcp_tool>...</use_mcp_tool>
    re.compile(r'<use_mcp_tool>\s*(\{.*?\})\s*</use_mcp_tool>', re.DOTALL),
]

# Patterns to detect "task complete" signals
DONE_PATTERNS = [
    re.compile(r'\b(task complete|done|finished|all done|complete)\b', re.I),
    re.compile(r'\b(no more (steps|actions|tasks))\b', re.I),
    re.compile(r'\b(successfully (built|created|deployed|published|committed))\b', re.I),
]


class WorkflowStep:
    def __init__(self, tool: str, args: dict, raw: str = ""):
        self.tool    = tool
        self.args    = args
        self.raw     = raw
        self.result  = None
        self.retries = 0

    def execute(self) -> dict:
        self.result = call(self.tool, **self.args)
        return self.result


class WorkflowResult:
    def __init__(self):
        self.steps: list[WorkflowStep] = []
        self.success = False
        self.final_output = ""
        self.error = ""
        self.files_written: list[str] = []
        self.commands_run: list[str] = []


def extract_tool_calls(text: str) -> list[WorkflowStep]:
    """Parse tool calls from LLM output."""
    steps = []
    seen  = set()

    for pattern in TOOL_CALL_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(1).strip()
            if raw in seen:
                continue
            seen.add(raw)
            try:
                obj  = json.loads(raw)
                tool = obj.get("tool") or obj.get("name") or obj.get("function")
                args = obj.get("args") or obj.get("input") or obj.get("parameters") or {}
                if tool:
                    steps.append(WorkflowStep(tool, args, raw))
            except json.JSONDecodeError:
                pass

    return steps


def is_done(text: str) -> bool:
    """Check if the LLM is signalling task completion."""
    for pat in DONE_PATTERNS:
        if pat.search(text):
            return True
    return False


def invoke_cortex(task: str, context: str = "", model: str = None) -> str:
    """
    Call opencode with the current task and accumulated context.
    Returns the raw text output.
    """
    env = {**os.environ, **_load_forge_env()}

    # Get model from keyring-aware cortex
    invoke = str(FORGE_DIR / "engine/cortex/invoke.sh")

    full_task = task
    if context:
        full_task = f"Current context:\n{context}\n\n---\nNext step:\n{task}"

    args = [invoke, "--task", full_task]
    if model:
        args += ["--model", model]

    result = subprocess.run(
        args, capture_output=True, text=True,
        timeout=300, env=env
    )
    return result.stdout.strip()


class AutoWorkflow:
    """
    Autonomous workflow that loops until the task is complete.
    This is FORGE acting like a human developer — not just generating code
    but running it, reading the output, fixing problems, trying again.
    """

    def __init__(self, task: str, cwd: str = None,
                 model: str = None, max_steps: int = MAX_STEPS):
        self.task      = task
        self.cwd       = cwd or str(Path.home() / "forge-workspace")
        self.model     = model
        self.max_steps = max_steps
        self.result    = WorkflowResult()
        self.context   = []   # Accumulated step results as context
        self.step_num  = 0

    def _context_str(self) -> str:
        """Build context string from recent steps (last 5)."""
        recent = self.context[-5:]
        lines  = []
        for entry in recent:
            lines.append(f"Step {entry['step']}: {entry['tool']}")
            if entry.get("stdout"):
                lines.append(f"  Output: {entry['stdout'][:300]}")
            if entry.get("error"):
                lines.append(f"  Error: {entry['error'][:200]}")
            if entry.get("ok") is False:
                lines.append(f"  FAILED")
        return "\n".join(lines)

    def _handle_result(self, step: WorkflowStep) -> bool:
        """Process a tool result, update context. Returns True if ok."""
        r = step.result or {}
        ok = r.get("ok", False)

        entry = {
            "step":   self.step_num,
            "tool":   step.tool,
            "args":   step.args,
            "ok":     ok,
            "stdout": r.get("stdout") or r.get("content", ""),
            "stderr": r.get("stderr", ""),
            "error":  r.get("error", ""),
        }
        self.context.append(entry)
        log(f"step {self.step_num} {step.tool}: {'ok' if ok else 'FAIL'}")

        if step.tool == "write_file":
            self.result.files_written.append(step.args.get("path", ""))
        if step.tool == "shell":
            self.result.commands_run.append(step.args.get("cmd", ""))

        return ok

    def _recovery_prompt(self, failed_step: WorkflowStep) -> str:
        """Generate a recovery prompt when a step fails."""
        err = (failed_step.result or {}).get("error") or \
              (failed_step.result or {}).get("stderr") or "unknown error"

        return (
            f"The previous step failed.\n"
            f"Tool: {failed_step.tool}\n"
            f"Args: {json.dumps(failed_step.args)}\n"
            f"Error: {err[:500]}\n\n"
            f"Original task: {self.task}\n\n"
            f"Think about why this failed and try a different approach. "
            f"Use tool calls to fix the problem."
        )

    def run(self) -> WorkflowResult:
        """
        Main agentic loop.
        Keeps calling LLM → execute tools → feed back results → repeat.
        """
        log(f"Workflow start: {self.task[:80]}")

        current_prompt = self.task
        consecutive_failures = 0

        for _ in range(self.max_steps):
            self.step_num += 1

            # Get next action from LLM
            llm_output = invoke_cortex(
                current_prompt,
                context=self._context_str(),
                model=self.model
            )

            if not llm_output:
                log("Empty LLM output — stopping")
                break

            self.result.final_output = llm_output

            # Check if task is complete
            if is_done(llm_output) and not extract_tool_calls(llm_output):
                log(f"Task complete signal at step {self.step_num}")
                self.result.success = True
                break

            # Extract and execute tool calls
            steps = extract_tool_calls(llm_output)

            if not steps:
                # No tool calls — LLM may be reasoning or done
                if is_done(llm_output):
                    self.result.success = True
                    break
                # Ask it to take an action
                current_prompt = (
                    "You need to take a concrete action. "
                    "Use a tool call to proceed with the task. "
                    f"Task: {self.task}"
                )
                continue

            # Execute each tool call in sequence
            all_ok = True
            for step in steps:
                step.execute()
                ok = self._handle_result(step)

                if not ok:
                    all_ok = False
                    consecutive_failures += 1

                    if consecutive_failures >= MAX_RETRIES:
                        # Completely different approach needed
                        log(f"3 consecutive failures — requesting new approach")
                        current_prompt = (
                            f"The current approach isn't working after {MAX_RETRIES} attempts.\n"
                            f"Task: {self.task}\n"
                            f"Last error: {(step.result or {}).get('error', 'unknown')}\n"
                            f"Take a fundamentally different approach."
                        )
                        consecutive_failures = 0
                        break

                    current_prompt = self._recovery_prompt(step)
                    break
                else:
                    consecutive_failures = 0

            if all_ok:
                # All steps succeeded — ask what to do next
                outputs = [
                    str(e.get("stdout") or e.get("content", ""))[:200]
                    for e in self.context[-len(steps):]
                ]
                current_prompt = (
                    f"Steps completed successfully.\n"
                    f"Results: {chr(10).join(outputs)}\n\n"
                    f"Original task: {self.task}\n\n"
                    f"What is the next step? If the task is complete, say 'Task complete'."
                )

        else:
            log(f"Workflow hit max steps ({self.max_steps})")
            self.result.error = f"Exceeded max steps ({self.max_steps})"

        return self.result


def run_workflow(task: str, cwd: str = None,
                 model: str = None, max_steps: int = MAX_STEPS) -> WorkflowResult:
    """Convenience function to run an autonomous workflow."""
    wf = AutoWorkflow(task, cwd=cwd, model=model, max_steps=max_steps)
    return wf.run()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not task:
        print("Usage: workflow.py 'task description'")
        sys.exit(1)

    result = run_workflow(task)

    print(f"\n{'='*50}")
    print(f"Workflow complete: {'✓' if result.success else '✗'}")
    print(f"Steps executed: {len(result.steps)}")
    print(f"Files written: {result.files_written}")
    print(f"Commands run: {len(result.commands_run)}")
    if result.error:
        print(f"Error: {result.error}")
    print(f"{'='*50}\n")
    print(result.final_output)
