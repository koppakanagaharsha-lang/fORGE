# ⚡ FORGE

**Autonomous AI developer. Thinks. Builds. Evolves.**

FORGE ships 5 production-quality software projects per day, maintains
everything it publishes, answers GitHub issues like the developer who
wrote the code, and improves itself through a fork-race-evolve system.
It runs indefinitely. It does not stop.

---

## Before installing this skill

Install the FORGE engine on your Ubuntu machine first:

```bash
export FORGE_GITHUB_USER=your-username
curl -fsSL https://raw.githubusercontent.com/$FORGE_GITHUB_USER/forge/main/install.sh | bash
```

Then install this skill and say:

```
forge start
```

---

## What FORGE does

**Builds 5 projects per day** in: AI agent frameworks, LLM developer
utilities, coding automation, OpenClaw skills, developer tooling.
Every project is real, tested, and published.

**MCP agentic build loop** — after opencode generates code, FORGE
executes it, reads the output, fixes errors, iterates — exactly like
Claude Code. Uses read_file, write_file, edit_file, shell, git tools
in a Think → Act → Observe loop until the task is done.

**Multi-key rotation** — add multiple Gemini and GitHub keys.
When one hits a rate limit FORGE rotates to the next automatically.
No interruption unless all keys are exhausted.

**Self-evolution via Arena** — every 10 projects, FORGE clones itself,
mutates a component, races original vs fork, applies the winner.
The safety wall cannot be weakened by mutation.

**Full maintenance** — reads GitHub issues, replies as the developer
who wrote the code, pushes fixes, runs weekly stability checks.

**Dual gateway** — every action reports to Telegram and OpenClaw
simultaneously. Command FORGE from either channel.

---

## Requirements

- FORGE engine installed (see above)
- OpenClaw with shell, file, browser_cdp, git tools
- opencode: `npm install -g opencode-ai`
- Ubuntu 22.04 / 24.04

---

## Commands (Telegram or OpenClaw)

`forge status` — phase, keyring, today's count
`forge build [X]` — build something specific
`forge mutate` — trigger Arena race immediately
`forge pause` / `forge resume`
`forge why` — what is running and why
`forge log [N]` — last N log lines
`forge keys status` / `forge keys add`
`forge issue [repo] [N]` — handle a specific issue

---

## License

MIT
