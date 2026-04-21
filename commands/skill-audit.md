---
name: skill-audit
description: "Run Magika + secret-scan over every installed skill (~/.claude/skills and project .claude/skills) to catch anything historically installed before the Trust Gate existed, or compromised after install. Returns a structured report."
---

# /skill-audit — Retrospective Trust Sweep

Runs the file-content layers of the Trust Gate (Magika Layer 1, secret-scan
Layer 2) across **already-installed** skills. Catches:

- Skills installed before the Trust Gate was wired (pre-2026-04-21)
- Skills compromised after install (e.g., manual edits, dependency pulls)
- Historical sprawl in `~/.claude/skills/` you've forgotten about

## Usage

```
/skill-audit                    # scan global + project scopes
/skill-audit --global           # global only
/skill-audit --project          # project only
/skill-audit --skill <name>     # specific skill directory
```

## What happens

1. Enumerate skill directories:
   - Global: `~/.claude/skills/*/`
   - Project: `.claude/skills/*/` (if cwd is a project)
2. For each skill directory, run:
   - `magika_scan` — extension-vs-detected-type mismatches
   - `secret_scan` — prompt injection + hardcoded secrets + fetch patterns
3. Produce a ranked report:
   - Clean skills listed with a ✓
   - Flagged skills listed with severity + specific findings
   - Summary: X clean / Y flagged / Z total
4. For any flagged skill, recommend either:
   - Review the flagged files and remove if malicious
   - Remove the skill entirely: `rm -rf <path>`

## What this command does NOT do

- Does NOT delete anything automatically.
- Does NOT run Socket/pip-audit — those are for install-time only
  (skills are markdown-first; behaviour scanners add little post-install).
- Does NOT fix findings — it reports, you decide.

## Output format

```
=== Skill Audit 2026-XX-XX ===
Global (~/.claude/skills): N skills
Project (./.claude/skills): M skills

✓ CLEAN (53):
  graphify, ui-ux-pro-max, ...

⚠ FLAGGED (2):
  some-skill: Magika mismatch
    README.md detected as shell script (score=0.91)
  other-skill: Prompt injection pattern
    SKILL.md line 42: "ignore all previous instructions..."

Recommendation: review each flagged skill manually. Remove compromised ones.
```

## Implementation

Delegates to `scripts/skill-install.sh` library functions directly — no
network calls, no install, no write operations beyond the audit report in
`scripts/.trust-gate.log`.
