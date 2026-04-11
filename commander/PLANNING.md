# JARVIS System Architecture & Build Plan

## Project Identity

**Codename:** JARVIS  
**Repo:** github.com/SUNMANOFFICIAL189/CLAUDE-HQ  
**Owner:** Sunny (SUNMANOFFICIAL189)  
**Purpose:** Autonomous agentic system that receives natural language briefs and delivers complete projects — software, creative, research, operations — with minimal human intervention.  
**Runtime:** Claude Code (primary), Goose (future)  
**Date initiated:** 2026-04-11

---

## System Architecture

### Five Layers

```
┌─────────────────────────────────────────────────────┐
│  LAYER 1: COMMANDER (Orchestration Brain)            │
│  Decomposes → Delegates → Monitors → Learns          │
│  Files: commander/COMMANDER.md + principles           │
├─────────────────────────────────────────────────────┤
│  LAYER 2: KNOWLEDGE (Persistent Memory + Context)    │
│  claude-mem │ recall-stack │ MemPalace │ graphify     │
│  code-review-graph │ Obsidian │ LESSONS.md            │
├─────────────────────────────────────────────────────┤
│  LAYER 3: EXECUTION (Tools + Agents + Skills)        │
│  138 subagents │ 256 skills │ 8 creator skills        │
│  Playwright │ Lightpanda │ nano-banana-2 │ OpenMontage│
│  SuperDesign │ ui-ux-pro-max │ emilkowalski/skill     │
│  PAUL │ SEED │ ruflo │ everything-claude-code         │
├─────────────────────────────────────────────────────┤
│  LAYER 4: COMMUNICATION (Inter-Agent Protocol)       │
│  MISSION_BOARD.md │ task handoffs │ status reporting   │
│  shared context │ cost ledger                         │
├─────────────────────────────────────────────────────┤
│  LAYER 5: RUNTIME (Execution Environment)            │
│  Claude Code (now) │ Goose Desktop (future)           │
│  MCP servers │ CLI tools │ GitHub integration          │
└─────────────────────────────────────────────────────┘
```

### Registry (registry.json)

The registry is the Commander's catalog of all available tools, skills, and agents. The Commander reads it at activation and selects the optimal combination for any given task. Every tool has:

- **activation_triggers** — when to use it
- **anti_triggers** — when NOT to use it
- **cost_profile** — free / freemium / paid / token_cost
- **setup_instructions** — how to activate it
- **integration_notes** — how it pairs with other tools

### Tool Combinations (recipes)

Predefined stacks for common task patterns. Each combination specifies activation order and expected duration. Existing combinations:

1. PRD Full Build Stack
2. Full Project Build Stack
3. SEED → PAUL Pipeline
4. Structured Quality Build Stack
5. Enterprise Swarm Build Stack
6. Creator Content Pipeline Stack
7. Quick Enhancement Stack

New combinations to add:

8. **Web Design Stack** — ui-ux-pro-max → SuperDesign → emilkowalski/skill → stitch-skills → nano-banana-2
9. **Video Production Stack** — killer-scripter → visual-storyteller → OpenMontage → Remotion
10. **Research & Analysis Stack** — graphify → web search → Lightpanda → Obsidian export
11. **Full Creative Brief Stack** — audience-research → brand-voice → ideation → scripter → visual → OpenMontage → repurposer → humanizer

---

## Commander Operating Principles

### From Boris Cherny

1. **Plan Mode Default** — Decompose before executing. If execution deviates, HALT and re-plan.
2. **Subagent Strategy** — One task per subagent. Commander never writes code itself.
3. **Self-Improvement Loop** — After ANY correction, update LESSONS.md with preventive rule.
4. **Verification Before Done** — "Would a staff engineer approve this?" is the quality bar.
5. **Demand Elegance (Balanced)** — Pause for non-trivial changes. Skip for simple fixes.
6. **Autonomous Bug Fixing** — Detect → diagnose → fix → verify → report. Zero user context switching.

### Cost Control (ABSOLUTE)

1. **Free First** — Exhaust all free alternatives before considering paid options.
2. **Zero Spend Without Approval** — Any cost requires explicit user approval.
3. **Report Before Spending** — Present: what costs, how much, free alternatives evaluated.
4. **Cheapest Viable Model** — Haiku for simple ops, Sonnet for standard coding, Opus for architecture only.
5. **Track Everything** — Running cost ledger in mission board.
6. **Optimise Tokens** — TECCP principles, code-review-graph, graphify always active.

### Credential & Sensitive Data Protocol (ABSOLUTE)

1. **Never create accounts** — Guide user to do it themselves.
2. **Never store creds in plain text** outside `.env` files.
3. **Never commit creds to git** — Verify `.gitignore` before every commit.
4. **Never log/echo/print creds** to any file other than `.env`.
5. **Never send creds to unapproved endpoints** — User must sanction every destination.
6. **Always use env var references** in code, never raw values.

