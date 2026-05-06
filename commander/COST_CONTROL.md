# Cost Control Protocol
## ABSOLUTE — overrides all other concerns except safety

### Hierarchy (every decision follows this order)

**Tier 1: Free first, always.**
- Open-source libraries over paid APIs
- Free tiers of services (Unsplash, Pexels, Gemini free tier)
- Local execution over cloud services
- Existing tools in the stack over new subscriptions
- Community skills over paid plugins
- Self-hosted over SaaS

**Tier 2: One-time cost over recurring.**
- Lifetime licence over monthly plan
- Download a dataset once over paying per-query

**Tier 3: Lowest recurring cost.**
- If recurring is unavoidable, find the cheapest option
- Must not compromise deliverable quality

**Tier 4: User approval gate.**
- ANY expenditure — even $0.01 — requires explicit user approval
- Commander pauses, reports, and WAITS

### Enforcement Protocol

```
BEFORE any agent selects a tool, API, service, or dependency:

1. COST CHECK: Does this cost money?
   ├─ NO → Proceed
   └─ YES → HALT
       ├─ Search for free alternatives (web search, GitHub, HuggingFace)
       ├─ Evaluate: Can a free alternative deliver the same result?
       │   ├─ YES → Use free alternative. Log why in mission board.
       │   └─ NO → COST REPORT to user:
       │       ├─ What costs money and why
       │       ├─ Exact amount (one-time or recurring)
       │       ├─ Free alternatives considered and why they fall short
       │       ├─ Impact of NOT using the paid option
       │       └─ WAIT for explicit user approval
       └─ User responds:
           ├─ APPROVED → Proceed, log approved expenditure
           ├─ REJECTED → Find another way or adjust scope
           └─ "Find cheaper" → Research deeper, report back
```

### Model Routing

**See `MODEL_ROUTING.md` — that is the single source of truth for which tier handles which task shape.**

This file (COST_CONTROL.md) governs *spending policy* (free-first hierarchy, user-approval gates, cost ledger format). Routing rules — task → tier mapping, hard quality floor, user overrides, quota awareness, weekly digest — live in MODEL_ROUTING.md and are enforced by `scripts/model-router.sh`.

The two files share the cost ledger at `run/cost-ledger.sqlite`. Schema is defined in MODEL_ROUTING.md §8.

**One-line summary of routing defaults:** mechanical work → Haiku, standard work → Sonnet, architecture / adversarial / investor / legal / security → Opus (hard floor). Override with `HQ_MODEL_OVERRIDE=…`.

**Image generation** — separate concern from text-model routing. Use Gemini (nano-banana) at ~$0.04/image for UI assets and thumbnails when needed.

### Cost Ledger

The mission board includes a running cost ledger:

```
## Cost Ledger
| Item | Type | Amount | Status | Approved |
|------|------|--------|--------|----------|
| Claude API (Sonnet) | Token usage | ~$0.15 est. | Running | Auto |
| Unsplash API | Free tier | $0 | Active | Auto |
| [any paid item] | [type] | [amount] | PENDING | ⏳ Awaiting |
```

### What This Covers

- API keys with usage costs
- Cloud hosting or deployment
- npm packages with paid tiers
- Model routing decisions
- MCP servers requiring paid accounts
- Any third-party service integration
- Token consumption estimates for large jobs
