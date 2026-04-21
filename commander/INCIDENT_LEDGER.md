# INCIDENT LEDGER — Vendor Cooling-Off Register

> Machine-readable register of vendors currently in a post-incident cooling-off period.
> Consumed by `scripts/lib/advisory-check.sh`. Format is strict — do not reformat.
>
> **Rule:** Any author/vendor with a publicly disclosed security incident in the last
> 90 days is auto-demoted from the Trust Gate allowlist to full Tier C scrutiny.
> Re-admission requires: (a) 90 days since incident closure, (b) published post-mortem,
> (c) verified supply chain integrity.

## Active cooling-off periods

The lines below are parsed by regex: `^COOLING_OFF:\s+<owner>/...\s+until\s+<YYYY-MM-DD>`

COOLING_OFF: vercel/* until 2026-07-20
COOLING_OFF: vercel-labs/* until 2026-07-20

## Entry details

### vercel/* and vercel-labs/*
- **Incident date:** 2026-04-19
- **Cooling-off until:** 2026-07-20 (90 days)
- **Source:** https://vercel.com/kb/bulletin/vercel-april-2026-security-incident
- **Summary:** Unauthorised access to Vercel internal systems via compromised third-party
  AI tool (Context.ai) → employee Google Workspace takeover → Vercel environments.
  Limited non-sensitive env vars exposed. npm packages confirmed not compromised per
  Vercel + GitHub + Microsoft + npm + Socket.
- **Rationale for cooling-off despite clean supply chain:** "Believed safe" ≠ "proven clean."
  Forensics post-window; cooling-off is elevated scrutiny, not an accusation. Vercel-labs
  also owns the `find-skills` skill (1.1M installs) which would otherwise be a default
  install — we use our own `/scout` wrapper instead during cooling-off.
- **Re-admission criteria:** Public post-mortem + 90 days of clean operations + one
  independent supply-chain review.

## Expired entries (historical — do not re-enable without review)

_None yet._

## Format reference (for future entries)

```
COOLING_OFF: <github-owner>/* until <YYYY-MM-DD>
```
Then a prose block following the template above. Keep entries even after expiry —
the history is useful for future trust decisions.
