#!/usr/bin/env python3
"""
Runtime rule: server cron entries reference existing files.

The 2026-05-07 session-start audit found a `*/5 * * * * /opt/polymarket-bot/health-check.sh`
cron entry pointing at a deleted file — silently failing every 5 minutes
since the file was removed. This rule SSHes the server, lists the crontab,
and verifies each referenced executable exists.

Calibrated against the broken-cron pattern. Catches:
  - Direct script paths (`/opt/.../foo.sh`) that no longer exist
  - Shebang-style invocations where the binary path is missing

Does NOT catch:
  - Indirect invocations (`bash -c 'cd X && foo'`) — too many false positives
  - Cron entries that work via $PATH lookup

Usage:
    python rules/runtime/cron_file_existence.py
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.finding import Finding, emit

RULE_ID = "pats-runtime-cron-file-existence"
SSH_HOST = "root@204.168.204.247"
CRON_LINE = re.compile(r"^\s*[\d\*\-\,\/]+\s+[\d\*\-\,\/]+\s+[\d\*\-\,\/]+\s+[\d\*\-\,\/]+\s+[\d\*\-\,\/]+\s+(.+)$")


def main() -> int:
    out = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", SSH_HOST, "crontab -l 2>/dev/null || true"],
        capture_output=True, text=True, timeout=20, check=False,
    )
    if out.returncode != 0:
        # SSH failure is transient — the listener watchdog will catch persistent SSH outage
        return 0

    crontab = out.stdout
    broken: list[dict[str, str]] = []
    for raw in crontab.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = CRON_LINE.match(line)
        if not m:
            continue
        command = m.group(1).strip()
        target = _extract_target(command)
        if target is None:
            continue
        if not _exists_on_server(target):
            broken.append({"line": line, "missing_path": target})

    if not broken:
        return 0

    sample = broken[0]
    count = len(broken)
    finding = Finding(
        rule_id=RULE_ID,
        severity="warn",
        what_happened=(
            f"The server has {count} cron entry/entries pointing at file(s) that no longer exist. "
            f"The first missing file is \"{sample['missing_path']}\". "
            f"Cron has been silently failing each time it tries to run."
        ),
        what_to_do=(
            f"Open `crontab -e` on the server (ssh {SSH_HOST}), find the line "
            f"pointing at the missing file, and either fix the path or delete the entry."
        ),
        technical_detail={
            "rule_id": RULE_ID,
            "ssh_host": SSH_HOST,
            "broken_count": count,
            "broken_entries": broken,
        },
    )
    emit(finding)
    return 0


def _extract_target(command: str) -> str | None:
    """Return the script-or-binary path the cron line invokes, if extractable.

    Skips bash -c '...' style chains (too many false positives), shell built-ins,
    and PATH-relative names (which can't be checked without the server's PATH).
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if not tokens:
        return None
    first = tokens[0]
    # Strip env assignments like FOO=bar
    while "=" in first and not first.startswith("/"):
        if len(tokens) < 2:
            return None
        tokens = tokens[1:]
        first = tokens[0]
    # Only flag absolute paths — relative lookups are PATH-dependent
    if not first.startswith("/"):
        return None
    # Skip well-known shells where the actual target is in -c args
    if first in ("/bin/sh", "/bin/bash", "/usr/bin/sh", "/usr/bin/bash"):
        return None
    return first


def _exists_on_server(path: str) -> bool:
    out = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", SSH_HOST, f"test -e {shlex.quote(path)}"],
        capture_output=True, text=True, timeout=15, check=False,
    )
    return out.returncode == 0


if __name__ == "__main__":
    sys.exit(main())
