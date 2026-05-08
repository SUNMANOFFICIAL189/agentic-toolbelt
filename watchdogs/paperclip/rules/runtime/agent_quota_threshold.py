#!/usr/bin/env python3
"""
Runtime rule: per-agent monthly budget approaching cap.

Paperclip already auto-pauses agents at 100% of monthly budget. By then it's
too late — the agent stops mid-work and an approval has to be manually
raised. This rule alerts at the soft threshold (default 80%) so you can
intervene before the auto-pause.

Reads /companies/:id/budgets/overview for each configured company and
compares spent_cents against budget_cents per agent.

Config (env vars):
    PAPERCLIP_COMPANY_IDS         — comma-separated UUIDs (same as burn-rate rule)
    PAPERCLIP_BUDGET_WARN_PCT     — default 80
    PAPERCLIP_BUDGET_CRITICAL_PCT — default 95

Usage:
    python rules/runtime/agent_quota_threshold.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.finding import Finding, emit
from lib.paperclip_api import _get  # noqa: PLC2701

RULE_ID = "paperclip-runtime-budget-threshold"
DEFAULT_COMPANY_ID = "58684871-fb90-4f3a-bf30-bbf80f2677e1"


def _company_ids() -> list[str]:
    raw = os.environ.get("PAPERCLIP_COMPANY_IDS", "").strip()
    if raw:
        return [c.strip() for c in raw.split(",") if c.strip()]
    return [DEFAULT_COMPANY_ID]


def _pct_threshold(env_key: str, default: int) -> int:
    raw = os.environ.get(env_key, "").strip()
    try:
        v = int(raw) if raw else default
    except ValueError:
        v = default
    return max(1, min(100, v))


def _budgets_overview(company_id: str) -> dict | None:
    return _get(f"/companies/{company_id}/budgets/overview")


def _extract_agent_budgets(overview: dict) -> list[dict]:
    """Tolerant extraction — Paperclip field names may evolve."""
    # Try common shapes: agents[], byAgent[], etc.
    for key in ("agents", "byAgent", "agentBudgets"):
        v = overview.get(key)
        if isinstance(v, list):
            return v
    return []


def main() -> int:
    warn_pct = _pct_threshold("PAPERCLIP_BUDGET_WARN_PCT", 80)
    crit_pct = _pct_threshold("PAPERCLIP_BUDGET_CRITICAL_PCT", 95)

    for company_id in _company_ids():
        overview = _budgets_overview(company_id)
        if overview is None:
            continue

        agents = _extract_agent_budgets(overview)
        for agent in agents:
            if not isinstance(agent, dict):
                continue
            spent = agent.get("spentMonthlyCents") or agent.get("spent_cents") or 0
            budget = agent.get("budgetMonthlyCents") or agent.get("budget_cents") or 0
            if not isinstance(spent, int) or not isinstance(budget, int) or budget <= 0:
                continue

            pct = (spent * 100) // budget
            if pct < warn_pct:
                continue

            agent_name = agent.get("name") or agent.get("displayName") or agent.get("id", "?")[:8]
            spent_dollars = spent / 100
            budget_dollars = budget / 100

            severity = "critical" if pct >= crit_pct else "warn"

            if severity == "critical":
                what_happened = (
                    f"Agent '{agent_name}' has burned through {pct} percent of its monthly "
                    f"budget — about ${spent_dollars:.2f} of its ${budget_dollars:.2f} cap. "
                    "Paperclip auto-pauses at 100 percent, so this agent is minutes from being "
                    "frozen mid-work."
                )
                what_to_do = (
                    "Open Paperclip's agent page for this agent. Either approve a budget raise "
                    "now, or pause the agent yourself so it stops in a clean state instead of "
                    "being interrupted by the auto-pause."
                )
            else:
                what_happened = (
                    f"Agent '{agent_name}' has used {pct} percent of its monthly budget — about "
                    f"${spent_dollars:.2f} of its ${budget_dollars:.2f} cap. Not yet pause-level, "
                    "but worth knowing about now rather than at the cap."
                )
                what_to_do = (
                    "If the work this agent's doing is still important, plan a budget raise "
                    "before the cap. Otherwise check whether it's burning on something it "
                    "shouldn't be."
                )

            emit(Finding(
                rule_id=f"{RULE_ID}.{severity}",
                severity=severity,
                what_happened=what_happened,
                what_to_do=what_to_do,
                technical_detail={
                    "rule_id": f"{RULE_ID}.{severity}",
                    "company_id": company_id,
                    "agent_id": agent.get("id"),
                    "agent_name": agent_name,
                    "spent_cents": spent,
                    "budget_cents": budget,
                    "pct_used": pct,
                },
            ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
