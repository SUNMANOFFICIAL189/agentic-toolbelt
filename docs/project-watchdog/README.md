# Project-Native Watchdog — Design Docs

**Status:** Design phase. No code yet. Being written while the HQ Watchdog collects baseline data.

**Motivation:** Every new project should spawn a dedicated watchdog at creation. Watchdogs across projects share a rule library that compounds — what one watchdog learns from a failure on Project A becomes latent intelligence for the watchdog on Project B. Pre-emptive oversight, formalised and portable.

**Reference implementation:** `~/claude-hq/watchdog/` — the HQ Watchdog is the single-project prototype. Extending to project-native is an extension, not a rebuild.

---

## The three load-bearing pieces

The whole system stands or falls on three design decisions. Each has its own doc:

| Doc | What it defines | Why it's load-bearing |
|---|---|---|
| [fingerprint-schema.md](fingerprint-schema.md) | The 6 dimensions that describe any project | Wrong fingerprint → rules inherited into projects they don't fit (noise) |
| [rule-tagging-schema.md](rule-tagging-schema.md) | How rules are labelled for inheritance | Wrong tags → good rules get missed, bad rules get auto-spread |
| [promotion-gate.md](promotion-gate.md) | How a local rule becomes canonical | No gate → rule drift and contradictions across watchdogs |

---

## Living docs — how these evolve

Each doc opens with **Revision triggers** — specific conditions under which we revisit it. No scheduled reviews, no calendar. The docs adapt when reality pushes back against them.

When a revision fires:
1. Edit the doc (git tracks every change)
2. Update `Last revised` date at the top
3. Note the trigger that caused the revision in the commit message

Core principles (at the bottom of each doc) are protected — those don't casually change. Schema details evolve freely.

---

## What's NOT decided yet

- Whether the watchdog-per-project runs as its own process or as a module inside the project
- Whether rules live in the per-project vault folder or in a shared registry
- How the operator-approval flow works when multiple projects' watchdogs propose rules at once

These get settled during implementation, not during design. The three docs above are the minimum we need before we can start coding.

---

## Relationship to HQ Watchdog

The HQ Watchdog's architecture already embodies the patterns these docs formalise:

| HQ Watchdog concept | Project-watchdog equivalent |
|---|---|
| Metrics with `plain_language` blocks | Rules with `fingerprints` + `mechanisms` tags |
| Zone A / B / C evolution | Local / Candidate / Canonical / Retired lifecycle |
| `LEARNINGS.md` with revision entries | Promotion-gate digest + rule provenance |
| `runtime_state.json` with pause/quiet/mute | Per-project watchdog config |
| Telegram two-way control | Same mechanism, scaled across project fleet |

So none of this is novel infrastructure. It's the HQ pattern scaled outward.

---

## Sequencing

```
Now        → Design docs (this folder). No code.
Week 1     → HQ Watchdog baseline week completes. Docs get stress-tested in review.
Week 2-3   → Build: extract HQ Watchdog into a reusable template.
Week 4     → Pilot: retrofit PATS-Copy as the first project-native watchdog.
Week 5-6   → Calibration pass. Reduce false positives. Refine the three schemas.
Week 7     → Modify Commander Step 0 to instantiate a watchdog on project creation.
Week 8+    → First new project gets a watchdog at spawn, automatically.
```

Anything post-Week 6 gets re-planned based on what the pilot reveals.

---

*Last revised: 2026-04-24*
