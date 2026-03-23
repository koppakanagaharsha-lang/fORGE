# FORGE Engine — Changelog

## v1.0.0 — Initial Release

### Modules

**Core**
- `boot.py` — Startup sequence, day rollover, maintenance urgency check
- `loop.py` — Main work cycle: polls commands, runs sentinel, routes to phase handler
- `phase_research.py` — Reads GitHub trending, ClawHub, HN, npm, PyPI, own issues
- `phase_ideate.py` — Generates 5 candidates, scores on 6 dimensions, picks winner
- `phase_build.py` — Design → build (MCP agentic) → test → safety → publish pipeline
- `phase_maintenance.py` — GitHub issue triage, replies, stability checks
- `safety.py` — Pre-publish safety wall (immutable, cannot be weakened by Arena)
- `error_recovery.py` — Classifies errors and returns recovery strategies

**Arena** — self-evolution via fork/race/evolve
- `race.sh` — Clone → mutate → safety check → test harness → judge → apply/discard
- `judge.py` — Scores original vs fork on quality/speed/error-rate
- `test_harness.sh` — Runs both versions against identical task/edge suites
- `task_suite.json` / `edge_suite.json` — Standard test cases for Arena races

**Cortex** — opencode orchestration
- `invoke.sh` — Key-rotating opencode invocation with rate-limit detection
- `model_select.py` — Routes tasks to optimal Gemini model by type
- `configure.sh` — Configures opencode to use Gemini API
- `verify.sh` — Verifies opencode installation

**Keyring** — multi-key rotation (mirrors OpenClaw's native key router)
- `keyring.py` — Per-key RPM tracking, cooldown, stats persistence, rotation
- `rotate.sh` — Shell interface for keyring operations
- `setup_wizard.sh` — Interactive key addition wizard

**MCP** — agentic tool use loop (mirrors Claude Code)
- `mcp_client.py` — Tool implementations: read/write/edit files, shell, git, fetch
- `workflow.py` — Think → Act → Observe loop with recovery
- `opencode_bridge.py` — MCP-aware opencode wrapper with tool schema injection
- `mcp_servers.json` — Tool registry in standard MCP format

**Phantom** — Chrome DevTools Protocol (research only, domain allowlist)
- `cdp.py` — Full CDP client with domain enforcement
- `cdp.sh` — Shell wrapper
- `start.sh` — Launches headless Chromium on port 9222
- `detect.sh` — Detects available Chromium binary

**Relay** — dual-channel reporting (Telegram + OpenClaw)
- `broadcast.sh` — Sends to both channels simultaneously, rotates Telegram keys
- `poll.sh` — Polls Telegram for commands, executes them
- `send.sh` — Raw Telegram message sender
- `configure_openclaw.sh` — Sets up OpenClaw callback URL
- `ping_openclaw.sh` — Tests OpenClaw bridge

**Sentinel** — monitoring and safety
- `monitor.sh` — Kills stale Arena forks, checks memory, enforces single runner
- `safety_check.py` — Validates Arena forks before judging

**Scripts**
- `start.sh` — Main runner (systemd entry point)
- `stop.sh` — Graceful stop
- `status.sh` — Human-readable status report
- `install_dep.sh` — Installs individual dependencies
- `validate_key.py` — Validates API keys (Gemini, GitHub, Telegram)
- Plus: install_gh.sh, install_claw.sh, configure_opencode.sh,
  setup_browser.sh, stability_check.sh, start_runner.sh, uninstall.sh

**Top-level**
- `install.sh` — One-command engine installer
- `uninstall.sh` — Clean removal with optional state preservation
- `EVOLUTION.md` — Log of all Arena mutations applied
- `.env.example` — Credential template (safe to commit)
- `.gitignore` — Excludes credentials, logs, arena forks, pycache
- `.github/workflows/ci.yml` — CI: syntax checks, credential scan, safety wall verification
