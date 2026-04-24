# Watchdog Message Style Guide — HARDWIRED

> **This is not a suggestion. It is enforced by `telegram.py`.**
> Any alert that fails this style guide is blocked at send time.

---

## The Rule

**Every message must be readable by someone who does not know:**
- what a "threshold" is
- what a "rolling baseline" is
- what "regression" means in a statistical sense
- what "standard deviation", "correlation", "percentile" mean
- what "FP/TP" means
- what "7d" or "24h" abbreviations mean

If a reasonably bright friend who doesn't work in software can't understand the message at a glance, it fails.

---

## The Shape of Every Alert

Every alert has exactly three parts, always in this order:

1. **An emoji + one-line headline** — what kind of alert this is, in 8 words or less
2. **What happened** — 1-3 plain sentences describing what's going on in the real world
3. **What to do** — one concrete action, written as a short instruction the user can follow

```
[emoji] [headline]

[what happened, 1-3 plain sentences]

What to do: [one short instruction]
```

---

## Banned Words (the jargon linter rejects these)

```
threshold          baseline          regression      delta
rolling            window            metric          coefficient
stdev              z-score           percentile      quantile
p-value            correlation       variance        anomaly
FP/TP             false positive    true positive   ratio
throughput        latency           concurrency     idempotent
7d    24h    1h    5m    N/A    n=    σ
```

And any ALL-CAPS technical abbreviation that isn't a recognised English word. (HQ, AI, LLM, PR are fine — context makes them clear.)

Replace with:

| Don't say | Say |
|---|---|
| "exceeded threshold" | "higher than usual" |
| "baseline delta of +78%" | "about 78% more than normal" |
| "7-day rolling mean" | "the typical number over the last week" |
| "regression detected" | "something's gotten worse" |
| "anomaly in metric X" | the plain-language name of X with "is behaving oddly" |
| "LESSONS velocity" | "how often Commander has been making mistakes" |
| "subagents per task" | "how many helper agents Commander needed" |

---

## Tone

- **Direct, not alarming.** "Something's off" beats "ALERT: REGRESSION DETECTED".
- **Useful, not chatty.** Skip filler like "I hope this message finds you well."
- **Honest about uncertainty.** "This usually means X or Y" is better than pretending to know.
- **One clear next step.** Never leave the reader wondering what to do.

---

## Template Examples (good)

### Critical — something broke
```
🚨 Something just went wrong

Commander did a thing that normally shouldn't happen: it bypassed the Trust Gate about 2 minutes ago. That's the security layer that checks outside code before letting it in.

What to do: reply "why" and I'll pull up what command was run and why the override was used.
```

### Warn — trending worse
```
🤔 Things are getting slower

Over the last few days, Commander has been taking about 50% longer to finish a typical task. Work is still getting done correctly, just less efficiently.

What to do: reply "show" for a breakdown of which step is dragging.
```

### Info — routine digest
```
☀️ HQ morning check — all good

Yesterday: 2 sessions, no corrections from you, 3 commits landed on claude-hq. Nothing unusual.
```

### Evolution — weekly tune-up proposal
```
🧠 Weekly tune-up

I'd like to make 2 small changes based on what I've seen this week:

A) Stop alerting on long refactor sessions. They naturally use more agents, and I've been crying wolf — 8 false alarms, 1 real one.

B) Add a new signal — whether Commander reads LESSONS.md before starting work. When it does, sessions go smoother.

Reply A, B, AB, or skip.
```

---

## Template Examples (BAD — would be blocked)

```
⚠ WARN: subagents_per_task regression detected.
Baseline delta +78% over 7d rolling window (σ = 0.42).
FP/TP ratio in last 30d: 8/1.
```

Why blocked:
- "WARN" is an abbreviation
- "regression", "baseline", "delta", "rolling window", "σ", "FP/TP" are all jargon
- No plain description of what actually happened
- No "what to do" instruction
- Reader has no idea whether they should care

---

## The Enforcement Pipeline

```
Watchdog computes a metric drift
   ↓
Looks up the metric's `plain_language.alert_template` from metrics.yaml
   ↓
Fills in the variables with plain English (e.g. "78% more" not "+0.78")
   ↓
Builds a PlainAlert(what_happened=..., what_to_do=...)
   ↓
telegram.py runs the jargon linter:
   - Are both fields present?
   - Does either field contain a banned word?
   - Is there a "what to do" with a clear instruction?
   ↓
If any check fails: exception raised, alert NOT sent, error logged
If all pass: sent to Telegram
```

---

## Extending Banned Words

If a technical phrase slips through in a real alert and confused you, add it to the banned list in `telegram.py` (top of file). No code change needed beyond that.

---

*This guide is itself the spec for the jargon linter. When in doubt, read this first.*
