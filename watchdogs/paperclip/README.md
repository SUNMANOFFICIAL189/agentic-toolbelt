# Paperclip Watchdog (Tier 1)

**Status:** Phase 1 — built 2026-05-08 alongside the multi-model routing build.

**Project:** Paperclip control plane at `~/projects/paperclip` (server on `http://localhost:3100`).

---

## What this is (in plain English)

A small Python program that wakes up every 5 minutes, peeks at Paperclip,
checks for known classes of trouble, and (after the 14-day soak window)
sends a plain-English Telegram alert if it finds any.

**It is a smoke detector, not a fire suppressor.** Tier 1 detects + alerts.
It does NOT auto-fix anything. You receive an alert, investigate manually,
fix it yourself, deploy.

The "auto-fix-with-approval" capability is Tier 4 — months of additional
work that builds on Tier 1's proven detection patterns. Don't expect Tier 1
to fix things for you.

This watchdog is the second tenant of the `~/claude-hq/watchdogs/` framework
(PATS was the first). The shared library, soak protocol, audit format, and
launchd patterns all match PATS by design.

---

## What Tier 1 catches (4 rules, calibrated to 2026-04-28 quota incident)

| # | Rule | Severity it can emit | What it catches |
|---|---|---|---|
| 1 | `server_health.py` | critical | Paperclip server stopped answering. Most important rule — the rest can't run if the server's down. |
| 2 | `healthchecks_io_relay.py` | warn | Paperclip is alive but the watchdog couldn't tell Healthchecks.io about it (or the watchdog itself can't ping). Forwards both pings each cycle so HC.io's "silence is the alarm" works. |
| 3 | `token_burn_rate.py` | warn / critical | Sustained tokens-per-minute over 5 minutes exceeds the threshold — the 2026-04-28 incident shape. Warn at 500K/min, critical at 2M/min. |
| 4 | `agent_quota_threshold.py` | warn / critical | Per-agent monthly budget approaching cap. Warn at 80%, critical at 95%, before Paperclip's 100% auto-pause kicks in. |

---

## What Tier 1 does NOT catch (be honest)

- **Stale heartbeat detection** — agent should have woken but didn't. Deferred to Phase 2.
- **High failure-rate detection** — too many runs failing in a window. Deferred to Phase 2.
- **Stuck queued-run detection** — runs queued but not executing. Deferred to Phase 2.
- **Strategy-quality issues** — the watchdog doesn't know if your agents are doing good work, only that they're alive and within budget.
- **Bugs in patterns the watchdog hasn't been taught about.**

The deferred rules are tracked in `~/claude-hq/docs/BACKLOG.md`. They wait
until Paperclip's REST API surface for runtime state is more thoroughly
mapped, and until soak data tells us what "normal" looks like.

---

## Directory layout

```
~/claude-hq/watchdogs/paperclip/
├── README.md                                  # this file
├── .gitignore                                 # excludes audit.log, state.json, .venv, logs
├── com.claude-hq.paperclip-watchdog.plist     # launchd plist (template, not auto-loaded)
├── orchestrator.py                            # main entry point — runs all rules
├── audit.log                                  # gitignored, history of findings
├── state.json                                 # gitignored, alert rate-limit state
├── lib/
│   ├── __init__.py
│   ├── finding.py                             # shared Finding dataclass (mirrors PATS)
│   ├── alerts.py                              # Finding → PlainAlert → Telegram (via HQ telegram.py)
│   └── paperclip_api.py                       # thin REST client for Paperclip
└── rules/
    └── runtime/
        ├── server_health.py
        ├── healthchecks_io_relay.py
        ├── token_burn_rate.py
        └── agent_quota_threshold.py
```

No `rules/static/` directory — Paperclip core code is upstream's, not ours,
so semgrep static rules don't make sense here.

---

## How it runs

