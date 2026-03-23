#!/usr/bin/env bash
source "$HOME/.forge/.env" 2>/dev/null || true
REPO="${1:-}"
[ -z "$REPO" ] && exit 1
WORKSPACE="$HOME/.forge/workspace/$REPO"
[ -d "$WORKSPACE" ] || exit 0
cd "$WORKSPACE"
git pull 2>/dev/null || true
npm audit 2>/dev/null | tail -3 || true
pip-audit 2>/dev/null | tail -3 || true
npm test 2>/dev/null | tail -5 || pytest 2>/dev/null | tail -5 || true
echo "Stability check complete: $REPO"
