# FORGE: Publishing to GitHub

Your `fORGE` autonomous agent, including the enhanced AutoResearch capabilities, native Telegram polling, OpenClaw skill integrations, and the Forest Blue UI, is **fully ready** to be published.

Here is how you can publish both the engine and the skill to GitHub as separate repositories or as a monorepo.

## Option 1: Monorepo (Recommended)
Publishing the entire `fORGE` directory as a single repository makes it easier to track the relationship between the engine and the OpenClaw skill.

1. **Initialize the Git Repository**
   Open your terminal in the `fORGE` root directory:
   ```bash
   cd /home/k-naga-harsha/fORGE
   git init
   ```

2. **Add and Commit All Files**
   ```bash
   git add .
   git commit -m "feat: initial commit of FORGE autonomous agent with AutoResearch, MCP tools, Telegram, and Forest Blue UI"
   ```

3. **Create a GitHub Repository**
   - Go to [GitHub](https://github.com/new).
   - Create a new repository named `fORGE`.
   - Do not initialize it with a README, .gitignore, or license (since you already have them locally).

4. **Push to GitHub**
   Copy the commands provided by GitHub to push an existing repository:
   ```bash
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/fORGE.git
   git push -u origin main
   ```

## Option 2: Publishing Engine and Skill Separately
If you want to maintain `forge-engine` and `forge-skill` as separate repositories:

**For the Engine:**
```bash
cd "/home/k-naga-harsha/fORGE/forge-engine (1)/forge-publish"
git init
git add .
git commit -m "feat: autonomous engine with AutoResearch and MCP tool extensions"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/forge-engine.git
git push -u origin main
```

**For the Skill:**
```bash
cd "/home/k-naga-harsha/fORGE/forge-skill/forge-publish"
git init
git add .
git commit -m "feat: OpenClaw skill with native Telegram routing and tool definitions"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/forge-skill.git
git push -u origin main
```

## Readiness Check
✅ **AutoResearch Loop:** Fully implemented in `core/phase_autoresearch.py`.
✅ **MCP Tools:** Schema and functions added (`browser`, `antigravity`, `stitch`, `opencode`).
✅ **Dynamic Arena:** `builder.py` and `test_harness.sh` deployment logic complete.
✅ **Light-models:** Cortex routed to `gemini-3.1-flash-lite`.
✅ **Telegram & OpenClaw:** Polling script added and `skill.yaml` heavily updated.
✅ **Forest Blue UI:** Built with slogans, symbols, and warnings in `web/index.html` and `web/style.css`.
✅ **Compilation:** All scripts passed syntax verification checks and are functionally integrated.

**Result:** Your custom agent is primed and completely ready for launch!
