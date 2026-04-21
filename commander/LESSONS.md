# LESSONS — Global Self-Improvement Log

> After ANY correction from the user, add a preventive rule here.
> Review this file at the start of every engagement.
> Rules should prevent mistakes, not just describe them.

---

## Rules

### 1. Never install external code without the Trust Gate
- **Rule:** Every `git clone`, `npm install`, `pip install`, `pipx install`,
  `cargo install --git`, and `npx skills add` passes through the Trust Gate
  (Tier B ambient hook + Tier C full pipeline for skills.sh).
- **Why:** Snyk Feb 2026 audit — 13.4% of skills.sh + ClawHub skills have
  critical issues (malware, prompt injection, secrets). Skill-based prompt
  injection succeeds 95.1% of the time vs 10.9% direct. The ecosystem is
  actively hostile.
- **How to apply:** The PreToolUse hook at `scripts/trust-gate.sh` is
  ambient — do not edit it away. For skill discovery, always use `/scout`,
  never `npx skills add` directly.

### 2. Install counts are a weak signal, not proof
- **Rule:** A skill with 1M installs is no more trustworthy than one with 100.
  Reputation is a tie-breaker when other layers pass, never an auto-pass.
- **Why:** Snyk data shows issue prevalence is roughly flat across install
  counts. The `find-skills` skill itself (1.1M installs) is published by
  vercel-labs — currently in cooling-off.
- **How to apply:** Trust Gate Layer 4 (reputation) runs AFTER Layers 0.5-3
  and only affects the auto-pass vs manual-review decision.

### 3. Allowlists decay — cooling-off overrides trust
- **Rule:** Any author/vendor with a publicly disclosed security incident in
  the last 90 days is demoted from allowlist to full Tier C scrutiny until
  90 days post-incident + published post-mortem + verified supply chain.
- **Why:** Vercel 2026-04-19 — compromised via a third-party AI tool
  (Context.ai) breaching an employee's Google Workspace. "We believe the
  supply chain is safe" is not "we have verified every artefact."
- **How to apply:** `commander/INCIDENT_LEDGER.md` holds active cooling-off.
  The advisory layer checks this BEFORE the allowlist — cooling-off wins.

### 4. Security-research skills will trigger Layer 2 false positives
- **Rule:** Skills authored by security research firms (trailofbits, snyk,
  lakera, etc.) will match prompt-injection/secret regex patterns because
  their documentation discusses the very patterns they're designed to detect.
  Treat Layer 2 FAIL from an allowlisted security author as manual-review
  required, not auto-block.
- **Why:** Shakedown 2026-04-21 on `trailofbits/skills` — flagged by Layer 2
  for YARA jailbreak detection docs, Firebase vulnerability research docs,
  Python sharp-edges notes (`subprocess shell=True` documented as DON'T).
  All legitimate security research content.
- **How to apply:** For allowlisted security research authors, review the
  specific file paths flagged. If all hits are in `references/` or `docs/`
  directories discussing patterns educationally, override with
  `HQ_TRUST_OVERRIDE=1`. Never auto-override for non-allowlisted authors.

### 5. Always query skills.sh before authoring a new skill
- **Rule:** Before building a new skill or slash command, run `/scout <task>`
  to check if the capability already exists in the ecosystem.
- **Why:** The ecosystem has ~91K skills. Most common needs are covered.
  Authoring duplicates wastes time and creates maintenance burden.
- **How to apply:** In Commander Step 2.5, skills.sh fallback runs after
  registry and Agent Bank scan. Only build new skills when `/scout` returns
  no adequate match (or all matches are low-reputation / in cooling-off).

### 6. Postinstall scripts run before hooks can stop them
- **Rule:** Our PreToolUse hook runs BEFORE the command, but `npm install`
  and `pip install` execute postinstall scripts AS PART OF the install, not
  after. PostToolUse scanning is retrospective for these.
- **Why:** Structural limitation of how package managers work — the hook
  cannot split install-time execution.
- **How to apply:** For npm/pip installs from unknown authors, prefer
  `--ignore-scripts` flag when available. For unknown authors, clone first
  (Tier B gated), scan with Tier C tools manually, then install.
