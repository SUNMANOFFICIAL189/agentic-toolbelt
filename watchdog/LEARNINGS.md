# HQ Watchdog — LEARNINGS

> The watchdog's own self-improvement log. Every change the watchdog makes
> to its own behaviour is recorded here — whether automatic (Zone A) or
> approved by Sunil (Zone B). Zone C changes are never made.
>
> **How to read an entry:** each one has a date, a zone tag, the action,
> the rationale, and the reversal instructions. Reverting any learning
> takes seconds.

---

## Three-zone model (the rules the watchdog plays by)

| Zone | What it means | Example |
|---|---|---|
| **A AUTO** | Happens without asking. Safe because there's no conflict of interest. | "Sessions on Sundays are slower — stop alerting on duration then" |
| **B APPROVED** | Watchdog proposes via Telegram, you approve with one letter. | "Raise the bar for noisy subagent alerts" |
| **C NEVER** | Never autonomous, never by proposal. Only Sunil, only by direct code or config change. | Silencing critical alerts, modifying this file's code, self-rewriting |

---

## Log

*No entries yet. This file grows as the watchdog learns. First entries expected after ~1 week of normal HQ use.*

---

## Reverting a learning

Each entry above has a "Reversal:" line describing exactly how to undo it.
Common patterns:

- **Delete this line / section** → the change is recorded only here; remove the entry, restart the watchdog
- **Run the reversal command shown** → for changes that touched baseline.json or metrics.yaml
- **Restore from git** → `git checkout HEAD~1 -- watchdog/metrics.yaml` for recent edits

If reversal instructions are ever missing or unclear, that's a bug — file it.

---

## Protected metrics (Zone C — cannot evolve)

These metrics have hardwired thresholds that neither Zone A nor Zone B can
modify. They protect against the watchdog quietly silencing itself on core
safety signals:

- `git_revert_on_claude_hq` — any revert alerts immediately, always
- `trust_gate_overrides` — any override alerts immediately, always
- `lessons_rule_velocity` — rule-burst alerts cannot be suppressed
- `repeated_mistake_signal` — repeat-mistake alerts cannot be suppressed
- `mission_board_before_agents` — plan-skipping alerts cannot be suppressed

To change these, edit `evolve.py` → `PROTECTED_METRICS` directly. Which is
a deliberate, reviewable code change — not an autonomous act.
