# Model Routing Doctrine

> **Authoritative source for all model-selection decisions inside HQ.**
> The Commander reads this at activation (Step 1, after `LESSONS.md`).
> The PreToolUse routing hook (`scripts/model-router.sh`) enforces it on every `Agent` dispatch.
>
> Companion docs:
> - `commander/COST_CONTROL.md` — spending policy (free-first hierarchy, approval gates).
> - `commander/LESSONS.md` rule 16 — plain-English alerts (applies to quota / cost notifications).
> - `commander/INCIDENT_LEDGER.md` — vendor cooling-off (overrides any provider in this doctrine).

---

## 1. Purpose

When a non-trivial task lands in HQ, every sub-step has a cheapest model that can do the work to quality. Without enforcement, the orchestrator forgets and runs everything on whatever model the active session is on. **This doctrine plus the routing hook make the cheap-default automatic.**

Out of scope: this doctrine does not control which *provider* is called by tools that bring their own clients (Bash → curl → Anthropic API, MCP launchers, plugin internals like `claude-mem`). Those are governed by their own configs. Routing here applies to:

- The `Agent` tool's subagent dispatches (Phase 1, native).
- Future cross-provider routing through a localhost gateway (Phase 2).

---

## 2. Concepts

| Term | Meaning |
|---|---|
| **Tier** | Within-Anthropic class: Haiku → Sonnet → Opus. Cheapest first. |
| **Provider** | Anthropic, Google (Gemini), Groq, Cerebras, OpenRouter, etc. |
| **Hard floor** | Agent kinds that refuse to route below Opus regardless of cost. |
| **Override** | Env-var or explicit `model:` param that bypasses the doctrine. |
| **Quota window** | Anthropic's rolling 5-hour Max-plan budget. |
| **Quality gate** | Sample-and-grade check on cheap-tier output before promoting it. (Phase 3, not yet active.) |
| **Cost ledger** | Local SQLite (`run/cost-ledger.sqlite`) recording every routing decision + observed cost. |

---

## 3. Decision algorithm

```
1. HQ_ROUTER_OFF=1                  → pass-through, no routing applied
2. Pick a candidate tier (first wins):
     a. HQ_MODEL_OVERRIDE=<tier>    → that tier
     b. Dispatch's model:<x>        → caller's choice
     c. Doctrine keyword match      → tier from §5 table
     d. Default                     → sonnet
3. HARD FLOOR GUARD (§4):
     If subagent_type matches the hard-floor list → force opus
     (overrides any choice in step 2 except HQ_ROUTER_OFF=1)
4. HQ_MODEL_FLOOR=<tier>            → never go below this tier
5. Quota-aware degradation (§7)     → may downgrade by one tier,
                                       skips hard-floor agents
6. Log decision to cost ledger (§8)
```

**Why the hard floor beats env override:** if a user types `HQ_MODEL_OVERRIDE=haiku` and *then* dispatches a red-team review, they almost certainly didn't mean to apply Haiku to red-teaming — they meant "use cheap models for routine work." The hard floor is the safety net against that footgun. Anyone who genuinely wants haiku-everywhere can set `HQ_ROUTER_OFF=1`.

The hook **does not** block the dispatch on errors — if any rule throws, it logs and falls through to the default. Routing must never break Claude Code; degraded mode is the failure shape.

---

## 4. Hard quality floor

Agents in this list **refuse all downgrades**. Even quota-aware degradation skips them.

| Agent kind / pattern | Reason |
|---|---|
| `red-team`, `*-reviewer` (security/code/cpp/python/go/etc.) | Adversarial reasoning is where Opus earns its cost. Cheap tiers miss non-obvious failure modes. |
| `investor-comms`, `investor-materials`, `investor-outreach` | Investor-facing copy must be tight. Quality regression is unrecoverable post-send. |
| `legal-review` | Liability surface. |
| `security-review` (matches existing skill) | Same as red-team. |
| `architect`, `code-architect`, anything with `architect` in the kind | Architecture decisions cascade — re-doing them after the fact is expensive. |

