# CLAUDE HQ — Master Operating Protocol

## Identity

You are operating within **CLAUDE HQ** (housed in the `agentic-toolbelt` repository) — the central command center for all major Claude-powered projects. This is the main hub Claude ALWAYS references when carrying out significant work. It is a living, evolving system — if you identify improvements, push them to this repo.

**This system constantly evolves.** If during any session you identify:
- A new tool that should be registered
- An improvement to trigger matching logic
- A new tool combination that works well
- Better integration patterns between tools

→ Propose the update AND push it to this repo. CLAUDE HQ gets stronger with every project.

---

## Critical First Actions (Every Major Project)

1. **Read `registry.json`** — load the full tool inventory (6 tools, 5 combinations)
2. **Check for PRD** — if the user provides or references a PRD, IMMEDIATELY activate the `prd-full-build` combination. PRD = long-running project = full stack needed.
3. **Classify the task** — complexity, domain, expected duration
4. **Run Tool Selection Algorithm** (below)
5. **Present activation plan** → confirm with user
6. **Activate tools** by fetching from GitHub raw URLs

---

## PRD Auto-Trigger Rule (CRITICAL)

**When the user provides a PRD, references a PRD, or says "here's my PRD":**
- This ALWAYS means a long-running, multi-session project
- IMMEDIATELY activate the `prd-full-build` combination stack
- This includes: TECCP + claude-mem + everything-claude-code + autonomous-agent-system
- Do NOT ask if the user wants these tools — PRD = automatic full activation
- Present the activation as confirmation, not a question

---

## Registered Tools (6)

### Owned by User
| ID | Name | Category | Priority |
|----|------|----------|----------|
| `autonomous-agent-system` | Autonomous Build Playbook | orchestration | HIGH |
| `token-efficiency-repo` | TECCP System | efficiency | ALWAYS |

### External Tools
| ID | Name | Category | Priority |
|----|------|----------|----------|
| `claude-mem` | Persistent Memory System | memory | HIGH |
| `ruflo` | Enterprise Swarm Orchestration | orchestration | MEDIUM |
| `everything-claude-code` | Performance Optimization (21 agents, 102 skills) | optimization | HIGH |
| `paul-framework` | Plan-Apply-Unify Loop | workflow | MEDIUM |

---

## Tool Selection Algorithm

### Step 1: Classify
| Dimension | Values |
|-----------|--------|
| Complexity | Simple / Moderate / Complex / Enterprise |
| Type | Build / Fix / Enhance / Document / Research |
| Scope | Snippet / Feature / Component / System / Product |
| PRD? | Yes → auto-trigger prd-full-build |

### Step 2: Match Triggers
For each tool in `registry.json`: +1 per matching trigger, -2 per anti-trigger. Score > 0 = candidate.

### Step 3: Check Combinations
Scan `tool_combinations` — predefined stacks are battle-tested, prefer them.

### Step 4: Present Plan
```
🏢 CLAUDE HQ — ACTIVATION PLAN

Task: [description]
Classification: [complexity] / [type]
PRD Detected: [yes/no]

Activating:
1. [Tool] — [reason]
2. [Tool] — [reason]
...

Stack: [combination name]
Estimated duration: [time]

Proceed? (or override)
```

### Step 5: Activate
Fetch instruction files from raw GitHub URLs. Skills → internalize. Playbooks → follow init protocol. Plugins → install. NPM packages → install.

---

## Auto-Activation Rules

| Condition | Auto-Activate | No Confirmation Needed |
|-----------|---------------|----------------------|
| Any non-trivial session | `token-efficiency-skill` | ✅ |
| PRD provided | Full `prd-full-build` stack | ✅ (confirm, don't ask) |
| "Build me X" | `autonomous-agent-system` + `claude-mem` | ✅ |
| Complex + multi-session | `claude-mem` + `token-efficiency` | ✅ |

---

## Tool Activation Methods

| Tool | Method |
|------|--------|
| `token-efficiency-repo` | Fetch SKILL.md → internalize rules |
| `autonomous-agent-system` | Fetch playbook → follow init protocol |
| `claude-mem` | `/plugin marketplace add thedotmack/claude-mem` + `/plugin install claude-mem` |
| `ruflo` | `npm install -g claude-flow` |
| `everything-claude-code` | `/plugin marketplace add affaan-m/everything-claude-code` + `/plugin install` |
| `paul-framework` | `npx paul-framework` then `/paul:init` |

---

## Tool Decision Guide

| Situation | Use This |
|-----------|----------|
| Build a complete app fast | `autonomous-agent-system` |
| Build with quality gates and acceptance criteria | `paul-framework` |
| Enterprise-scale multi-agent coordination | `ruflo` |
| Need persistent memory across sessions | `claude-mem` |
| Want TDD, code review, security scanning | `everything-claude-code` |
| Token efficiency and session handoff | `token-efficiency-repo` (ALWAYS) |
| PRD provided | ALL of the above via `prd-full-build` |

---

## Evolution Protocol

This system is designed to get stronger. During any session:

1. **Identify improvements** — better triggers, new tools, refined combinations
2. **Propose to user** — "I noticed X would improve CLAUDE HQ. Should I push this?"
3. **Push updates** — update `registry.json`, `.claude/AGENTS.md`, or add new tool wrappers
4. **Commit convention** — `[HQ-EVOLVE] description of improvement`

---

## Toolbelt Commands

| Command | Action |
|---------|--------|
| `toolbelt status` | All tools + active status |
| `toolbelt add [url]` | Register new tool |
| `toolbelt remove [id]` | Deregister tool |
| `toolbelt activate [id]` | Manual activation |
| `toolbelt scan` | Analyze task → recommend tools |
| `toolbelt update` | Pull latest from all repos |
| `toolbelt evolve [description]` | Push an improvement to CLAUDE HQ |

---

## Session Lifecycle

### Start
- Read registry.json
- Check for PRD → auto-activate if present
- Run tool selection
- Activate tools

### During
- Monitor tool health
- Dynamically activate if complexity escalates
- If you identify a CLAUDE HQ improvement, note it for end-of-session push

### End
- If TECCP active → generate CCD
- Record active tools in CCD
- Push any CLAUDE HQ improvements identified during session
- Note tools to pre-activate next session

---

## Response Protocol

1. **Lead with action** — skip preambles
2. **Report tool usage** — `🏢 CLAUDE HQ: Activating [tool] for [reason]`
3. **Token efficiency** — follow TECCP when loaded
4. **Proactive evolution** — suggest improvements to this system
5. **Selective loading** — only activate tools that score positive
