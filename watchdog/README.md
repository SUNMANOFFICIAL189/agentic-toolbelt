# HQ Watchdog

A quality-monitoring sidecar for Claude HQ & Commander.

It watches how well HQ is working, notices when things get worse, and tells you on Telegram — in plain English, always.

---

## What it actually does

1. **Reads local data only.** Your session logs, git commits on `claude-hq`, LESSONS.md updates, Trust Gate log. Nothing leaves your machine except the short Telegram alert.
2. **Compares now against your recent normal.** If this week is noticeably worse than the last 7-day rolling average, it flags it.
3. **Messages you on Telegram.** Every alert explains *what happened*, *why it matters*, and *what to do*. No jargon, ever (enforced by code — see [STYLE_GUIDE.md](STYLE_GUIDE.md)).
4. **Evolves itself safely.** Weekly, it sends a "here's what I'd like to tweak" digest. You approve with one letter. No self-silencing, no autonomous threshold changes on the metrics that matter.

---

## Setup (one-time, ~5 minutes)

### Step 1 — Create a dedicated Telegram bot for HQ

This keeps HQ alerts separate from your Polymarket alerts so you always know at a glance which system is talking.

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Name it something like `HQ Watchdog` (display name) and `hq_watchdog_bot` (username — must end in `bot` and be unique)
4. BotFather replies with a **token** that looks like `1234567890:ABCdefGhIjKlmNoPqRsTuVwXyZ`
5. Copy that token somewhere safe for a moment

### Step 2 — Get your chat ID

1. Search your new bot in Telegram, tap Start, send it any message (e.g. "hi")
2. Open this URL in a browser, replacing `<TOKEN>` with your bot token:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Find `"chat":{"id": <number> ...` — that number is your chat ID

### Step 3 — Store the credentials securely

Run this (one line, one time — fills macOS Keychain, following the HQ Keychain pattern from Rule 15):

```bash
security add-generic-password -U -a "$USER" -s "claude-hq-watchdog-token" -w "<TOKEN>"
security add-generic-password -U -a "$USER" -s "claude-hq-watchdog-chat-id" -w "<CHAT_ID>"
```

Then copy the example env file:

```bash
cp ~/claude-hq/watchdog/.env.example ~/claude-hq/watchdog/.env
```

The watchdog reads from Keychain at runtime — nothing sensitive ever touches disk in plain text.

### Step 4 — Test the pipe

```bash
python3 ~/claude-hq/watchdog/telegram.py --self-test
```

You should receive a Telegram message that says something like:

> ✅ HQ Watchdog is connected
>
> Good news — the alert pipe is working. You'll start getting daily quality digests at 08:00 once the baseline week is complete.
>
> Nothing to do right now.

If you don't receive it, the script prints what went wrong (wrong token, wrong chat ID, network issue).

### Step 5 — Enable the hooks

```bash
bash ~/claude-hq/watchdog/install-hooks.sh
```

Installs the post-commit hook on `claude-hq` and registers the session-end hook. You can uninstall with `bash install-hooks.sh --uninstall` — takes 1 second, leaves nothing behind.

---

## What you'll see day to day

### Normal day
One quiet Telegram message at **08:00**:

> ☀️ HQ morning check — all good
>
> Yesterday: 2 sessions, 0 corrections, 3 commits on claude-hq. Nothing unusual.

### Something's off
An immediate or hourly message, depending on severity:

> 🤔 Something's off
>
> Over the last few sessions, Commander has been pulling in almost twice as many helper agents as usual to get work done. This usually means either a recent change made it less efficient, or your recent tasks were genuinely harder.
>
> **What to do:** reply **"look"** and I'll check the last 3 sessions and tell you which it is.

### Weekly self-improvement digest (Sundays 08:00)
Short proposals, approve with one letter:

> 🧠 Weekly tune-up
>
> I'd like to make 2 changes based on what I've seen this week:
>
> A) Quieter alerts for refactor sessions — they naturally use more agents, and I've been crying wolf.
>
> B) Add a new signal — how often Commander reads LESSONS.md before starting work. I've noticed this predicts whether a session goes smoothly.
>
> Reply **A**, **B**, **AB**, or **skip**.

---

## How it stays honest

Three things the watchdog is **not allowed to do**, even if it "learns" they'd help:

1. **Silence its own critical alerts.** If LESSONS.md velocity spikes, no amount of "learning" can suppress that signal. You always hear about mistake bursts.
2. **Raise thresholds on core safety metrics.** Trust Gate overrides, git reverts, and correction spikes have fixed alarms.
3. **Modify its own code.** Only `metrics.yaml`, `baseline.json`, `history.db`, and `LEARNINGS.md` are live data. Python code stays frozen unless you change it.

See [LEARNINGS.md](LEARNINGS.md) for the full log of what the watchdog has learned and changed.

---

## Uninstall

If you want to remove the watchdog completely:

```bash
bash ~/claude-hq/watchdog/install-hooks.sh --uninstall
rm -rf ~/claude-hq/watchdog/
git checkout main && git branch -D watchdog-v1
```

Takes under a minute. Nothing else on your system is affected.

---

## File map

| File | What it is |
|---|---|
| `STYLE_GUIDE.md` | The hardwired rules for how Telegram messages must be written |
| `metrics.yaml` | The list of things being watched (editable, plain descriptions required) |
| `watchdog.py` | The scoring engine |
| `telegram.py` | The message sender + jargon linter |
| `evolve.py` | The weekly self-improvement proposer |
| `hooks/post-commit` | Triggers a score run after every commit to claude-hq |
| `hooks/session-end.sh` | Captures per-session numbers |
| `history.db` | SQLite — all historical sessions, commits, and scores (gitignored) |
| `LEARNINGS.md` | What the watchdog has learned and what it's changed |
| `.env.example` | Template for local config (real `.env` gitignored) |

---

*Built on the `watchdog-v1` branch. See `commander/LESSONS.md` Rule 16 for the plain-English communication rule that this system enforces.*
