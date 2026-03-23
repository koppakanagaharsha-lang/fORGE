#!/usr/bin/env python3
"""
FORGE opencode Bridge — MCP-aware code generation.

Instead of just calling opencode and hoping it outputs correct code,
this bridge:
  1. Gives opencode the MCP tool schema so it knows what tools exist
  2. Runs opencode in an agentic loop — it can emit tool calls
  3. Executes those tool calls via mcp_client
  4. Feeds results back to opencode for the next step
  5. Continues until opencode signals completion

This is how Claude Code works. FORGE now works the same way.
"""

import json, os, sys, subprocess, time
from pathlib import Path

# Add mcp dir to path
sys.path.insert(0, str(Path(__file__).parent))
from mcp_client import call, _load_forge_env
from workflow import extract_tool_calls, is_done

FORGE_DIR  = Path.home() / ".forge"
ENGINE     = FORGE_DIR / "engine"
MCP_SCHEMA = Path(__file__).parent / "mcp_servers.json"
MAX_ROUNDS = 20

def get_mcp_system_prompt() -> str:
    """Build system prompt that tells opencode about available MCP tools."""
    schema = json.loads(MCP_SCHEMA.read_text()) if MCP_SCHEMA.exists() else {}

    tool_descriptions = []
    for server_name, server in schema.get("mcpServers", {}).items():
        for tool in server.get("tools", []):
            props = tool.get("inputSchema", {}).get("properties", {})
            param_list = ", ".join(
                f"{k}: {v.get('type','any')}"
                for k, v in props.items()
            )
            tool_descriptions.append(
                f"  {tool['name']}({param_list})\n"
                f"    → {tool['description']}"
            )

    tools_text = "\n".join(tool_descriptions)

    return f"""You are FORGE's coding engine, running in an agentic loop.

You have access to these tools. When you need to take an action,
emit a tool call as a JSON block wrapped in triple backticks:

```json
{{"tool": "tool_name", "args": {{"arg1": "value1"}}}}
```

Available tools:
{tools_text}

You will be called multiple times in a loop. Each call you will receive:
- The original task
- Results of any previous tool calls
- What to do next

When the task is fully complete, say "Task complete." and stop emitting tool calls.

Never ask the human for input. If you hit a problem, try a different approach.
Always check your work by reading files after writing them.
Always run code after writing it to verify it works."""


def run_agentic(task: str, cwd: str = None,
                model: str = None, context_files: list = None) -> dict:
    """
    Run opencode in an MCP-aware agentic loop.
    Returns dict with: success, output, files_written, steps
    """
    env = {**os.environ, **_load_forge_env()}
    cwd = cwd or str(Path.home() / "forge-workspace")

    system_prompt = get_mcp_system_prompt()
    context = []
    files_written = []
    steps_taken = 0

    # Pre-load context files if specified
    file_context = ""
    if context_files:
        for cf in context_files:
            p = Path(cf)
            if p.exists():
                content = p.read_text(errors="replace")[:3000]
                file_context += f"\n--- {p.name} ---\n{content}\n"

    # Build initial prompt
    current_prompt = f"{system_prompt}\n\n"
    if file_context:
        current_prompt += f"Reference files:\n{file_context}\n\n"
    current_prompt += f"Task: {task}"

    for round_num in range(MAX_ROUNDS):
        steps_taken += 1

        # Call opencode
        result = subprocess.run(
            [str(ENGINE / "cortex/invoke.sh"),
             "--task", current_prompt] + (["--model", model] if model else []),
            capture_output=True, text=True,
            timeout=300, env=env, cwd=cwd
        )
        output = result.stdout.strip()

        if not output:
            break

        # Check for completion
        if is_done(output) and not extract_tool_calls(output):
            return {
                "success": True,
                "output": output,
                "files_written": files_written,
                "steps": steps_taken,
                "rounds": round_num + 1,
            }

        # Extract and execute tool calls
        tool_calls = extract_tool_calls(output)

        if not tool_calls:
            # No tool calls and not done — probably pure text output
            # Check if it wrote any code we should capture
            if "```" in output:
                # Extract code blocks and write them
                import re
                code_blocks = re.findall(
                    r'```(?:python|javascript|typescript|bash|sh)?\s*\n(.*?)\n```',
                    output, re.DOTALL
                )
                if code_blocks:
                    # Try to figure out filename from context
                    pass
            # Continue the loop asking for actions
            current_prompt = (
                f"Continue the task. Use tool calls to take concrete actions.\n"
                f"Task: {task}\n"
                f"Previous output:\n{output[:500]}"
            )
            continue

        # Execute tool calls and collect results
        results_summary = []
        all_succeeded = True

        for tc in tool_calls:
            tc.execute()
            r = tc.result or {}
            ok = r.get("ok", False)

            if not ok:
                all_succeeded = False

            # Track files written
            if tc.tool == "write_file" and ok:
                files_written.append(tc.args.get("path", ""))

            # Build result summary
            stdout = r.get("stdout") or r.get("content", "")
            stderr = r.get("stderr", "")
            error  = r.get("error", "")

            summary = f"Tool: {tc.tool} → {'OK' if ok else 'FAILED'}"
            if stdout:
                summary += f"\nOutput: {stdout[:400]}"
            if stderr:
                summary += f"\nStderr: {stderr[:200]}"
            if error:
                summary += f"\nError: {error[:200]}"

            results_summary.append(summary)
            context.append({"tool": tc.tool, "ok": ok,
                            "stdout": stdout[:200], "error": error})

        # Build next prompt with results
        results_text = "\n\n".join(results_summary)
        if all_succeeded:
            current_prompt = (
                f"Tool calls succeeded.\n\n"
                f"Results:\n{results_text}\n\n"
                f"Original task: {task}\n\n"
                f"What is the next step? If complete, say 'Task complete.'"
            )
        else:
            current_prompt = (
                f"Some tool calls failed.\n\n"
                f"Results:\n{results_text}\n\n"
                f"Original task: {task}\n\n"
                f"Fix the failures. Try a different approach if needed."
            )

    return {
        "success": False,
        "output": output if "output" in dir() else "",
        "files_written": files_written,
        "steps": steps_taken,
        "error": f"Did not complete in {MAX_ROUNDS} rounds",
    }


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not task:
        print("Usage: opencode_bridge.py 'task'")
        sys.exit(1)
    result = run_agentic(task)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)