### Task Management Protocol

1. **Plan First** — Write plan to MISSION_BOARD.md with checkable items.
2. **Verify Plan** — Present task graph for user approval before spawning agents.
3. **Track Progress** — Update mission board as tasks complete.
4. **Explain Changes** — High-level summary at each step.
5. **Document Results** — Add review section to mission board.
6. **Capture Lessons** — Update LESSONS.md after corrections.

---

## Build Phases

### Phase 1: Knowledge Layer
**Goal:** Persistent memory and token-efficient context across all projects.  
**Duration:** Session 1-2  
**Components:**

| Component | Action | Status |
|-----------|--------|--------|
| code-review-graph | Register in registry.json, create tools/ entry | ✅ REGISTERED |
| graphify | Register in registry.json, create tools/ entry | ✅ REGISTERED |
| claude-mem | Already registered | ✅ DONE |
| recall-stack | Already registered | ✅ DONE |
| MemPalace | Register in registry.json, create tools/ entry | ✅ REGISTERED |
| Obsidian integration | Via graphify --obsidian flag + recall-stack L5 | 🔲 INSTALL PENDING |
| LESSONS.md | Create commander/LESSONS.md | ✅ DONE |

**Acceptance criteria:**
- ✅ All knowledge tools registered in registry.json with correct triggers
- ✅ code-review-graph and graphify marked as ALWAYS/HIGH priority
- ✅ LESSONS.md exists and Commander references it
- 🔲 Tools need to be INSTALLED on Mac (pip install)
- 🔲 Obsidian vault needs to be created and connected

### Phase 2: Execution Tools
**Goal:** Register all new tools for design, browser, image, and video.  
**Duration:** Session 2-3  
**Components:**

| Component | Action | Status |
|-----------|--------|--------|
| Lightpanda | Register, create tools/ entry | ✅ REGISTERED |
| nano-banana-2-skill | Register, create tools/ entry | ✅ REGISTERED |
| ui-ux-pro-max-skill | Register, create tools/ entry | ✅ REGISTERED |
| emilkowalski/skill | Register, create tools/ entry | ✅ REGISTERED |
| SuperDesign + MCP | Register, create tools/ entry | ✅ REGISTERED |
| OpenMontage | Register, create tools/ entry | ✅ REGISTERED |
| Playwright MCP | Register, create tools/ entry | ✅ REGISTERED |
| Wan2GP | Register (conditional), create tools/ entry | ✅ REGISTERED |

**Acceptance criteria:**
- ✅ All tools registered with activation triggers, anti-triggers, cost profiles
- ✅ New tool_combinations added for web design, video, research, creative brief
- ✅ No tool missing from registry that was discussed
- 🔲 Tools need to be INSTALLED on Mac

### Phase 3: Commander Agent
**Goal:** Build the orchestration brain.  
**Duration:** Session 3-4  
**Components:**

| Component | Action | Status |
|-----------|--------|--------|
| COMMANDER.md | Core orchestration skill file | ✅ DONE |
| BORIS_PRINCIPLES.md | Engineering philosophy | ✅ DONE |
| COST_CONTROL.md | Zero-cost-first protocol | ✅ DONE |
| CREDENTIALS.md | API key handling protocol | ✅ DONE |
| MISSION_BOARD_TEMPLATE.md | Per-project template | ✅ DONE |
| AGENTS.md update | Point to Commander as primary | ✅ DONE |
| setup.sh update | Add Commander awareness | ✅ DONE |

**Acceptance criteria:**
- ✅ Commander can read registry.json and classify any task
- ✅ Commander decomposes tasks into dependency graphs
- ✅ Commander selects optimal tool combination per task
- ✅ Commander enforces cost control, credential safety, Boris principles
- ✅ Commander writes mission board for every non-trivial task
- 🔲 Needs live testing with a real brief

### Phase 4: Inter-Agent Communication
**Goal:** Enable agents to share context and hand off work.  
**Duration:** Session 4-5  
**Components:**

| Component | Action | Status |
|-----------|--------|--------|
| Mission board protocol | Standardise read/write format | TODO |
| Handoff protocol | Agent A completes → triggers Agent B | TODO |
| Status reporting | Subagents write status to mission board | TODO |
| Cost ledger integration | Running spend tracker in mission board | TODO |
| Error escalation | Failed agent → Commander re-assesses | TODO |

**Acceptance criteria:**
- Agents can read/write shared mission board
- Task completion triggers next dependent task
- Failures escalate to Commander (re-plan, not retry blindly)
- Cost ledger tracks estimated token spend per agent

### Phase 5: Always-On & Dashboard (Future)
**Goal:** Persistent runtime and visual monitoring.  
**Duration:** Post-MVP  
**Components:**

