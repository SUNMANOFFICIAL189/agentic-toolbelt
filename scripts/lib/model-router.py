#!/usr/bin/env python3
"""
Model routing hook — PreToolUse handler for Agent dispatches.

Doctrine: ../commander/MODEL_ROUTING.md (single source of truth).
This script implements §3 (decision algorithm) and §5 (doctrine table).
Keep DOCTRINE / HARD_FLOOR_PATTERNS in sync with that file.

Reads hook JSON from stdin, decides the right tier, logs the decision to
the cost ledger, prints a transparency banner to stderr, and (where Claude
Code supports it) modifies tool_input.model.

Exit code: always 0 — never block dispatches. Degraded routing is the
failure mode, not a halted Agent call.

Modes:
  Normal   — invoked by Claude Code as a PreToolUse hook
  Dry-run  — set HQ_DRY_RUN=1, suppresses ledger writes + JSON output;
             still prints the transparency banner. Used by /route preview.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Doctrine — mirror of MODEL_ROUTING.md §4 + §5. Keep in sync.
# --------------------------------------------------------------------------

HARD_FLOOR_PATTERNS = [
    "red-team", "redteam", "adversarial",
    "reviewer",  # *-reviewer (security-, code-, cpp-, python-, etc.)
    "security-review",
    "investor-comms", "investor-materials", "investor-outreach",
    "legal-review",
    "architect", "code-architect",
]

# (priority, [keywords], tier, label) — higher priority wins on multi-match
DOCTRINE = [
    # Opus tier (priority 30)
    (30, ["red-team", "adversarial", "threat-model", "contradict"], "opus", "adversarial"),
    (30, ["architect", "design", "blueprint", "plan system"], "opus", "architecture"),
    (30, ["pitch", "deck", "memo", "investor", "fundraise"], "opus", "investor-comms"),
    (30, ["legal", "compliance", "regulatory", "license"], "opus", "legal/compliance"),
    (30, ["long-context"], "opus", "long-context"),

    # Sonnet tier (priority 20)
    (20, ["implement", "build", "add feature", "fix bug"], "sonnet", "implementation"),
    (20, ["review", "audit", "simplify"], "sonnet", "code-review"),
    (20, ["synthesise", "synthesize", "compile findings", "merge"], "sonnet", "synthesis"),
    (20, ["write tests", "tdd", "coverage"], "sonnet", "testing"),
    (20, ["refactor", "restructure", "decompose"], "sonnet", "refactor"),

    # Haiku tier (priority 10)
    (10, ["rename", "format", "lint", "prettier", "normalise", "normalize"], "haiku", "mechanical"),
    (10, ["summarise", "summarize", "extract", "condense", "tldr"], "haiku", "summarisation"),
    (10, ["classify", "categorise", "categorize", "tag", "label"], "haiku", "classification"),
]

DEFAULT_TIER = "sonnet"
TIER_ORDER = {"haiku": 0, "sonnet": 1, "opus": 2}
VALID_TIERS = set(TIER_ORDER.keys())

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

HQ_ROOT = Path(os.environ.get("HQ_ROOT", str(Path.home() / "claude-hq")))
LEDGER_PATH = HQ_ROOT / "run" / "cost-ledger.sqlite"
LOG_PATH = HQ_ROOT / "scripts" / ".model-router.log"

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def log_debug(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


def banner(text: str) -> None:
    """Visible in conversation via stderr."""
    sys.stderr.write(f"→ {text}\n")
    sys.stderr.flush()


def normalise_tier(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower()
    return v if v in VALID_TIERS else None


# --------------------------------------------------------------------------
# Decision logic — §3 algorithm
# --------------------------------------------------------------------------


def is_hard_floor(subagent_type: str) -> bool:
    if not subagent_type:
        return False
    name = subagent_type.lower()
    return any(p.lower() in name for p in HARD_FLOOR_PATTERNS)


def doctrine_match(prompt: str) -> tuple[str, str]:
    if not prompt:
        return DEFAULT_TIER, "default"
    p = prompt.lower()
    best: tuple[int, str, str] | None = None
    for priority, keywords, tier, label in DOCTRINE:
        for kw in keywords:
            if kw in p:
                if best is None or priority > best[0]:
                    best = (priority, tier, f"'{kw}' → {label}")
                break
    if best is None:
        return DEFAULT_TIER, "default"
    return best[1], best[2]


def apply_floor(tier: str, floor: str | None) -> tuple[str, bool]:
    """Return (resulting_tier, did_apply_floor)."""
    if not floor:
        return tier, False
    if TIER_ORDER.get(tier, -1) < TIER_ORDER[floor]:
        return floor, True
    return tier, False


def decide(tool_input: dict) -> tuple[str, str]:
    """
    Apply §3 decision algorithm. Returns (chosen_tier, reason).

    Order:
      1. HQ_ROUTER_OFF=1                     → pass-through, no routing applied
      2. Pick a candidate tier:
           a. HQ_MODEL_OVERRIDE if set       → that tier
           b. else caller-supplied model:    → caller's choice
           c. else doctrine keyword match    → tier from §5 table
           d. else default                   → DEFAULT_TIER (sonnet)
      3. Hard floor guard: if subagent kind is on the §4 list, force opus
         (this beats every choice in step 2 except HQ_ROUTER_OFF).
      4. HQ_MODEL_FLOOR guard: never go below the user-set floor.
    """
    # 1. Router off entirely
    if os.environ.get("HQ_ROUTER_OFF") == "1":
        return tool_input.get("model") or DEFAULT_TIER, "router-off"

    subagent_type = tool_input.get("subagent_type", "") or ""

    # 2. Pick candidate tier
    candidate_tier = None
    candidate_reason = ""

    override = normalise_tier(os.environ.get("HQ_MODEL_OVERRIDE"))
    if override:
        candidate_tier = override
        candidate_reason = f"env-override (HQ_MODEL_OVERRIDE={override})"

    if not candidate_tier:
        requested = normalise_tier(tool_input.get("model"))
        if requested:
            candidate_tier = requested
            candidate_reason = "caller-supplied"

    if not candidate_tier:
        prompt = tool_input.get("prompt", "") or ""
        tier, label = doctrine_match(prompt)
        candidate_tier = tier
        candidate_reason = label

    # 3. Hard floor — overrides candidate (§4: refuse all downgrades)
    if is_hard_floor(subagent_type):
        if TIER_ORDER[candidate_tier] < TIER_ORDER["opus"]:
            return "opus", f"hard-floor ({subagent_type}; candidate was {candidate_tier})"
        return "opus", f"hard-floor ({subagent_type})"

    # 4. HQ_MODEL_FLOOR
    floor = normalise_tier(os.environ.get("HQ_MODEL_FLOOR"))
    new_tier, applied = apply_floor(candidate_tier, floor)
    if applied:
        return new_tier, f"floor (HQ_MODEL_FLOOR={floor}; candidate was {candidate_tier})"

    return candidate_tier, candidate_reason


# --------------------------------------------------------------------------
# Cost ledger
# --------------------------------------------------------------------------

LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS routing_decisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT    NOT NULL,
    session_id      TEXT,
    project         TEXT,
    agent_kind      TEXT,
    task_summary    TEXT,
    model_requested TEXT,
    model_chosen    TEXT    NOT NULL,
    override_reason TEXT,
    matched_keyword TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    cost_usd        REAL,
    duration_ms     INTEGER,
    status          TEXT
);
CREATE INDEX IF NOT EXISTS idx_ts      ON routing_decisions(ts);
CREATE INDEX IF NOT EXISTS idx_session ON routing_decisions(session_id);
CREATE INDEX IF NOT EXISTS idx_project ON routing_decisions(project);
"""


