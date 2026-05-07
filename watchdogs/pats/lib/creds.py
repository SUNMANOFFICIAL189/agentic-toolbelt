"""
Lightweight .env loader for PATS-Copy watchdog runtime rules.

We don't bring in python-dotenv to keep the watchdog's dependency surface
zero. The .env files we read are simple KEY=VALUE pairs (no shell expansion,
no quoting tricks), which is exactly what PATS-Copy and HQ Watchdog write.
"""

from __future__ import annotations

import os
from pathlib import Path

# Canonical .env locations
PATS_COPY_ENV = Path.home() / "Desktop" / "POLYMARKET_TRADING_3.0" / ".env"
HQ_WATCHDOG_ENV = Path.home() / "claude-hq" / "watchdog" / ".env"


def load_env(path: Path) -> dict[str, str]:
    """Read KEY=VALUE pairs from a .env file. Returns dict (unmodified env)."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        env[key] = value
    return env


def supabase_creds() -> tuple[str, str]:
    """Return (SUPABASE_URL, SUPABASE_SERVICE_KEY) from PATS-Copy .env or env."""
    env = load_env(PATS_COPY_ENV)
    url = env.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
    key = env.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            f"Supabase credentials not found in {PATS_COPY_ENV} or environment."
        )
    return url, key


__all__ = ["load_env", "supabase_creds", "PATS_COPY_ENV", "HQ_WATCHDOG_ENV"]