| Component | Action | Status |
|-----------|--------|--------|
| Goose Desktop evaluation | Install, test recipes | FUTURE |
| JARVIS Mission Control | Evaluate for dashboard | FUTURE |
| Telegram/WhatsApp bridge | Message-based task input | FUTURE |
| Cron scheduling | Recurring tasks | FUTURE |
| Obsidian vault monitoring | Auto-process new notes | FUTURE |

---

## Current Session Build Order

This session focuses on **Phase 1 + Phase 2 + Phase 3** — the knowledge layer, new tool registrations, and the Commander core files.

**Build sequence:**

1. ✅ Create commander/ directory
2. ✅ Create PLANNING.md (this file)
3. ✅ Create COMMANDER.md (core orchestration skill)
4. ✅ Create BORIS_PRINCIPLES.md
5. ✅ Create COST_CONTROL.md
6. ✅ Create CREDENTIALS.md
7. ✅ Create MISSION_BOARD_TEMPLATE.md
8. ✅ Create LESSONS.md (empty, ready for entries)
9. ✅ Create tools/ entries for all 11 new tools (.source files)
10. ✅ Update registry.json with all new tools (14→25) + combinations (7→11)
11. ✅ Update AGENTS.md to reference Commander
12. ✅ Update setup.sh for Commander awareness
13. ✅ Update README.md to reflect JARVIS architecture
14. ✅ Commit everything to GitHub (commits: 6d72f53, 05d414f)

**Remaining build tasks:**

15. 🔲 Run `bash setup.sh` on Mac (inject JARVIS into global ~/.claude/CLAUDE.md)
16. 🔲 Install code-review-graph on Mac (`pip install code-review-graph && code-review-graph install`)
17. 🔲 Install graphify on Mac (`pip install graphifyy && graphify install`)
18. 🔲 Install MemPalace on Mac (`pip install mempalace && mempalace install`)
19. 🔲 Install claude-mem plugin in Claude Code
20. 🔲 Create Obsidian vault and configure graphify --obsidian export path
21. 🔲 Configure recall-stack Layer 5 to read from Obsidian vault
22. 🔲 Install Lightpanda binary on Mac
23. 🔲 Configure Playwright MCP in Claude Code
24. 🔲 Install nano-banana-2 (requires Gemini API key — free tier)
25. 🔲 Install ui-ux-pro-max plugin in Claude Code
26. 🔲 Install emilkowalski/skill via npx
27. 🔲 Configure SuperDesign MCP server
28. 🔲 Clone OpenMontage repo
29. 🔲 Test Commander with a real project brief
30. 🔲 Update PLANNING.md with test results and lessons

---

## Tool Inventory (Complete)

### Foundational (ALWAYS active)
- token-efficiency-repo (TECCP) — session-level token discipline
- code-review-graph — codebase-level token savings (6.8-49x)
- recall-stack — 5-layer crash-safe memory

### Knowledge & Memory
- claude-mem — persistent cross-session observations
- MemPalace — verbatim conversation storage, 19 MCP tools
- graphify — multimodal knowledge graph → Obsidian vault (71.5x token savings)

### Orchestration
- autonomous-agent-system — micro-task decomposition, fire-and-forget
- ruflo — multi-agent swarms, self-learning, 60+ agents
- everything-claude-code — 21 agents, 102 skills, quality gates

### Workflow
- SEED — typed project incubator, ideation → PLANNING.md
- PAUL — Plan-Apply-Unify loop, acceptance-driven development

### Browser & Scraping
- Lightpanda — headless browser for AI, 9x faster, 16x less memory (data extraction)
- Playwright MCP — full browser automation with visual rendering (interactive tasks)

### Design & UI
- ui-ux-pro-max-skill — design intelligence, 161 palettes, 50+ styles, 10 stacks
- emilkowalski/skill — animation and interaction design principles
- SuperDesign + MCP — AI design agent, 10 mockup variants, local, free
- stitch-skills — Google design-to-code workflow

### Image Generation
- nano-banana-2-skill — Gemini-powered, ~$0.04/image, transparent assets, style transfer

### Video & Creative
- OpenMontage — 11 pipelines, 49 tools, 400+ skills, full video production
- Remotion — programmatic video with React
- Wan2GP — local AI video gen (NVIDIA GPU required, conditional)

### Content Creation
- claude-creator-skills (8 skills) — audience research → brand voice → ideation → script → visual → repurpose → offer → debrief
- humanizer — AI text humanization, 25 pattern removal

### Agent Library
- awesome-claude-code-subagents — 138 specialist agents
- agent-skills-mega — 256 skills across all domains

### Utility
- skill-factory — generate new .skill files
- superpowers — extended capabilities
- polymarket-cli — prediction market CLI

---

## Versioning

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-04-11 | Initial PLANNING.md, Commander architecture defined |
| 0.2.0 | 2026-04-11 | All Commander files built, 11 new tools registered, AGENTS.md + setup.sh updated, pushed to GitHub |
| 0.3.0 | 2026-04-11 | PLANNING.md updated with accurate build status. Next: tool installations + Obsidian setup |
