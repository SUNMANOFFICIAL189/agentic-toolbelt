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

### Model Routing (Token Cost)

| Task Type | Model | Approx Cost | Use When |
|-----------|-------|-------------|----------|
| Simple file ops | Haiku | ~$0.001/task | Formatting, renaming, simple tests |
| Standard coding | Sonnet | ~$0.01-0.05/task | Feature implementation, scripts |
| Architecture/planning | Opus | ~$0.10-0.30/task | System design, decomposition |
| Image generation | Gemini (nano-banana) | ~$0.04/image | UI assets, thumbnails |

**Default:** Sonnet for everything. Upgrade to Opus ONLY for planning and architecture. Downgrade to Haiku for mechanical tasks.

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
