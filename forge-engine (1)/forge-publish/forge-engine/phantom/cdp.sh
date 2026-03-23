#!/usr/bin/env bash
# phantom/cdp.sh — wrapper
exec python3 "$(dirname "$0")/cdp.py" "$@"
