# TRUST GATE — Supply-Chain Security Protocol for Claude HQ

> Defence-in-depth pipeline for any external code entering this system.
> Active since 2026-04-21. Mandatory for all skills.sh installs and any clone
> from non-allowlisted authors.

---

## Why this exists

Snyk audit of 3,984 skills on skills.sh + ClawHub (February 2026):
- **13.4%** contain critical security issues (malware, prompt injection, exposed secrets)
- **36.8%** have at least one security flaw
- **76 skills confirmed actively malicious**
- **10.9%** contain hardcoded secrets
- **Skill-based prompt injection achieves 95.1% success** (vs 10.9% direct)

Install counts are weak signals. The ecosystem is actively hostile.
We build our own gate. This is it.

---

## Architecture

Two tiers, one shared engine:

**Tier B — Ambient** (PreToolUse + PostToolUse hooks)
- Fires on `git clone`, `npm install`, `pip install`, `pipx install`, `cargo install --git`
- PreToolUse: metadata gate (author allowlist + INCIDENT_LEDGER)
- PostToolUse: file-content scan (Magika + secret-scan) after clone

**Tier C — Full pipeline** (`scripts/skill-install.sh`, called by `/scout`)
- All 4 layers mandatory regardless of author
- For skills.sh installs and any unknown-author install

## The 5 layers

### Layer 0.5 — Advisory check (`lib/advisory-check.sh`)
Metadata-only. Runs at PreToolUse when files don't exist yet.
- Parse owner from URL or `owner/repo` ref
- Consult `commander/INCIDENT_LEDGER.md` for cooling-off status
- Consult allowlist
- Returns: allowlist (auto-pass) / cooling-off (block) / unknown (Tier C required)

### Layer 1 — Magika file-type integrity (`lib/magika-core.sh`)
Google's AI file-type classifier. ~5ms per file, 99% accuracy.
- Catches extension-spoofed payloads
- Flags `.md` files that are actually executables, `.pdf` that's a Python script, etc.
- HARD FAIL on any mismatch

### Layer 2 — Prompt-injection + secret scan (`lib/secret-scan.sh`)
Grep-based static analysis targeting known attack patterns.
- Prompt-injection markers (OWASP Agentic Skills Top 10 baseline)
- Third-party content fetchers (`curl … | bash`, `eval(requests…)`)
- Hardcoded secret patterns (OpenAI, Anthropic, GitHub PAT, AWS, Slack, private keys)
- HARD FAIL on any hit

### Layer 3 — Package behavioural scan (`lib/socket-core.sh`)
Industry-grade malicious package detection.
- Socket CLI (npm) — catches typosquatting, compromised maintainers, obfuscated code.
  Socket surfaced the Axios 4.2.1 compromise in 6 minutes after registry publish.
- pip-audit (Python) — CVE database check against requirements.txt / pyproject.toml
- HARD FAIL on high/critical

### Layer 4 — Reputation (weak signal, tie-breaker only)
- Author allowlist check (see `lib/advisory-check.sh`)
- Install count threshold (skills.sh API — to be wired v2)
  - ≥10K installs + trusted author: auto-pass
  - 1K–10K: manual review required
  - <1K: blocked unless author on allowlist
- **Never a pass by itself** — Snyk data shows 13.4% critical issues regardless of count

---

## OWASP Agentic Skills Top 10 mapping

| OWASP category | Our layer |
|---|---|
| AS01 Malicious Skill Distribution | Layers 0.5, 1, 3 |
| AS02 Prompt Injection via Skills | Layer 2 |
| AS03 Credential/Secret Exposure | Layer 2 |
| AS04 Untrusted Third-Party Content | Layer 2 (fetch pattern detection) |
| AS05 Typosquatting / Confused Deputy | Layer 3 (Socket) |
| AS06 Supply-Chain Compromise (maintainer) | Layer 0.5 (INCIDENT_LEDGER) + Layer 3 |
| AS07 Obfuscated Payloads | Layer 1 (Magika) + Layer 3 (Socket) |
| AS08 Privilege Escalation | Layer 4 (scope: project before global) |
| AS09 Data Exfiltration | Layer 2 (fetch detection) + Layer 3 |
| AS10 Insecure Dependencies | Layer 3 (pip-audit, Socket) |

---

## Author allowlist (Layer 0.5)

Defined in `scripts/lib/advisory-check.sh`. Current list:

- `SUNMANOFFICIAL189` (you)
- `anthropics`
- `google`
- `microsoft`
- `thedotmack`
- `affaan-m`
- `trailofbits`
- `ChristopherKahler`
- `keshavsuki`
- `ruvnet`

**Deliberately excluded (cooling-off):** `vercel/*`, `vercel-labs/*` until 2026-07-20.

**Allowlist does not skip Layer 1.** File-content scans still run after clone.

---

## Operational contract

### When Tier B fires (PreToolUse)
1. Hook receives Bash tool call JSON
2. If command is not an install pattern → allow immediately
3. Extract owner from URL/ref
4. Call `advisory_check`
5. Result:
   - Allowlisted → allow, PostToolUse will still scan content
   - Cooling-off → block with exit 2 + reason to stderr
   - Unknown → block with pointer to `/scout` or Tier C
6. Override mechanism: `HQ_TRUST_OVERRIDE=1 <command>` — logged, not silent

### When Tier C fires (explicit invocation)
1. `scripts/skill-install.sh owner/repo@skill [--scope project|global]`
2. Layer 0.5 (advisory) — cooling-off blocks immediately
3. Clone to `/tmp/skill-staging-$$/src`
4. Layer 1 (Magika) → HARD FAIL exits
5. Layer 2 (secret-scan) → HARD FAIL exits
6. Layer 3 (Socket/pip-audit if manifests present) → HARD FAIL exits
7. Layer 4 (reputation — weak tie-breaker)
8. Copy approved files to project (`.claude/skills/`) or global (`~/.claude/skills/`)
9. Default scope: project. Promote to global after 2 clean uses.

### When PostToolUse fires (after git clone)
1. Locate the cloned directory
2. Run Magika + secret-scan
3. If issues: warn loudly with `rm -rf` recommendation (non-blocking — work already done)
4. If clean: silent pass, log entry

---

## Override protocol

Three legitimate override scenarios:

1. **You authored the repo being cloned** — add to allowlist rather than overriding
2. **You need to investigate a known-bad repo** — use `HQ_TRUST_OVERRIDE=1`, scan
   with throwaway directory, rm afterwards
3. **Scan tools error out transiently** — investigate the scanner first, do not blindly
   override

Every override is logged in `scripts/.trust-gate.log`. Review quarterly.

---

## Known gaps (being transparent)

- `npm install` / `pip install` postinstall scripts run during install. Our hook runs
  before and after, but cannot stop a running postinstall. Mitigation: Layer 3 (Socket)
  catches most malicious packages before you'd ever install them.
- Hooks only fire inside Claude Code sessions. `git clone` in your plain shell is
  ungated. Run a manual `scripts/trust-gate-post.sh <dir>` for those.
- Layer 2 is regex-based — sophisticated obfuscated prompt injection can evade it.
  Claude Code Security (web) provides deeper code reasoning if needed as escalation.
- Layer 4 install-count API not yet wired — threshold enforcement is documented but
  not automated yet. Manual check via `npx skills find` until v2.

---

## Maintenance

- Review `INCIDENT_LEDGER.md` monthly — expire entries past their cooling-off date
- Review allowlist quarterly — any member with a public incident → cooling-off
- Update regex patterns in `secret-scan.sh` when new injection patterns are published
- Re-read this file at HQ activation (Commander Step 1)
