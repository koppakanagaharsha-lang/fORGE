#!/usr/bin/env python3
"""
FORGE Keyring — Multi-key rotation with automatic failover.
Mirrors the key rotation model OpenClaw uses natively.

Supports multiple Gemini keys, GitHub tokens, ClawHub tokens.
When a key hits rate limit or quota: rotate to next, continue silently.
Tracks per-key health, cooldown, and usage stats.
Persists state across sessions in ~/.forge/keyring.json
"""

import json, time, os, sys, threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

FORGE_DIR  = Path.home() / ".forge"
KEYRING_FILE = FORGE_DIR / "keyring.json"
ENV_FILE     = FORGE_DIR / ".env"

# How long to cool a key down after rate limit (seconds)
COOLDOWN_SECONDS = {
    "gemini":  65,   # Gemini free tier: 1 min + buffer
    "github":  60,
    "clawhub": 60,
    "telegram": 10,
}

# Max requests per minute per key (soft limit — rotate before hard limit)
SOFT_RPM = {
    "gemini":  14,   # Gemini free: 15 RPM → rotate at 14
    "github":  55,   # GitHub: 60 RPM → rotate at 55
    "clawhub": 50,
    "telegram": 25,
}


class KeyState:
    """State for a single API key."""
    def __init__(self, service: str, key: str, label: str = ""):
        self.service  = service
        self.key      = key
        self.label    = label or key[:8] + "..."
        self.active   = True
        self.requests_this_minute = 0
        self.minute_start = time.time()
        self.cooldown_until: float = 0
        self.total_requests = 0
        self.total_errors   = 0
        self.last_used: float = 0
        self.last_error: str  = ""

    def is_available(self) -> bool:
        now = time.time()
        if not self.active:
            return False
        if now < self.cooldown_until:
            return False
        # Reset per-minute counter if minute has elapsed
        if now - self.minute_start >= 60:
            self.requests_this_minute = 0
            self.minute_start = now
        soft = SOFT_RPM.get(self.service, 50)
        return self.requests_this_minute < soft

    def cooldown_remaining(self) -> float:
        return max(0, self.cooldown_until - time.time())

    def record_use(self):
        self.requests_this_minute += 1
        self.total_requests += 1
        self.last_used = time.time()

    def record_error(self, error: str):
        self.total_errors += 1
        self.last_error = error

    def apply_cooldown(self, seconds: Optional[float] = None):
        cd = seconds or COOLDOWN_SECONDS.get(self.service, 60)
        self.cooldown_until = time.time() + cd

    def to_dict(self) -> dict:
        return {
            "service":  self.service,
            "label":    self.label,
            "active":   self.active,
            "total_requests":  self.total_requests,
            "total_errors":    self.total_errors,
            "cooldown_until":  self.cooldown_until,
            "last_used":       self.last_used,
            "last_error":      self.last_error,
        }


