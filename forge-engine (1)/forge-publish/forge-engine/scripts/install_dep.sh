#!/usr/bin/env bash
# FORGE — install a named dependency
# Usage: install_dep.sh [gh|claw|opencode|chromium|jq]

DEP="${1:-}"

case "$DEP" in
  gh)
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt-get update -qq && sudo apt-get install gh -y -qq
    gh --version
    ;;
  claw)
    npm install -g clawhub-cli -q 2>&1 | tail -2
    command -v claw && echo "claw installed" || echo "claw install failed"
    ;;
  opencode)
    npm install -g opencode-ai -q 2>&1 | tail -2
    command -v opencode && opencode --version || echo "opencode install failed"
    ;;
  chromium)
    sudo apt-get install -y chromium-browser -qq 2>/dev/null || \
      sudo snap install chromium 2>/dev/null || \
      echo "chromium install failed — install manually"
    ;;
  jq)
    sudo apt-get install -y jq -qq
    ;;
  *)
    echo "Unknown dependency: $DEP"
    echo "Available: gh, claw, opencode, chromium, jq"
    exit 1
    ;;
esac
