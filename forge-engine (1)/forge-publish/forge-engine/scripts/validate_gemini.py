#!/usr/bin/env python3
import sys, urllib.request, json
key = sys.argv[1] if len(sys.argv) > 1 else ""
if not key: print("error: no key"); sys.exit(1)
try:
    with urllib.request.urlopen(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        timeout=10) as r:
        print("valid" if "models" in json.loads(r.read()) else "invalid")
except urllib.error.HTTPError as e: print(f"error: {e.code}"); sys.exit(1)
except Exception as e: print(f"error: {e}"); sys.exit(1)
