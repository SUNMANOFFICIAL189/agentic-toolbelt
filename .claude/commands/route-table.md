---
description: Show the model routing keyword table (MODEL_ROUTING.md §5) as a quick cheat sheet.
---

Display the following table verbatim to the user:

| Task shape | Keywords | Tier | Why |
|---|---|---|---|
| Mechanical file ops | rename, format, lint, prettier, normalise | **Haiku** | Pure mechanical — no reasoning. |
| Per-page summarisation | summarise, extract, condense, tldr | **Haiku** | Below Sonnet's threshold. |
| Bulk classification | classify, categorise, tag, label | **Haiku** | High-volume, low-judgement. |
| Standard implementation | implement, build, add feature, fix bug | **Sonnet** | Default for code work. |
| Code review (non-adversarial) | review, audit (general), simplify | **Sonnet** | Adversarial reviews → hard floor. |
| Multi-source synthesis | synthesise, compile findings, merge | **Sonnet** | Synthesis sweet spot. |
| Test writing | write tests, tdd, coverage | **Sonnet** | Default. |
| Refactor proposals | refactor, restructure, decompose | **Sonnet** | |
| Architecture / system design | architect, design, blueprint, plan system | **Opus** | Hard floor — architecture decisions cascade. |
| Adversarial / red-team | red-team, adversarial, threat-model, contradict | **Opus** | Hard floor. |
| Long-context analysis (>150K tokens) | (caller tags `long-context`) | **Opus** (1M context) | Sonnet/Haiku cap at 200K. |
| Investor comms / materials | pitch, deck, memo, investor, fundraise | **Opus** | Hard floor. |
| Legal / compliance | legal, compliance, regulatory, license | **Opus** | Hard floor. |

Then add this footer:

> **Hard floor agents** (always Opus regardless of keywords): `*-reviewer`, `architect`, `red-team`, `investor-*`, `legal-review`, `security-review`.
>
> **Overrides** (set in shell): `HQ_ROUTER_OFF=1`, `HQ_MODEL_OVERRIDE=opus|sonnet|haiku`, `HQ_MODEL_FLOOR=sonnet`, `HQ_QUOTA_AWARENESS=off`.
>
> Full doctrine: `~/claude-hq/commander/MODEL_ROUTING.md`. Use `/route preview "<text>"` to dry-run any task description.

No tool calls needed. Just print the table and footer above.