class Keyring:
    """
    Multi-key rotator for all FORGE API services.
    Thread-safe. Persists stats to keyring.json.
    """

    def __init__(self):
        self._lock  = threading.Lock()
        self._keys: dict[str, list[KeyState]] = {}
        self._index: dict[str, int] = {}
        self._load_env()
        self._load_stats()

    def _load_env(self):
        """Load all keys from ~/.forge/.env"""
        if not ENV_FILE.exists():
            return

        env_text = ENV_FILE.read_text()
        for line in env_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if not v:
                continue
            self._register_from_env(k, v)

    def _register_from_env(self, key_name: str, value: str):
        """Parse env var name to determine service and register key."""
        kl = key_name.lower()

        # Support multiple keys: GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...
        # or GEMINI_API_KEY (single), GEMINI_KEYS=key1,key2,key3 (csv)

        if "gemini" in kl:
            if key_name.endswith("_KEYS") or key_name.endswith("_KEYS"):
                # CSV list
                for i, k in enumerate(value.split(",")):
                    k = k.strip()
                    if k:
                        self._add_key("gemini", k, f"gemini-{i+1}")
            else:
                label = key_name.replace("GEMINI_API_KEY", "").strip("_") or "1"
                self._add_key("gemini", value, f"gemini-{label}")

        elif "github" in kl and "token" in kl:
            label = key_name.replace("GITHUB_TOKEN", "").strip("_") or "1"
            self._add_key("github", value, f"github-{label}")

        elif "clawhub" in kl and "token" in kl:
            label = key_name.replace("CLAWHUB_TOKEN", "").strip("_") or "1"
            self._add_key("clawhub", value, f"clawhub-{label}")

        elif "telegram" in kl and "token" in kl:
            label = key_name.replace("TELEGRAM_BOT_TOKEN", "").strip("_") or "1"
            self._add_key("telegram", value, f"telegram-{label}")

    def _add_key(self, service: str, key: str, label: str):
        """Add a key if not already registered."""
        with self._lock:
            if service not in self._keys:
                self._keys[service] = []
                self._index[service] = 0
            # Deduplicate
            existing = [ks.key for ks in self._keys[service]]
            if key not in existing:
                self._keys[service].append(KeyState(service, key, label))

    def _load_stats(self):
        """Load persisted stats (not keys) from keyring.json"""
        if not KEYRING_FILE.exists():
            return
        try:
            data = json.loads(KEYRING_FILE.read_text())
            for service, stats_list in data.items():
                if service not in self._keys:
                    continue
                for ks in self._keys[service]:
                    for stat in stats_list:
                        if stat.get("label") == ks.label:
                            ks.active         = stat.get("active", True)
                            ks.total_requests = stat.get("total_requests", 0)
                            ks.total_errors   = stat.get("total_errors", 0)
                            ks.cooldown_until = stat.get("cooldown_until", 0)
                            ks.last_used      = stat.get("last_used", 0)
                            ks.last_error     = stat.get("last_error", "")
        except Exception:
            pass

    def save_stats(self):
        """Persist key stats (not keys themselves) to keyring.json"""
        try:
            data = {
                service: [ks.to_dict() for ks in keys]
                for service, keys in self._keys.items()
            }
            KEYRING_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def add_key(self, service: str, key: str, label: str = ""):
        """Add a new key at runtime and persist it to .env"""
        self._add_key(service, key, label or f"{service}-{len(self._keys.get(service,[]))+1}")
        # Append to .env
        env_var = {
            "gemini":   f"GEMINI_API_KEY_{len(self._keys.get('gemini',[]))}",
            "github":   f"GITHUB_TOKEN_{len(self._keys.get('github',[]))}",
            "clawhub":  f"CLAWHUB_TOKEN_{len(self._keys.get('clawhub',[]))}",
            "telegram": f"TELEGRAM_BOT_TOKEN_{len(self._keys.get('telegram',[]))}",
        }.get(service, f"{service.upper()}_KEY_{len(self._keys.get(service,[]))}")

        with open(ENV_FILE, "a") as f:
            f.write(f'\n{env_var}="{key}"\n')

    def get_key(self, service: str) -> Optional[str]:
        """
        Get the next available key for a service.
        Rotates automatically. Returns None if all keys exhausted.
        """
        with self._lock:
            keys = self._keys.get(service, [])
            if not keys:
                return None

            start = self._index.get(service, 0)
            n = len(keys)

            for i in range(n):
                idx = (start + i) % n
                ks  = keys[idx]
                if ks.is_available():
                    self._index[service] = idx
                    ks.record_use()
                    return ks.key

            return None  # All keys on cooldown

    def report_rate_limit(self, service: str, key: str,
                          cooldown: Optional[float] = None):
        """Mark a key as rate-limited and rotate to next."""
        with self._lock:
            for ks in self._keys.get(service, []):
                if ks.key == key:
                    ks.apply_cooldown(cooldown)
                    ks.record_error("rate_limit")
                    # Advance index past this key
                    keys = self._keys[service]
                    idx  = keys.index(ks)
                    self._index[service] = (idx + 1) % len(keys)
                    break
        self.save_stats()

    def report_error(self, service: str, key: str, error: str):
        """Record an error on a key without cooling it down."""
        with self._lock:
            for ks in self._keys.get(service, []):
                if ks.key == key:
                    ks.record_error(error)
                    break
        self.save_stats()

    def disable_key(self, service: str, key: str):
        """Permanently disable a key (e.g. invalid/revoked)."""
        with self._lock:
            for ks in self._keys.get(service, []):
                if ks.key == key:
                    ks.active = False
                    break
        self.save_stats()

    def cooldown_remaining(self, service: str) -> float:
        """Minimum time until any key for service becomes available."""
        with self._lock:
            keys = self._keys.get(service, [])
            if not keys:
                return 0
            available = [ks for ks in keys if ks.active]
            if not available:
                return 0
            return min(ks.cooldown_remaining() for ks in available)

    def key_count(self, service: str) -> dict:
        """Return counts of total/available/cooling keys."""
        with self._lock:
            keys = self._keys.get(service, [])
            total     = len(keys)
            available = sum(1 for ks in keys if ks.is_available())
            cooling   = sum(1 for ks in keys
                            if ks.active and ks.cooldown_remaining() > 0)
            disabled  = sum(1 for ks in keys if not ks.active)
            return {
                "total": total, "available": available,
                "cooling": cooling, "disabled": disabled,
            }

    def status_report(self) -> str:
        """Human-readable status of all keys."""
        lines = ["⚡ FORGE Keyring Status", ""]
        for service in sorted(self._keys.keys()):
            counts = self.key_count(service)
            lines.append(
                f"  {service:12} {counts['available']}/{counts['total']} available"
                + (f" ({counts['cooling']} cooling)" if counts['cooling'] else "")
                + (f" ({counts['disabled']} disabled)" if counts['disabled'] else "")
            )
            for ks in self._keys[service]:
                cd = ks.cooldown_remaining()
                status = (
                    f"cooling {cd:.0f}s" if cd > 0 else
                    "disabled" if not ks.active else
                    "ready"
                )
                lines.append(
                    f"    {ks.label:20} {status:15} "
                    f"req:{ks.total_requests} err:{ks.total_errors}"
                )
        return "\n".join(lines)