The hook checks `subagent_type` against this list (case-insensitive substring match). If matched, model = `opus` regardless of any other rule except `HQ_ROUTER_OFF=1`.

---

## 5. Doctrine table — task shape → tier

Match by keyword/intent in the dispatch's task description (the `prompt` argument to the `Agent` tool). The hook does case-insensitive substring matching against these lemmas.

| Task shape | Keywords | Tier | Why |
|---|---|---|---|
| Mechanical file ops | rename, format, lint, prettier, normalise | **Haiku** | Pure mechanical — no reasoning. |
| Per-page summarisation | summarise, extract, condense, tldr | **Haiku** | Below Sonnet's threshold. |
| Bulk classification | classify, categorise, tag, label | **Haiku** | High-volume, low-judgement. |
| Standard implementation | implement, build, add feature, fix bug | **Sonnet** | Default for code work. |
| Code review (non-adversarial) | review, audit (general), simplify | **Sonnet** | Adversarial reviews → hard floor. |
| Multi-source synthesis | synthesise, compile findings, merge | **Sonnet** | Synthesis sweet spot. |
| Test writing | write tests, tdd, coverage | **Sonnet** | Default. |
| Refactor proposals | refactor, restructure, decompose | **Sonnet** | |
| Architecture / system design | architect, design, blueprint, plan system | **Opus** | Hard floor (§4 also catches this). |
| Adversarial / red-team | red-team, adversarial, threat-model, contradict | **Opus** | Hard floor. |
| Long-context analysis (>150K tokens) | (caller tags `long-context`) | **Opus** (1M context) | Sonnet/Haiku cap at 200K. |
| Investor comms / materials | pitch, deck, memo, investor, fundraise | **Opus** | Hard floor. |
| Legal / compliance | legal, compliance, regulatory, license | **Opus** | Hard floor. |

If multiple keywords match, the tier with the highest priority (Opus > Sonnet > Haiku) wins. **Do not "sum" matches** — a single Opus keyword forces Opus.

---

## 6. User overrides

All overrides are env-var driven. Set in shell or via `~/.zshrc`. The hook reads them at fire time.

| Variable | Effect | Use when |
|---|---|---|
| `HQ_ROUTER_OFF=1` | Disable routing entirely. Hook becomes a no-op. | Debugging the router; need raw Claude Code behaviour. |
| `HQ_MODEL_OVERRIDE=opus\|sonnet\|haiku` | Force one tier for the whole session. | "Use Opus for everything tonight." |
| `HQ_MODEL_FLOOR=sonnet` | Never go below this tier (overrides downgrades). | High-stakes session where you don't want any Haiku. |
| `HQ_QUOTA_AWARENESS=off` | Disable the §7 quota-aware degradation. | When you've already accepted the quota burn and don't want surprise downgrades. |

**Transparency:** at session start, the SessionStart hook prints a one-line banner:

```
Routing: ON  |  Override: HQ_MODEL_OVERRIDE=<unset>  |  Quota awareness: ON
```

so it's never ambiguous what the routing layer is doing.

---

## 7. Quota awareness (Phase 4 — defined here, activated when scaffolded)

**Trigger condition:** Anthropic Max 5-hour rolling window > 80% consumed.

**Source of truth:** TBD by Phase 4 implementation. Candidates:
- `claude usage` CLI subcommand (if exposed)
- Read from Claude Code's local usage telemetry
- Periodic API ping with token counting

**Action when triggered:**

| Current chosen tier | Degraded tier | Notes |
|---|---|---|
| Opus | Sonnet | Unless on hard floor (§4) → no change |
| Sonnet | Haiku | |
| Haiku | Haiku | Already lowest |

**Alert:** PlainAlert via Telegram per Lesson 16. Banned-word list applies. Template:

