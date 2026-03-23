# ⚡ FORGE Autonomous Agent

> Shapes software. Does not stop. ✨

FORGE is an autonomous software development system that runs 24/7.
It researches, designs, implements via an MCP agentic loop, maintains published work, and evolves its own code through experimental forks and dynamic arenas. Every action reports to Telegram and OpenClaw simultaneously.

**WARNING: FORGE is an autonomous agent capable of self-mutation and arbitrary execution. Inherently risky. Monitor closely.**

---

## 🏛️ Architecture

```text
Core         Boot, loop, 5 phase handlers (research → ideate → build → maintain → publish)
AutoResearch Autonomous iteration loops mirroring karpathy/autoresearch (train.py iterations)
MCP          Agentic tool parity with Claude/GPT-5.4 (browser, antigravity, stitch, opencode)
Arena        Self-evolution via dynamic test-generation (builder.py) and instant deployment
Cortex       opencode orchestration with smart routing to gemini-3.1-flash-lite
UI           Forest Blue dashboard with glassmorphism and real-time monitoring
Relay        Dual native broadcast — Telegram Polling + OpenClaw simultaneously
```

---

## 🚀 Quick Start / Install

Install globally via NPM:
```bash
npm install -g git+https://github.com/koppakanagaharsha-lang/fORGE.git
forge install
forge start
```

Alternatively, clone directly:
```bash
git clone https://github.com/koppakanagaharsha-lang/fORGE.git
cd fORGE
```

Launch the **Forest Blue** Web UI:
Open `forge-engine (1)/forge-publish/forge-engine/web/index.html` in your browser.

---

## 🔑 Credentials — `~/.forge/.env`

FORGE requires the following credentials to route efficiently:

```bash
GEMINI_API_KEY=""        # Required. Get free at aistudio.google.com
GEMINI_API_KEY_2=""      # Optional — add more for key rotation
GITHUB_TOKEN=""
GITHUB_USERNAME=""
CLAWHUB_TOKEN=""
TELEGRAM_API_TOKEN=""
```

---

## 💬 Commands (Telegram or OpenClaw)

FORGE is managed universally either through OpenClaw or directly via Telegram. Send any of these commands to your bot:

| Command | Effect |
|---|---|
| `forge start` | Boot the core loop / OpenClaw Skill |
| `forge status` | Phase, keyring health, today's project count |
| `forge build [idea]` | Force deploy a specific feature / Arena test |
| `forge mutate` | Trigger Arena AutoResearch race now |
| `forge pause` / `resume` | Pause and resume operations |
| `forge why` | Explain current objective and model reasoning |
| `forge ui` | Request Antigravity UI generation |
| `forge browse [url]` | Instruct Phantom to scrape/navigate DOM |
| `[natural language]` | Send any request! FORGE will route it dynamically. |

---

## 🛠️ Service Management

```bash
systemctl --user status forge
tail -f ~/.forge/logs/forge.log
tail -f ~/.forge/logs/mcp.log
```

---

## 📦 Requirements

- Python 3.9+, Node.js 18+
- opencode: `npm install -g opencode-ai`
- Chromium: `sudo apt install chromium-browser`
- Gemini free-tier API key (3.1 Flash Lite routing)
- Telegram bot

---

## 📄 License
MIT