- **Where:** Mac, scheduled via launchd
- **When:** every 5 minutes (faster than PATS's 30-min cycle because Paperclip burn rate spikes evolve in minutes, not commits)
- **What it reads:**
  - Paperclip REST endpoints at `http://localhost:3100` (via `lib/paperclip_api.py`)
  - Healthchecks.io URLs from `~/claude-hq/watchdog/healthchecks-urls.env`
  - `PAPERCLIP_COMPANY_IDS` env var (comma-separated, falls back to Agent Alpha default)
- **Where it logs:** `audit.log` in this directory (gitignored)
- **How it alerts:** reuses `~/claude-hq/watchdog/telegram.py` PlainAlert pattern (Lesson 16 — plain English, what_happened + what_to_do). Alerts prefixed `[Paperclip]` to distinguish from PATS findings.

---

## 14-day observe-only soak

Per `~/claude-hq/docs/project-watchdog/`, watchdogs start in observe-only
mode for 14 days. Soak ends **2026-05-22**.

- Findings logged to `audit.log` ✓
- Telegram alerts SUPPRESSED ✗

Why: prevents alert fatigue from initial false positives during calibration.
If a rule fires constantly during soak, we tune it BEFORE going live.

After 14 days of clean baseline (or earlier if rules look stable), flip to
active mode by editing the launchd plist's argument from `--soak` to
`--active`.

A reminder is set in `~/claude-hq/watchdog/reminders.json` for 2026-05-22:
"Paperclip watchdog soak ending — review audit.log + flip to active?"

---

## How to run manually

```bash
cd ~/claude-hq/watchdogs/paperclip
python3 orchestrator.py                                 # runs all rules, soak mode
python3 orchestrator.py --once-stdout                   # JSON lines to stdout (dev)
python3 orchestrator.py --active                        # send Telegram for warn|critical
python3 rules/runtime/server_health.py                  # one specific rule
```

To install on launchd:

```bash
cp com.claude-hq.paperclip-watchdog.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.claude-hq.paperclip-watchdog.plist
launchctl kickstart -k gui/$(id -u)/com.claude-hq.paperclip-watchdog
```

---

## Healthchecks.io setup (required for Layer 2 dead-man's switch)

The user has an existing Healthchecks.io account already used by PATS.
For Paperclip, two new "checks" need to be created in the same account:

1. **`paperclip-server`** — period 5 min, grace 10 min. Tag: `paperclip`.
2. **`paperclip-watchdog`** — period 5 min, grace 10 min. Tag: `paperclip`.

After creating them, copy each ping URL into `~/claude-hq/watchdog/healthchecks-urls.env`:

```bash
HC_PING_PAPERCLIP_SERVER=https://hc-ping.com/<uuid-1>
HC_PING_PAPERCLIP_WATCHDOG=https://hc-ping.com/<uuid-2>
```

The watchdog reads both at run time. Without these, the `healthchecks_io_relay`
rule emits an `info`-severity finding noting that setup isn't complete.
Healthchecks.io's existing Telegram integration (already configured for PATS)
covers the alert routing automatically.

---

## What's NOT in Tier 1 (deferred)

Per the design at `~/claude-hq/docs/project-watchdog/`, the full vision includes:

- **Stale heartbeat / failure-rate / stuck-run rules** — Phase 2 of this watchdog
- **Promotion gate** — defer until cross-project rules emerge
- **Performance regression detection** — Tier 3
- **Backtest-gated fix proposals** — Tier 4
- **Auto-PR fix submission** — Tier 4

Tier 1 ships first. Tier 2/3/4 layer in only after Tier 1 has proven its
detection accuracy.

---

## References

- Sibling watchdog (template): `~/claude-hq/watchdogs/pats/` and its README
- Design docs: `~/claude-hq/docs/project-watchdog/` (if present)
- HQ Watchdog (parent / shared infra): `~/claude-hq/watchdog/`
- Plain-English alert pattern: Lesson 16 in `~/claude-hq/commander/LESSONS.md`
- Plain-English chat pattern (sister doctrine): `~/claude-hq/commander/COMMUNICATION.md`
- Burn-rate calibration source: `~/.claude/projects/-Users-sunil-rajput/memory/project_quota_incident_2026_04_28.md`
- Existing manual burn tracker (superseded by `token_burn_rate.py`): `~/claude-hq/scripts/paperclip-burn-tracker.py`
