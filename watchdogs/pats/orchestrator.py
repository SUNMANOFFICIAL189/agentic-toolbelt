#!/usr/bin/env python3
"""
PATS-Copy Architectural Watchdog Tier 1 — Orchestrator.

Runs all static and runtime rules, collects Findings, logs to audit.log,
and (in --active mode) sends plain-English Telegram alerts.

Modes:
  --soak        log findings to audit.log only; never send alerts. (Default — first 14 days.)
  --active      send alerts for warn|critical findings, rate-limited per rule_id.
  --once-stdout run once, dump JSON findings to stdout, no audit.log, no alerts. (Dev.)

Severity gate (active mode):
  critical → always alert (every run, no rate limit)
  warn     → alert at most once per rule_id per ALERT_COOLDOWN_SECONDS
  info     → log only

Rules covered (Tier 1, calibrated against 2026-05-07 PATS-Copy bug class):
  Static (semgrep):
    1. enddate-flow.yml          — Trade missing endDate
    2. side-aware-pnl.yml        — side-blind loss formula
    3. single-trade-pool.yml     — copyExecutor receiving signal-bot trades
  Runtime (Python):
    4. supabase_consistency.py
    5. cron_file_existence.py
    6. low_priced_sell_max_loss.py            (new — Phase A)
    7. supabase_pnl_write_reliability.py      (new — Phase A)

Reference:
  ~/claude-hq/watchdogs/pats/README.md
  ~/claude-hq/commander/LESSONS.md  (Rules 16, 19, 20)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Local lib (orchestrator.py sits at the package root, so lib.* works directly)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lib.alerts import send_finding, static_finding_from_semgrep
from lib.finding import Finding

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PATS_REPO = Path.home() / "Desktop" / "POLYMARKET_TRADING_3.0"
PATS_SRC = PATS_REPO / "src"

STATIC_RULES_DIR = HERE / "rules" / "static"
RUNTIME_RULES_DIR = HERE / "rules" / "runtime"

AUDIT_LOG = HERE / "audit.log"
STATE_FILE = HERE / "state.json"

ALERT_COOLDOWN_SECONDS = 3600  # 1 hour rate limit for warn-severity alerts


# ---------------------------------------------------------------------------
# Static rules (semgrep)
# ---------------------------------------------------------------------------

def run_static_rules() -> list[Finding]:
    findings: list[Finding] = []
    if not PATS_SRC.exists():
        return findings

    rule_files = sorted(STATIC_RULES_DIR.glob("*.yml"))
    if not rule_files:
        return findings

    # One semgrep call covering all rules — JSON output we can parse
    cmd = ["semgrep", "scan", "--json", "--no-git-ignore", "--quiet"]
    for rf in rule_files:
        cmd.extend(["--config", str(rf)])
    cmd.append(str(PATS_SRC))

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        # Transient — log and continue
        print(f"# semgrep run failed: {e}", file=sys.stderr)
        return findings

    if not proc.stdout.strip():
        return findings

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        print(f"# semgrep JSON parse failed: {e}", file=sys.stderr)
        return findings

    # Group results by check_id, keep first occurrence as the representative
    by_check: dict[str, list[dict]] = {}
    for r in data.get("results", []):
        cid = r.get("check_id", "unknown")
        by_check.setdefault(cid, []).append(r)

    for check_id, results in by_check.items():
        first = results[0]
        path = first.get("path", "?")
        # Show path relative to the repo for readability
        try:
            path = str(Path(path).resolve().relative_to(PATS_REPO))
        except ValueError:
            pass
        line = (first.get("start") or {}).get("line", 0)
        finding = static_finding_from_semgrep(
            check_id=check_id,
            path=path,
            line=line,
            count=len(results),
        )
        findings.append(finding)

    return findings


# ---------------------------------------------------------------------------
# Runtime rules (Python subprocesses, JSON-line stdout)
# ---------------------------------------------------------------------------

def run_runtime_rules() -> list[Finding]:
    findings: list[Finding] = []
    rule_scripts = sorted(RUNTIME_RULES_DIR.glob("*.py"))

    for script in rule_scripts:
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True, timeout=60, check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"# runtime rule {script.name} failed to launch: {e}", file=sys.stderr)
            continue

        if proc.returncode != 0:
            print(f"# runtime rule {script.name} exited {proc.returncode}: {proc.stderr.strip()[:200]}", file=sys.stderr)
            # Don't break the run — other rules still run. Caller can audit.
            continue

        for raw in proc.stdout.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print(f"# runtime rule {script.name} produced non-JSON line: {line[:120]}", file=sys.stderr)
                continue
            try:
                findings.append(Finding(
                    rule_id=obj["rule_id"],
                    severity=obj["severity"],
                    what_happened=obj["what_happened"],
                    what_to_do=obj["what_to_do"],
                    technical_detail=obj.get("technical_detail", {}) or {},
                ))
            except (KeyError, ValueError) as e:
                print(f"# runtime rule {script.name} produced malformed Finding: {e}", file=sys.stderr)
                continue

    return findings


# ---------------------------------------------------------------------------
# Audit log + alert state
# ---------------------------------------------------------------------------

def append_audit(findings: list[Finding], mode: str) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for finding in findings:
            entry = {
                "ts": ts,
                "mode": mode,
                "rule_id": finding.rule_id,
                "severity": finding.severity,
                "what_happened": finding.what_happened,
                "what_to_do": finding.what_to_do,
                "technical_detail": finding.technical_detail,
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"last_alerted": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"last_alerted": {}}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def should_alert(finding: Finding, state: dict, now: datetime) -> bool:
    """Severity gate + per-rule rate limit for warn alerts."""
    if finding.severity == "info":
        return False
    if finding.severity == "critical":
        return True
    # warn → check cooldown
    last = state.get("last_alerted", {}).get(finding.rule_id)
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (now - last_dt) >= timedelta(seconds=ALERT_COOLDOWN_SECONDS)


def mark_alerted(finding: Finding, state: dict, now: datetime) -> None:
    state.setdefault("last_alerted", {})[finding.rule_id] = (
        now.strftime("%Y-%m-%dT%H:%M:%SZ")
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PATS-Copy architectural watchdog Tier 1")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--soak", action="store_true",
                     help="observe-only: log to audit.log, no Telegram alerts (DEFAULT)")
    grp.add_argument("--active", action="store_true",
                     help="active alerting: send Telegram for warn|critical")
    grp.add_argument("--once-stdout", action="store_true",
                     help="run all rules once, dump findings as JSON lines to stdout, no log/alert")
    args = parser.parse_args(argv)

    mode = "soak"
    if args.active:
        mode = "active"
    elif args.once_stdout:
        mode = "once-stdout"

    findings: list[Finding] = []
    findings.extend(run_static_rules())
    findings.extend(run_runtime_rules())

    if mode == "once-stdout":
        for f in findings:
            print(f.to_json_line())
        return 0

    # Soak + active both write audit log
    if findings:
        append_audit(findings, mode)

    if mode == "soak":
        # Stdout one-line summary for launchd captures
        n_critical = sum(1 for f in findings if f.severity == "critical")
        n_warn = sum(1 for f in findings if f.severity == "warn")
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"{ts} soak: {len(findings)} finding(s) — {n_critical} critical, {n_warn} warn", flush=True)
        return 0

    # Active mode — apply gate, send Telegram, update state
    state = load_state()
    now = datetime.now(timezone.utc)
    sent = 0
    suppressed = 0
    for finding in findings:
        if not should_alert(finding, state, now):
            suppressed += 1
            continue
        try:
            send_finding(finding)
            mark_alerted(finding, state, now)
            sent += 1
        except Exception as e:  # noqa: BLE001 — never let one bad alert kill the run
            print(f"# alert send failed for {finding.rule_id}: {e}", file=sys.stderr)
    save_state(state)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"{ts} active: {len(findings)} finding(s) → sent {sent}, suppressed {suppressed}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as e:
        print(f"# transient: network error during run: {e}", file=sys.stderr)
        sys.exit(0)
