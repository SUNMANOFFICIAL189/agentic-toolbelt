# PATTERNS — reusable templates and design patterns

> **Curated library of patterns we've reused at least once and would
> reuse again.** Read at task start (via `memory-probe.sh`) so we
> reach for an existing template before re-deriving.
>
> A "pattern" earns a place here when it has been applied to **two or
> more different problems** with successful results. Single-use
> ideas live in Decision Log entries, not here.
>
> **When to add an entry:** the second time you reach for the same
> shape, write it down. The third time you reach for it, the entry is
> already in the probe and saves you re-deriving.
>
> **When NOT to add:** project-specific implementation details (those
> belong in the project's own docs), one-off decisions (Decision Log
> is the home), or untested ideas (those start in BACKLOG).

---

## Tier 1 architectural watchdog

**Pattern:** Per-project Python detector that runs on a schedule (launchd), scans for known classes of architectural drift via a mix of static rules (semgrep) and runtime probes, logs findings to an `audit.log`, and sends plain-English Telegram alerts via the shared HQ Telegram pipe. Starts in `--soak` (observe-only) mode for 14 days, then operator manually flips to `--active` after reviewing the soak log for false-positive rate.

**Instances:**
- `~/claude-hq/watchdogs/pats/` (2026-05-07) — 7 rules, 30-min cycle
- `~/claude-hq/watchdogs/paperclip/` (2026-05-08) — 4 rules, 5-min cycle

**Reuse for:** any long-running system that needs known-failure-class detection without disrupting existing alert pipes (databases, services, control-plane software).

**Don't reuse for:** real-time / latency-sensitive systems (use embedded `monitor.py`-style auto-healing instead — see PATS-Copy `monitor.py`).

**Skeleton:** `orchestrator.py` + `lib/{finding.py,alerts.py}` + `rules/{static,runtime}/` + `com.claude-hq.<project>-watchdog.plist`. Mirror the layout from `watchdogs/pats/`.

---

## Plain-English alert / chat / message

**Pattern:** Every user-facing message has three parts in order: emoji headline, what happened in 1-3 plain sentences, what to do (one concrete instruction or "no action needed"). Banned-jargon list enforced at construction time (no `regression`, `baseline`, `threshold`, `7d`, `FP/TP`, etc. unless defined in the same sentence).

**Instances:**
- `~/claude-hq/watchdog/telegram.py` `PlainAlert` dataclass + `STYLE_GUIDE.md` (Lesson 16, 2026-04-24)
- `~/claude-hq/commander/COMMUNICATION.md` (extends to chat replies, 2026-05-08)
- All Tier 1 watchdog `Finding` dataclasses (re-export the same fields)

**Reuse for:** every new outbound notification path (Telegram, email, push, SMS) and every user-facing chat reply.

**Skeleton:** dataclass with `what_happened: str` + `what_to_do: str` + `severity: Literal["info","warn","critical"]`. Linter rejects banned words at construction. Three-part shape enforced in the renderer, not the schema.

---

## Soak before active alerting (14-day observe-only)

**Pattern:** Any new alerting rule starts in soak mode where findings are logged to `audit.log` but NO notifications fire. After 14 days (or earlier if data is convincing), operator reviews the audit log for false-positive rate, then manually flips a `--soak` → `--active` flag in the launchd plist. Reminder fires automatically at the soak-end date via `~/claude-hq/watchdog/reminders.json`.

**Instances:** PATS Tier 1 watchdog (soak 2026-05-07 → 2026-05-22), Paperclip Tier 1 watchdog (soak 2026-05-08 → 2026-05-22).

**Reuse for:** any new alerting rule, regardless of how confident you are that thresholds are right. Soak catches calibration errors before they become alert fatigue.

**Why mandatory:** Lesson 16 (no jargon) + Lesson 20 (pilots need deadline + signal + default action) — soak is the natural deadline + signal vehicle for new alerts.

---

## Read-only sqlite / REST integrity probe

**Pattern:** Standalone Python script that queries a system's state via sqlite (read-only mode) or REST (GET only), checks for known corruption / drift signatures, and exits with structured codes (0 = OK, 2 = corruption, 3 = unreachable). Designed to be called as a guard from hooks before any mutating operation. Never mutates state; never throws.

**Instances:**
- `~/claude-hq/scripts/mempalace-precheck.py` (2026-05-08) — sqlite mode
- `~/claude-hq/watchdogs/paperclip/rules/runtime/server_health.py` — REST mode (probes `/health`)
- `~/claude-hq/scripts/paperclip-burn-tracker.py` (read-only mode) — REST + computation

**Reuse for:** any operation where running a mutating step on corrupt prior state could spread the damage. Catch and abort cheaply rather than fail expensively.

**Skeleton:** `try` open via `sqlite3.connect(...?mode=ro)` (or `urllib.request.urlopen` with timeout) → run a small set of integrity SQL queries (or response-shape checks) → emit `[name] WARN: <msg>` to stderr → `sys.exit(0|2|3)`.

---

## macOS Keychain + launcher script for secrets

**Pattern:** Any service / MCP that needs a secret (API key, token) is launched via a small bash script in `~/claude-hq/scripts/mcp-launchers/`. The script reads the secret from macOS Keychain at spawn time via `security find-generic-password`, exports it to the child process's env, then `exec`s the actual binary. The desktop config (`claude_desktop_config.json`) references the *launcher path*; its `env: {}` block stays empty.

**Instances:** all six launchers in `~/claude-hq/scripts/mcp-launchers/` (paperclip, exa, gemini, github, claude-code-bridge, reddit). Pattern documented in Lessons 14 and 15 (2026-04-22).