# ── Module-level singleton ────────────────────────────────────────────────────
_keyring: Optional[Keyring] = None

def get_keyring() -> Keyring:
    global _keyring
    if _keyring is None:
        _keyring = Keyring()
    return _keyring

def get_key(service: str) -> Optional[str]:
    return get_keyring().get_key(service)

def report_rate_limit(service: str, key: str, cooldown: float = None):
    get_keyring().report_rate_limit(service, key, cooldown)

def report_error(service: str, key: str, error: str):
    get_keyring().report_error(service, key, error)


# ── CLI interface ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    kr = get_keyring()

    if cmd == "status":
        print(kr.status_report())

    elif cmd == "get":
        service = sys.argv[2] if len(sys.argv) > 2 else "gemini"
        key = kr.get_key(service)
        if key:
            # Print only first 8 chars for security
            print(f"key:{key[:8]}...  service:{service}")
        else:
            print(f"no available key for {service}")
            sys.exit(1)

    elif cmd == "add":
        # add <service> <key> [label]
        if len(sys.argv) < 4:
            print("Usage: keyring.py add <service> <key> [label]")
            sys.exit(1)
        service = sys.argv[2]
        key     = sys.argv[3]
        label   = sys.argv[4] if len(sys.argv) > 4 else ""
        kr.add_key(service, key, label)
        kr.save_stats()
        print(f"Added {service} key: {key[:8]}...")

    elif cmd == "cooldown":
        service = sys.argv[2] if len(sys.argv) > 2 else "gemini"
        remaining = kr.cooldown_remaining(service)
        if remaining > 0:
            print(f"{remaining:.1f}s until a {service} key is available")
        else:
            print(f"{service}: key available now")

    elif cmd == "counts":
        service = sys.argv[2] if len(sys.argv) > 2 else "gemini"
        print(json.dumps(kr.key_count(service)))

    elif cmd == "report":
        # report_ratelimit <service> <key>
        if len(sys.argv) < 4:
            sys.exit(1)
        kr.report_rate_limit(sys.argv[2], sys.argv[3])
        print("Rate limit recorded. Key cooled.")

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: status, get, add, cooldown, counts, report")
        sys.exit(1)
