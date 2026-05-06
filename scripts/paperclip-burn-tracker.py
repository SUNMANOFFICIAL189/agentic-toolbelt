#!/usr/bin/env python3
"""
Paperclip Token Burn Tracker
============================

Reads Paperclip's cost API, displays per-agent + total token usage, saves
timestamped snapshots, and computes delta vs the previous snapshot.

Why this exists:
- The 2026-04-28 quota incident burned 66M cached tokens in ~30min.
- Workstream 1 + 2a + 2b applied architectural fixes (lean prompts, event-driven,
  cooldown 120s, Planner on gemini-2.5-flash).
- We need quantitative measurement to prove the fixes work — not assumption.

Usage:
  paperclip-burn-tracker.py                # snapshot + report (default)
  paperclip-burn-tracker.py --baseline     # save current as the baseline reference
  paperclip-burn-tracker.py --json         # machine-readable output

Snapshots saved to: ~/.paperclip/burn-snapshots/<ISO-timestamp>.json
Baseline saved as:  ~/.paperclip/burn-snapshots/baseline.json

Read-only — never mutates Paperclip state.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PAPERCLIP_URL = os.environ.get("PAPERCLIP_URL", "http://localhost:3100")
COMPANY_ID = os.environ.get(
    "PAPERCLIP_COMPANY_ID",
    "58684871-fb90-4f3a-bf30-bbf80f2677e1",  # Agent Alpha — UGC Ads
)
SNAPSHOT_DIR = Path.home() / ".paperclip" / "burn-snapshots"


def fetch(path: str) -> Any:
    url = f"{PAPERCLIP_URL}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"FATAL: GET {url} failed: {e}", file=sys.stderr)
        sys.exit(2)


@dataclass
class AgentBurn:
    agent_id: str
    name: str
    status: str
    model: str | None
    runs: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    cost_cents: int


def aggregate_metered_runs(limit: int = 500) -> dict[str, Any]:
    """Aggregate non-Anthropic billed runs from heartbeat-runs.

    Paperclip's /costs/* endpoints currently only ingest Anthropic-billed runs
    into aggregations. Gemini, OpenRouter, etc. flow through with usage in
    each run's resultJson.stats but don't roll up. This function fills the gap.

    Two-pass approach: the heartbeat-runs LISTING endpoint strips resultJson
    (performance), so we identify non-Anthropic run IDs from the listing then
    fetch each individually for the full stats.

    Token semantics (Gemini CLI conventions, used as canonical):
      input_tokens  = total prompt tokens including cached
      cached        = cached portion of input
      output_tokens = generated tokens

    Returns aggregations keyed by (agent_id, biller, model) and per-agent totals.
    """
    runs = fetch(f"/api/companies/{COMPANY_ID}/heartbeat-runs?limit={limit}")
    runs = runs.get("runs", runs) if isinstance(runs, dict) else runs

    # Pass 1: identify non-Anthropic succeeded runs from the listing
    metered_run_ids: list[str] = []
    for r in runs:
        if r.get("status") != "succeeded":
            continue
        usage = r.get("usageJson") or {}
        biller = usage.get("biller")
        if not biller or biller == "anthropic":
            continue
        metered_run_ids.append(r["id"])

    # Pass 2: fetch each individually for full resultJson.stats
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    per_agent: dict[str, dict[str, Any]] = {}

    for run_id in metered_run_ids:
        try:
            r = fetch(f"/api/heartbeat-runs/{run_id}")
        except SystemExit:
            continue
        usage = r.get("usageJson") or {}
        biller = usage.get("biller") or "?"
        model = usage.get("model") or "?"
        result = r.get("resultJson") or {}
        stats = result.get("stats") or {}
        agent_id = r.get("agentId") or "?"

        in_total = int(stats.get("input_tokens") or 0)
        cached = int(stats.get("cached") or 0)
        out = int(stats.get("output_tokens") or 0)

        key = (agent_id, biller, model)
        bucket = by_key.setdefault(key, {
            "agent_id": agent_id,
            "biller": biller,
            "model": model,
            "billing_type": usage.get("billingType"),
            "runs": 0,
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
        })
        bucket["runs"] += 1
        bucket["input_tokens"] += in_total
        bucket["cached_input_tokens"] += cached
        bucket["output_tokens"] += out

        agg = per_agent.setdefault(agent_id, {
            "runs": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0,
        })
        agg["runs"] += 1
        agg["input_tokens"] += in_total
        agg["cached_input_tokens"] += cached
        agg["output_tokens"] += out

    return {
        "by_key": list(by_key.values()),
        "per_agent": per_agent,
        "metered_run_count": len(metered_run_ids),
    }


def snapshot() -> dict[str, Any]:
    """Build a complete burn snapshot at the current moment."""
    by_agent = fetch(f"/api/companies/{COMPANY_ID}/costs/by-agent")
    by_agent_model = fetch(f"/api/companies/{COMPANY_ID}/costs/by-agent-model")
    summary = fetch(f"/api/companies/{COMPANY_ID}/costs/summary")
    window_spend = fetch(f"/api/companies/{COMPANY_ID}/costs/window-spend")
    metered = aggregate_metered_runs()

    # Build one row per agent — pick the FIRST model entry per agent for display
    # (most agents have one model; if multiple, we annotate)
    agent_models: dict[str, list[dict[str, Any]]] = {}
    for r in by_agent_model:
        agent_models.setdefault(r["agentId"], []).append(r)

    agents: list[AgentBurn] = []
    for r in by_agent:
        agent_id = r["agentId"]
        models = agent_models.get(agent_id, [])
        primary_model = models[0]["model"] if models else None
        if len(models) > 1:
            primary_model = f"{primary_model}+{len(models) - 1}more"
        # Add metered (non-anthropic) tokens onto the agent's totals
        m_agg = metered["per_agent"].get(agent_id, {})
        agents.append(
            AgentBurn(
                agent_id=agent_id,
                name=r["agentName"],
                status=r["agentStatus"],
                model=primary_model,
                runs=r.get("apiRunCount", 0) + r.get("subscriptionRunCount", 0) + m_agg.get("runs", 0),
                input_tokens=r.get("inputTokens", 0) + m_agg.get("input_tokens", 0),
                cached_input_tokens=r.get("cachedInputTokens", 0) + m_agg.get("cached_input_tokens", 0),
                output_tokens=r.get("outputTokens", 0) + m_agg.get("output_tokens", 0),
                cost_cents=r.get("costCents", 0),
            )
        )

    totals = {
        "runs": sum(a.runs for a in agents),
        "input_tokens": sum(a.input_tokens for a in agents),
        "cached_input_tokens": sum(a.cached_input_tokens for a in agents),
        "output_tokens": sum(a.output_tokens for a in agents),
        "cost_cents": sum(a.cost_cents for a in agents),
    }

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "company_id": COMPANY_ID,
        "agents": [asdict(a) for a in agents],
        "totals": totals,
        "summary": summary,
        "window_spend": window_spend,
        "metered_by_key": metered["by_key"],
    }


def fmt_int(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def fmt_cents(cents: int) -> str:
    return f"${cents/100:.2f}"


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def report(current: dict[str, Any], previous: dict[str, Any] | None = None) -> str:
    lines: list[str] = []
    captured = parse_iso(current["captured_at"])
    lines.append("=" * 76)
    lines.append("Paperclip Token Burn Report")
    lines.append("=" * 76)
    lines.append(f"Captured:  {captured.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append(f"Company:   {current['company_id']}")
    lines.append("")

    # Per-agent table
    lines.append(f"{'Agent':<12} {'Status':<10} {'Model':<24} {'Runs':>6} {'In':>8} {'CachedIn':>10} {'Out':>8} {'Cost':>8}")
    lines.append("-" * 76)
    for a in current["agents"]:
        lines.append(
            f"{a['name']:<12} {a['status']:<10} {(a['model'] or '-')[:24]:<24} "
            f"{a['runs']:>6} {fmt_int(a['input_tokens']):>8} "
            f"{fmt_int(a['cached_input_tokens']):>10} {fmt_int(a['output_tokens']):>8} "
            f"{fmt_cents(a['cost_cents']):>8}"
        )
    t = current["totals"]
    lines.append("-" * 76)
    lines.append(
        f"{'TOTAL':<12} {'':<10} {'':<24} {t['runs']:>6} {fmt_int(t['input_tokens']):>8} "
        f"{fmt_int(t['cached_input_tokens']):>10} {fmt_int(t['output_tokens']):>8} "
        f"{fmt_cents(t['cost_cents']):>8}"
    )
    lines.append("")

    # Budget
    s = current["summary"]
    util = s.get("utilizationPercent", 0)
    lines.append(f"Budget: {fmt_cents(s['spendCents'])} / {fmt_cents(s['budgetCents'])} ({util:.1f}%)")
    lines.append("")

    # Window spend (Anthropic only — Paperclip's window-spend endpoint doesn't aggregate metered)
    lines.append("Rolling-window spend (Anthropic only — Paperclip cost service limitation):")
    for w in current["window_spend"]:
        lines.append(
            f"  {w.get('window', '?'):<6} provider={w.get('provider', '-'):<10} "
            f"in={fmt_int(w.get('inputTokens', 0))} cachedIn={fmt_int(w.get('cachedInputTokens', 0))} "
            f"out={fmt_int(w.get('outputTokens', 0))} cost={fmt_cents(w.get('costCents', 0))}"
        )
    lines.append("")

    # Metered API runs (non-Anthropic — gemini, openrouter, etc.)
    metered = current.get("metered_by_key", [])
    if metered:
        lines.append("Metered-API runs (gemini, openrouter, etc. — from heartbeat-runs resultJson.stats):")
        # Look up agent name by agent_id from the agents list
        agent_name_by_id = {a["agent_id"]: a["name"] for a in current["agents"]}
        for m in sorted(metered, key=lambda x: (x["biller"], x["agent_id"])):
            name = agent_name_by_id.get(m["agent_id"], m["agent_id"][:8])
            lines.append(
                f"  {name:<12} biller={m['biller']:<10} model={(m['model'] or '-')[:24]:<24} "
                f"runs={m['runs']:>3} in={fmt_int(m['input_tokens'])} "
                f"cachedIn={fmt_int(m['cached_input_tokens'])} out={fmt_int(m['output_tokens'])}"
            )
        lines.append("")
    else:
        lines.append("Metered-API runs: none yet (all activity on Anthropic subscription)")
        lines.append("")

    # Delta vs previous
    if previous is None:
        lines.append("Δ: no previous snapshot for comparison (run again later to see deltas)")
    else:
        prev_at = parse_iso(previous["captured_at"])
        elapsed_min = (captured - prev_at).total_seconds() / 60
        prev_t = previous["totals"]
        d_runs = t["runs"] - prev_t["runs"]
        d_in = t["input_tokens"] - prev_t["input_tokens"]
        d_cin = t["cached_input_tokens"] - prev_t["cached_input_tokens"]
        d_out = t["output_tokens"] - prev_t["output_tokens"]
        d_cost = t["cost_cents"] - prev_t["cost_cents"]

        lines.append(f"Δ since {prev_at.astimezone().strftime('%Y-%m-%d %H:%M:%S')} ({elapsed_min:.1f} min ago):")
        lines.append(
            f"  +{d_runs} runs, +{fmt_int(d_in)} in, +{fmt_int(d_cin)} cachedIn, "
            f"+{fmt_int(d_out)} out, +{fmt_cents(d_cost)}"
        )
        if elapsed_min > 0:
            rate_tok_min = (d_in + d_cin + d_out) / elapsed_min
            lines.append(f"  rate: {fmt_int(int(rate_tok_min))} tok/min")
            # Compare to incident burn
            INCIDENT_RATE = 66_000_000 / 30  # 66M tokens in ~30 min
            ratio = rate_tok_min / INCIDENT_RATE if INCIDENT_RATE else 0
            lines.append(f"  vs 2026-04-28 incident rate ({fmt_int(int(INCIDENT_RATE))} tok/min): {ratio*100:.1f}%")

    lines.append("")
    lines.append("=" * 76)
    return "\n".join(lines)


def save_snapshot(data: dict[str, Any], as_baseline: bool = False) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = data["captured_at"].replace(":", "-").replace(".", "-")
    path = SNAPSHOT_DIR / f"{ts}.json"
    path.write_text(json.dumps(data, indent=2))
    if as_baseline:
        (SNAPSHOT_DIR / "baseline.json").write_text(json.dumps(data, indent=2))
    return path


def load_previous() -> dict[str, Any] | None:
    """Load the most recent snapshot before now (excluding baseline.json)."""
    if not SNAPSHOT_DIR.exists():
        return None
    candidates = sorted(
        [p for p in SNAPSHOT_DIR.glob("*.json") if p.name != "baseline.json"],
        reverse=True,
    )
    if not candidates:
        return None
    try:
        return json.loads(candidates[0].read_text())
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true", help="save this snapshot as the baseline reference")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of human-readable report")
    args = ap.parse_args()

    previous = load_previous()
    current = snapshot()
    save_snapshot(current, as_baseline=args.baseline)

    if args.json:
        print(json.dumps({"current": current, "previous_for_delta": previous}, indent=2))
    else:
        print(report(current, previous))

    return 0


if __name__ == "__main__":
    sys.exit(main())
