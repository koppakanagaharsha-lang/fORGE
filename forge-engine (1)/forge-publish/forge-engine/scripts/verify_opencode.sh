#!/usr/bin/env bash
command -v opencode &>/dev/null && opencode --version &>/dev/null && echo "found" || echo "not_found"