**Reuse for:** every new MCP server, every new local service that needs a key. The pattern beats inline-env in the desktop config because (a) Keychain entries are encrypted at rest, (b) the launcher process replaces itself via `exec` so secrets don't persist beyond spawn, (c) the config file is never a leak vector.

**Skeleton:** see any existing launcher (e.g., `paperclip-launcher.sh`). Three lines: read Keychain secret → `export` → `exec` the real command.

---

## PreToolUse + PostToolUse ambient hook pattern

**Pattern:** A hook script that fires automatically on every Claude Code tool call (Bash, Edit, Agent, etc.) without explicit user invocation. The hook is fail-soft: any error logs to stderr but never aborts the tool call. Hook reads context from stdin (JSON), inspects, optionally vetoes the action with non-zero exit code + clear error message, otherwise exits 0 silently.

**Instances:**
- `~/claude-hq/scripts/trust-gate.sh` — PreToolUse Bash matcher, blocks unknown-author code installs
- `~/claude-hq/scripts/model-router.sh` — PreToolUse Agent matcher, applies tier doctrine
- `~/claude-hq/scripts/trust-gate-post.sh` — PostToolUse Bash matcher, scans cloned dirs

**Reuse for:** any safety / governance / routing rule that needs to apply to *every* tool call rather than only when remembered.

**Skeleton:** `set -uo pipefail` (NOT `-e` — fail-soft behaviour matters), parse stdin JSON via Python one-liner, apply check, emit decision via exit code + stderr message. Register in `~/.claude/settings.json` under `hooks.{PreToolUse|PostToolUse}` with the matcher type.

---

## Three-layer behavioural enforcement

**Pattern:** When a behavioural rule needs to survive across sessions and projects, it gets THREE redundant homes:
1. **Doctrine in `commander/`** — the human-readable canonical rule
2. **Memory feedback file in `~/.claude/projects/.../memory/feedback_*.md`** — auto-loaded into every session's system prompt
3. **`commander/COMMANDER.md` Step 1 read-list** — loaded explicitly when HQ activates

This way the rule applies whether the user is in HQ mode (Step 1 reads it), outside HQ (memory file is auto-loaded), or in a fresh session before HQ activates (memory file still loads).

**Instances:**
- COMMUNICATION (CTDD + plain English, 2026-05-08)
- TRUST_GATE (supply-chain protocol, 2026-04-21)
- MODEL_ROUTING (tier doctrine, 2026-05-06)

**Reuse for:** any behavioural rule that should apply universally, not just in one project context.

---

## HQ patches/ directory for non-pushable upstream code

**Pattern:** Code changes made in external repositories where we don't have push access (because the user doesn't have a fork) are exported as `.patch` files via `git diff <base>..<branch>` and stored in `~/claude-hq/patches/<project>-<topic>-<sha>.patch`. The HQ repo IS pushed to GitHub, so the patch is recoverable even if the local Mac is wiped. Filename includes the source-branch SHA so future-self knows which version this snapshot represents.

**Instance:** `~/claude-hq/patches/paperclip-multi-model-routing-8028acf.patch` (2026-05-08, first instance — generalising into a pattern for next time).

**Reuse for:** any time you modify external code without forking. Belt-and-braces backup independent of the upstream repo's availability.

**Skeleton:** `git diff <base>..<branch> > ~/claude-hq/patches/<project>-<topic>-$(git rev-parse --short HEAD).patch`. Add a row to `patches/README.md` describing what the patch does and how to apply it (`git apply` or `git am`).

---

## Healthchecks.io dead-man's switch

**Pattern:** A long-running service emits a fire-and-forget HTTP ping to a Healthchecks.io check URL on every cycle. If the pings stop arriving within the configured grace period, Healthchecks.io itself sends a Telegram alert (the alert is delivered by an external service, so silence in our local code is the alarm — no local trust required for the alarm to fire).

**Instances:**
- PATS-Copy bot status (2026-05-06)
- PATS-Copy `monitor.py` (2026-05-06)
- Paperclip server (2026-05-08)
- Paperclip watchdog (2026-05-08)

**Reuse for:** any process where "process died silently" is a failure mode you want caught externally. Especially valuable for scheduled jobs (cron, launchd) where a missed run is invisible to local observers.

**Skeleton:** create a check in your existing Healthchecks.io account (period + grace tuned to expected cycle), put the ping URL in `~/claude-hq/watchdog/healthchecks-urls.env` (gitignored), call `curl -fsS -m 5 <URL>` at the end of every cycle. Failure to ping is non-blocking — wrap in `|| true`.

---

## Per-project memory mining via mempalace.yaml + session-end auto-mine

**Pattern:** Every project that produces persistent knowledge gets a `mempalace.yaml` at its root defining wing/room structure. The `~/.claude/hooks/session-end.sh` hook automatically runs `mempalace mine "$PROJECT_DIR"` after every session in a git project, gated by precheck + lockfile + nohup so corruption can't recur.

**Instances:** 4 active configs:
- `~/claude-hq/mempalace.yaml`
- `~/projects/paperclip/mempalace.yaml`
- `~/projects/corporate-brains/mempalace.yaml`
- `~/Desktop/POLYMARKET_TRADING_3.0/mempalace.yaml`

**Reuse for:** any new project that should have its content searchable via MemPalace. Run `mempalace init --yes <project-dir>` once to set up the yaml; session-end auto-mine takes over from there.

**Skeleton:** `mempalace init --yes <project-dir>` → confirm wing/rooms in the generated yaml → first session-end mine runs automatically. Subsequent sessions auto-update.
