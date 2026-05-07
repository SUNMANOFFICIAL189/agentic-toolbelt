# PATS-Copy Architectural Watchdog (Tier 1)

**Status:** Phase 1 — scaffolding. Built 2026-05-07.

**Project:** PATS-Copy (Polymarket trading bot at `~/Desktop/POLYMARKET_TRADING_3.0`)
**Fingerprint:** `paper, realtime, many, multi-source, never, costly` (per `~/claude-hq/docs/project-watchdog/fingerprint-schema.md`)

---

## What this is

A scheduled detector that watches the PATS-Copy codebase + Supabase state for known classes of architectural drift. Sends Telegram alerts via the existing HQ Watchdog `telegram.py` pipeline when issues are detected.

**Important: this is a smoke detector, not a fire suppressor.** Tier 1 detects + alerts. It does NOT auto-fix anything. You receive an alert, investigate manually, write the fix yourself, deploy.

The "auto-fix-with-approval" capability is Tier 4 — months of additional work that builds on Tier 1's proven detection patterns. Don't expect Tier 1 to fix things for you.

---

## What Tier 1 catches (5 starter rules)

Each rule is calibrated against a real bug from the 2026-05-07 PATS-Copy session.

| # | Rule | Type | Catches |
|---|---|---|---|
| 1 | endDate flow integrity | Static (semgrep) | Hydration drop bug — `runner.ts` dropping `endDate` between input and storage |
| 2 | Side-aware pnl/loss formulas | Static (semgrep) | Side-blind stop-loss — `position-lifecycle.ts` formulas treating SELL like BUY |
| 3 | Single-source-of-truth trade tracking | Static (semgrep) | Dual-executor mismatch — `copyExecutor` and `signalExecutor` both holding signal-bot trades |
| 4 | Supabase ↔ memory consistency | Runtime (Python) | Stale "open" rows from failed close persistence |
| 5 | Cron entries reference existing files | Runtime (Python via SSH) | Broken cron — server cron pointing to deleted files like `health-check.sh` |

---

## What Tier 1 does NOT catch (be honest)

- Strategy quality issues (e.g., low WR, asymmetric sizing problems)
- Configuration tuning (e.g., timeout values, thresholds)
- Performance regressions (Tier 3 work)
- Design-level decisions (Tier 4 work)
- Bugs in patterns the watchdog hasn't been taught about

If the watchdog hasn't been taught a pattern, it can't detect that pattern. It supplements TDD + code review + types — doesn't replace them.

---

## Directory layout

```
~/claude-hq/watchdogs/pats/
├── README.md                          # this file
├── .gitignore                         # excludes audit.log, baseline.json, .venv
├── com.claude-hq.pats-watchdog.plist  # launchd plist (template, not auto-loaded)
├── rules/
│   ├── static/                         # semgrep rules (YAML)
│   │   ├── enddate-flow.yml
│   │   ├── side-aware-pnl.yml
│   │   └── single-trade-pool.yml
│   └── runtime/                        # Python runtime checks
│       ├── supabase_consistency.py
│       └── cron_file_existence.py
├── lib/
│   └── alerts.py                       # wraps HQ Watchdog's telegram.py PlainAlert
├── orchestrator.py                     # main entry point — runs all rules
├── audit.log                           # gitignored, history of findings
└── baseline.json                       # gitignored, first-run snapshot for diffing
```

---

## How it runs

- **Where**: Mac, scheduled via launchd
- **When**: every 30 min for static checks (semgrep), every 5 min for runtime checks (Python)
- **What it reads**: PATS-Copy code from `~/Desktop/POLYMARKET_TRADING_3.0`, Supabase state via creds in `~/claude-hq/watchdog/.env`
- **Where it logs**: `audit.log` in this directory
- **How it alerts**: reuses `~/claude-hq/watchdog/telegram.py` PlainAlert pattern (Lesson 16 — plain English, what_happened + what_to_do)

---

## 14-day observe-only soak

Per `~/claude-hq/docs/project-watchdog/`, watchdogs start in observe-only mode for 14 days:

- Findings logged to `audit.log` ✓
- Telegram alerts SUPPRESSED ✗

Why: prevents alert fatigue from initial false positives during calibration. If a rule fires constantly during soak, we tune it BEFORE going live.

After 14 days of clean baseline (or earlier if rules look stable), flip alerting on by setting `ALERT_MODE=active` in `~/claude-hq/watchdog/.env`.

A reminder is set in `~/claude-hq/watchdog/reminders.json` for 14 days post-deploy: "PATS watchdog soak ending — review audit.log + flip to active?"

---

## How to run manually

```bash
cd ~/claude-hq/watchdogs/pats
python3 orchestrator.py            # runs all rules, prints findings
python3 orchestrator.py --soak     # observe-only mode (default for first 14 days)
python3 orchestrator.py --active   # active alerting (after soak)
python3 orchestrator.py --rule enddate-flow   # run one specific rule
```

---

## What's NOT in Tier 1 (deferred)

Per the design at `~/claude-hq/docs/project-watchdog/`, the full vision includes:

- **Fingerprint schema** — defer until 2nd project exists
- **Promotion gate** — defer until cross-project rules emerge
- **Performance regression detection** — Tier 3
- **Backtest-gated fix proposals** — Tier 4
- **Auto-PR fix submission** — Tier 4

Tier 1 ships first. Tier 2/3/4 layer in only after Tier 1 has proven its detection accuracy.

---

## References

- Design docs: `~/claude-hq/docs/project-watchdog/`
- HQ Watchdog (parent): `~/claude-hq/watchdog/`
- PATS-Copy code: `~/Desktop/POLYMARKET_TRADING_3.0/`
- Plain-English alert pattern: Lesson 16 in `~/claude-hq/commander/LESSONS.md`
- Trust Gate concerns about `uzucky/watchdog-ai`: `~/claude-hq/docs/BACKLOG.md` (2026-05-07 entry)
