#!/usr/bin/env python3
"""FORGE — API key validator. Usage: validate_key.py [service] [key]"""
import sys, urllib.request, json

SERVICE = sys.argv[1] if len(sys.argv) > 1 else "gemini"
KEY     = sys.argv[2] if len(sys.argv) > 2 else ""

if not KEY:
    print("error: no key"); sys.exit(1)

if SERVICE == "gemini":
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={KEY}"
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read())
            print("valid" if "models" in d else "invalid")
    except urllib.error.HTTPError as e:
        print(f"error: HTTP {e.code}"); sys.exit(1)
    except Exception as e:
        print(f"error: {e}"); sys.exit(1)

elif SERVICE == "github":
    try:
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={"Authorization": f"token {KEY}",
                     "User-Agent": "FORGE/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            print(f"valid:{d.get('login','?')}")
    except Exception as e:
        print(f"error: {e}"); sys.exit(1)

elif SERVICE == "telegram":
    try:
        url = f"https://api.telegram.org/bot{KEY}/getMe"
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read())
            if d.get("ok"):
                print(f"valid:{d['result'].get('username','?')}")
            else:
                print("invalid")
    except Exception as e:
        print(f"error: {e}"); sys.exit(1)
else:
    print(f"unknown service: {SERVICE}"); sys.exit(1)