```
🌡️ Heads up — running closer to the Anthropic limit

Used about 80% of the 5-hour budget. Until it resets in about an hour, I'm going to use a smaller model for routine work to leave headroom for important stuff.

What to do: nothing needed. If you'd rather I keep using the bigger model, reply "keep big".
```

If user replies "keep big" → hook sets `HQ_QUOTA_AWARENESS=off` for the session.

---

## 8. Cost ledger

**Location:** `~/claude-hq/run/cost-ledger.sqlite` (gitignored — local only).

**Schema (v1):**

```sql
CREATE TABLE IF NOT EXISTS routing_decisions (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ts              TEXT    NOT NULL,                 -- ISO 8601 UTC
  session_id      TEXT,
  project         TEXT,                             -- cwd basename
  agent_kind      TEXT,                             -- subagent_type or 'main'
  task_summary    TEXT,                             -- first 120 chars of prompt
  model_requested TEXT,                             -- caller-supplied, NULL if none
  model_chosen    TEXT    NOT NULL,                 -- final tier used
  override_reason TEXT,                             -- env_override | hard_floor |
                                                    -- doctrine_match | frontmatter |
                                                    -- default | quota_degraded
  matched_keyword TEXT,                             -- which doctrine rule fired
  -- Filled post-completion (best-effort; nullable)
  input_tokens    INTEGER,
  output_tokens   INTEGER,
  cost_usd        REAL,
  duration_ms     INTEGER,
  status          TEXT                              -- queued | completed | failed |
                                                    -- fallback | rate_limited
);
CREATE INDEX IF NOT EXISTS idx_ts      ON routing_decisions(ts);
CREATE INDEX IF NOT EXISTS idx_session ON routing_decisions(session_id);
CREATE INDEX IF NOT EXISTS idx_project ON routing_decisions(project);
```

**On-demand reporting:** `/cost-report` slash command (TBD: project skill in `~/claude-hq/.claude/commands/`) prints last 24h / 7d aggregates per project, per tier, per agent kind.

**Weekly Telegram digest:**
- Cron / launchd: Sunday 09:00 local.
- Reads last 7d of routing_decisions.
- Generates a PlainAlert (Lesson 16 compliant). Banned-word linter checked.
- Template:

```
📊 Weekly routing report

Last 7 days: about [N] agent dispatches, costing roughly $[X.XX].
Most expensive day: [day] (about $[Y.YY]). Most common task: [shape].

Anything unusual: [auto-flagged outliers, plain English]
[OR] Nothing unusual to flag.

What to do: reply "details" for a per-project breakdown, or "reset" if you want me to reconsider any tier mappings.
```

