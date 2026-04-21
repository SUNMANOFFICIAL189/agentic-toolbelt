---
name: scout
description: "Search the skills.sh ecosystem for a skill that matches the task at hand, then route the install through the full Tier C Trust Gate. Use whenever no matching tool exists in registry.json and the task would benefit from a community skill."
---

# /scout — Gated Skill Discovery

Search **skills.sh** (~91K skills), evaluate candidates, and install through the
Trust Gate — never blindly. Use this instead of `npx skills add` directly;
raw `npx skills add` is blocked by the PreToolUse hook.

## Usage

```
/scout <free-text query>
```

Example: `/scout kubernetes yaml linting for production deployments`

## What happens

1. **Query skills.sh** — `npx skills find "<query>"` surfaces the top N ranked
   results with install counts, authors, and descriptions.
2. **Present candidates to user** — rank by install count, filter out anything
   from an author in `commander/INCIDENT_LEDGER.md` cooling-off.
3. **User picks one** — explicit choice, no auto-select.
4. **Route through Tier C** — `scripts/skill-install.sh <owner/repo@skill>`
   runs all 5 layers (advisory → Magika → secret-scan → Socket → reputation).
5. **Install scope** — project by default (`.claude/skills/`). Promote to
   global only after 2+ clean uses.

## What this command does NOT do

- Does NOT install automatically — always asks user first.
- Does NOT bypass the Trust Gate — even for high-install-count skills.
- Does NOT search outside skills.sh — for other sources, use the standard
  Tier B hook on `git clone`.

## Rules

- If a search returns no result above 1,000 installs AND no author on the
  allowlist, report "no trustworthy candidate found" rather than offering
  low-reputation options.
- Skills in active cooling-off (Vercel through 2026-07-20) are filtered out
  silently — do not surface them.
- Every install decision is logged in `scripts/.trust-gate.log`.

## Output format

```
Top candidates for "<query>":
  1. owner/repo@skill  — 42K installs — <description>  [allowlist ✓]
  2. ...

To install: reply with the number (1, 2, …) or "none".
Install scope [project/global], default project:
```

Then invoke `scripts/skill-install.sh` with the chosen ref.
