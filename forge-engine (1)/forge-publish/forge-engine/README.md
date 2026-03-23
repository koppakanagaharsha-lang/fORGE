# ⚡ FORGE Engine

> Autonomous AI developer. Thinks. Builds. Evolves.

FORGE is an autonomous software development system that runs 24/7.
It researches, designs, implements via an MCP agentic loop, maintains
published work, and evolves its own code through a fork-race system.
Every action reports to Telegram and OpenClaw simultaneously.

This repo is the **engine** — the persistent background process.
The **brain** (ClawHub skill) runs inside OpenClaw.

---

## Architecture

```
Core      Boot, loop, 5 phase handlers (research → ideate → build → maintain → publish)
MCP       Agentic tool-use — opencode loops with read/write/shell/git, like Claude Code
Keyring   Multi-key rotation — mirrors OpenClaw's native key router
Arena     Self-evolution — fork → mutate → race → keep winner
Cortex    opencode orchestration with model selection
Phantom   Headless Chrome DevTools for research (strict domain allowlist)
Relay     Dual broadcast — Telegram + OpenClaw simultaneously
Sentinel  Monitors arena forks, memory, runaway processes
```

---

## Install

```bash
export FORGE_GITHUB_USER=your-username
curl -fsSL https://raw.githubusercontent.com/$FORGE_GITHUB_USER/forge/main/install.sh | bash
```

Then install the FORGE skill from ClawHub and say `forge start`.
The setup wizard handles all account configuration.

---

## Credentials — `~/.forge/.env`

```bash
GEMINI_API_KEY=""        # Required. Get free at aistudio.google.com
GEMINI_API_KEY_2=""      # Optional — add more for key rotation
GITHUB_TOKEN=""
GITHUB_USERNAME=""
CLAWHUB_TOKEN=""
CLAWHUB_USERNAME=""
TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHAT_ID=""
```

Or use the interactive wizard: `bash ~/.forge/engine/keyring/setup_wizard.sh`

---

## Commands (Telegram or OpenClaw)

| Command | Effect |
|---|---|
| `forge status` | Phase, keyring health, today's count |
| `forge build [idea]` | Force build something specific |
| `forge mutate` | Trigger Arena race now |
| `forge pause` / `forge resume` | Pause and resume |
| `forge why` | What is running and why |
| `forge log [N]` | Last N lines of forge.log |
| `forge keys status` | All keys: available / cooling / disabled |
| `forge keys add` | Add more keys for rotation |
| `forge issue [repo] [N]` | Handle a specific GitHub issue |

---

## Service management

```bash
systemctl --user status forge
bash ~/.forge/engine/scripts/status.sh
tail -f ~/.forge/logs/forge.log
tail -f ~/.forge/logs/mcp.log
systemctl --user restart forge
bash ~/.forge/engine/uninstall.sh
```

---

## Requirements

- Ubuntu 22.04 / 24.04 with systemd
- Python 3.9+, Node.js 18+
- opencode: `npm install -g opencode-ai`
- Chromium: `sudo apt install chromium-browser`
- Gemini free-tier API key
- Telegram bot

---

## License

MIT