If the digest detects a likely problem (e.g. one project's spend grew 3× week-on-week), it surfaces that as the "anything unusual" line. The bar for flagging: only if the change is large enough to matter to a human reading half-attentively.

---

## 9. Quality gate (Phase 3 — defined here, not yet active)

**Goal:** catch silent quality regression when cheap-tier outputs feed into expensive synthesis.

**Mechanism:**
- 10% sampling rate on Haiku and Sonnet outputs (excluding hard floor).
- Sampled outputs get re-graded by next tier up.
- Disagreement → escalate the *whole batch* to higher tier; log to ledger as `quality_escalated`.
- Persistent disagreement on a doctrine row (>30% disagree over 50 samples) → surface as a doctrine-revision suggestion in the weekly digest.

Not active in Phase 1. Add when we have 30 days of cost-ledger data showing it's worth the overhead.

---

## 10. Failure handling

| Failure | Response | Logged status |
|---|---|---|
| Network 5xx, transient timeout | Retry once with 2s backoff. If still fails → fallback one tier up. | `fallback` |
| 429 rate limit | Fallback one tier up immediately. No retry. | `rate_limited` |
| 401 auth error | **HALT.** Send Telegram alert. Do NOT fallback (key may be revoked / leaked — never fanout to other providers). | `failed` |
| Quality gate fail (Phase 3) | Escalate one tier up. | `quality_escalated` |
| Provider unreachable (DNS / connection refused) | Fallback to next provider in chain (Phase 2). | `fallback` |

**Why no fallback on 401:** a 401 might mean credential leak in progress. The right response is to tell a human, not to try every other provider with the same broken assumption. Lesson 14 spirit.

---

## 11. Context-length safety

| Tier | Context window | When to force |
|---|---|---|
| Haiku 4.5 | 200K | Default for short tasks |
| Sonnet 4.6 | 200K | Default for medium |
| Opus 4.7 | 1M | Tasks tagged `long-context`, OR observed input > 150K tokens |
| Opus 4.6 (Fast) | 200K | Avoid for long-context |
| Gemini 2.5 Pro (Phase 2) | 1M | Cross-provider option for huge input |

The hook **cannot** reliably measure input size pre-dispatch (the prompt is the dispatch's `prompt` arg, not the actual context the subagent will pull in). Pragmatic rule: callers tag `long-context` in the task description (e.g. "long-context: review the full repo's …") and the hook routes accordingly.

If a routed model returns a context-overflow error mid-execution, treat as `failed` per §10 — alert, do not fallback (would re-incur the cost on the other tier).

---

## 12. Provenance and transparency

Every dispatch landing in the cost ledger is queryable by:
- Session ID
- Project
- Agent kind
- Time window
- Model chosen
- Override reason

Final reports compiled by HQ (e.g. investor briefs, research syntheses) should include a short provenance footer:

```
Generated by HQ on [date].
Routing summary: [N] agent calls. Per-page summarisation: Haiku.
Synthesis: Sonnet. Adversarial pass: Opus. Total spend: $[X.XX].
```

This is generated automatically from cost-ledger queries by the `/cost-report --provenance` flag.

---

## 13. Trust Gate intersection (Phase 2 reminder)

When Phase 2 (cross-provider gateway) is built, every new provider added to the routing chain must pass through the Trust Gate. Specifically:

- LiteLLM (BerriAI) — not currently allowlisted; install via Docker only, pin SHA. See `LESSONS.md` rule 1.
- Cooling-off check (`INCIDENT_LEDGER.md`) runs before any provider gets added to the active chain.
- New provider keys go to Keychain via the existing launcher pattern (`LESSONS.md` rules 14–15).

The router never bypasses Trust Gate. If a provider's allowlist status changes (incident → cooling-off), routing automatically removes it from the chain at next session start. Implementation: chain is built fresh from `INCIDENT_LEDGER.md` minus cooling-off entries.

---

## 14. What this file is NOT

- **Not the full pricing reference.** Model token costs change. See provider docs at evaluation time. The doctrine reasons about *relative* cost (Haiku ≪ Sonnet ≪ Opus), not absolute prices.
- **Not the implementation.** The hook lives at `scripts/model-router.sh`. Doctrine drives behaviour; hook enforces it. Updating doctrine requires re-reading the hook to confirm enforcement still aligns.
- **Not a replacement for human judgement.** The Commander can override at any time by passing explicit `model:` to the Agent tool. The hook respects that.
- **Not retroactive.** Routing changes apply forward-only. Past observations in the ledger reflect past doctrine.

---

## 15. Revision triggers

Update this file when:

- A new tier becomes available (e.g. a new Anthropic tier between Sonnet and Opus).
- A new provider gets added to Phase 2 chain.
- The cost ledger reveals a doctrine row is consistently mis-routing (quality gate persistent disagreement, or human override frequency on a specific keyword).
- A new agent kind is added to the hard floor (or removed — rare).
- Lesson 16 banned-word list extends in a way that affects digest templates.

Commit messages: `docs(routing): <what changed and why>`.

---

*Doctrine v1 — drafted 2026-05-06 alongside Phase 0 of the multi-model routing build.
Next reviewer: read §3 (decision algorithm) first, then §5 (doctrine table). The rest is reference.*