def write_decision(record: dict) -> None:
    try:
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(LEDGER_PATH)
        try:
            conn.executescript(LEDGER_SCHEMA)
            conn.execute(
                """
                INSERT INTO routing_decisions (
                    ts, session_id, project, agent_kind, task_summary,
                    model_requested, model_chosen, override_reason,
                    matched_keyword, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["ts"],
                    record.get("session_id"),
                    record.get("project"),
                    record.get("agent_kind"),
                    record.get("task_summary"),
                    record.get("model_requested"),
                    record["model_chosen"],
                    record.get("override_reason"),
                    record.get("matched_keyword"),
                    "queued",
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        log_debug(f"ledger write failed: {e}")


# --------------------------------------------------------------------------
# Entry
# --------------------------------------------------------------------------


def main() -> int:
    dry_run = os.environ.get("HQ_DRY_RUN") == "1"

    try:
        raw = sys.stdin.read()
        if not raw.strip():
            log_debug("empty stdin; no-op")
            return 0
        hook_input = json.loads(raw)
    except Exception as e:
        log_debug(f"parse error: {e}")
        return 0

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Agent":
        return 0

    tool_input = hook_input.get("tool_input", {}) or {}
    session_id = hook_input.get("session_id")
    cwd = hook_input.get("cwd") or os.getcwd()
    project = Path(cwd).name

    chosen_tier, reason = decide(tool_input)
    requested = tool_input.get("model")
    subagent_kind = tool_input.get("subagent_type") or "general-purpose"
    prompt_text = (tool_input.get("prompt") or "").strip().replace("\n", " ")
    prompt_summary = prompt_text[:120]

    # Transparency banner — always prints
    if requested and normalise_tier(requested) != chosen_tier:
        banner(
            f"Routed {subagent_kind} → {chosen_tier} "
            f"({reason}; caller asked for {requested})"
        )
    else:
        banner(f"Routed {subagent_kind} → {chosen_tier} ({reason})")

    if dry_run:
        # Don't log, don't emit hook output — preview only
        return 0

    # Log decision
    write_decision({
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "project": project,
        "agent_kind": subagent_kind,
        "task_summary": prompt_summary,
        "model_requested": requested,
        "model_chosen": chosen_tier,
        "override_reason": reason.split(" (", 1)[0],
        "matched_keyword": reason,
    })

    # Hook output — allow + (forward-compatible) modifyToolInput
    output: dict = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": f"routed → {chosen_tier} ({reason})",
        }
    }
    # Best-effort tool_input override for newer Claude Code versions
    if normalise_tier(requested) != chosen_tier:
        output["modifyToolInput"] = {"model": chosen_tier}

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
