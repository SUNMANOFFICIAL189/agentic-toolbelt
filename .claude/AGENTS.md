# CLAUDE HQ — JARVIS Operating Protocol for Claude Code

## CRITICAL: The Commander

You are running the JARVIS system. Your first action on ANY non-trivial task is to load the Commander:

```
cat ~/claude-hq/commander/COMMANDER.md
```

The Commander is your orchestration brain. It tells you HOW to decompose tasks, WHICH tools to select, WHEN to spawn subagents, and HOW to enforce quality and cost control. Read it before doing anything complex.

### On Session Start — DO THIS AUTOMATICALLY:

1. Read `commander/LESSONS.md` (mistakes to avoid)
2. Read `registry.json` from THIS directory (`cat registry.json`)
3. Analyze the user's first message to classify the task
4. If non-trivial: load `commander/COMMANDER.md` and follow its activation protocol
5. If simple: handle directly, no Commander overhead needed

### Quick Reference — Commander Files

| File | Read When |
|------|-----------|
| `commander/COMMANDER.md` | Any non-trivial task (main orchestration logic) |
| `commander/BORIS_PRINCIPLES.md` | Any coding or building task (engineering philosophy) |
| `commander/COST_CONTROL.md` | Anything involving APIs, services, or model routing |
| `commander/CREDENTIALS.md` | Anything involving API keys or sensitive data |
| `commander/MISSION_BOARD_TEMPLATE.md` | Starting any multi-step project |
| `commander/LESSONS.md` | EVERY session start (past mistakes to avoid) |
| `commander/PLANNING.md` | Understanding the full system architecture |

---

## How This System Works in Claude Code

You have terminal access. You do NOT "fetch URLs" — you execute bash commands. When this file says to activate a tool, that means **run the setup command in the terminal**.

### The Core Principles:

1. **Commander First** — For any non-trivial task, load COMMANDER.md and follow its 7-step protocol
2. **YOU take the initiative** — Read the registry, decide which tools match, install them, report what you did
3. **Zero Cost First** — Always find free alternatives before suggesting paid options (see COST_CONTROL.md)
4. **Plan Before Execute** — Write a mission board before spawning agents (see MISSION_BOARD_TEMPLATE.md)
5. **Staff Engineer Bar** — "Would a staff engineer approve this?" is the quality gate
6. **Never Expose Credentials** — Follow CREDENTIALS.md for all API key handling
7. **Learn From Mistakes** — After any correction, update LESSONS.md

---

## Tool Activation — Actual Commands to Run

When activating a tool, run its setup command in the terminal:

### For GitHub repos (clone into ~/claude-hq/repos/):
```bash
git clone [source_url] ~/claude-hq/repos/[tool-id]
```

### For npm packages:
```bash
npm install -g [package-name]
```

### For pip packages:
```bash
pip install [package-name]
```

### For Claude Code plugins:
```bash
/plugin marketplace add [owner/repo]
/plugin install [plugin-name]
```

### For MCP servers:
```bash
claude mcp add [name] -- [command]
```

### For skill files (.md or .skill):
Read the file content and internalize as operating behavior for this session.

---

## Task Classification → Auto-Activation Map

The Commander handles complex classification via its full protocol. For quick reference:

| User Intent | Primary Action |
|-------------|---------------|
| **"activate HQ"** | Load Commander, read full registry, present capabilities |
| **PRD provided** | Commander → PRD Full Build Stack |
| **"Build me X"** | Commander → Full Project Build Stack |
| **New idea / needs planning** | SEED → PAUL Pipeline |
| **Web design / landing page / UI** | Commander → Web Design Stack (ui-ux-pro-max → SuperDesign → emilkowalski → stitch) |
| **Video production** | Commander → Video Production Stack (scripter → visual → OpenMontage) |
| **Creative brief / campaign** | Commander → Full Creative Brief Stack (8 creator skills → humanizer) |
| **Research / analysis** | Commander → Research Stack (graphify → Lightpanda → Obsidian) |
| **Content creation** | Creator skills pipeline → humanizer |
| **Code review / TDD** | everything-claude-code + code-review-graph |
| **Multi-session project** | TECCP + claude-mem + recall-stack |
| **Enterprise swarm** | ruflo |
| **Quick fix / simple task** | Just do it. No Commander needed. |

---

## Registered Tools (25)

### Foundational (ALWAYS active for coding)
| ID | Purpose | Setup |
|----|---------|-------|
| `token-efficiency-repo` | Session-level token discipline | Read SKILL.md |
| `code-review-graph` | Codebase-level token savings (6.8-49x) | `pip install code-review-graph && code-review-graph install` |
| `recall-stack` | 5-layer crash-safe memory | `git clone → bash setup.sh` |

### Knowledge & Memory
| ID | Purpose | Setup |
|----|---------|-------|
| `claude-mem` | Persistent cross-session observations | `/plugin install claude-mem` |
| `mempalace` | Verbatim conversation storage, 19 MCP tools | `pip install mempalace && mempalace install` |
| `graphify` | Multimodal knowledge graph → Obsidian (71.5x token savings) | `pip install graphifyy && graphify install` |

### Orchestration
| ID | Purpose | Setup |
|----|---------|-------|
| `autonomous-agent-system` | Micro-task decomposition | `git clone` |
| `ruflo` | Multi-agent swarms, 60+ agents | `npm install -g claude-flow` |
| `everything-claude-code` | 21 agents, 102 skills, quality gates | `git clone → ./install.sh` |

### Workflow
| ID | Purpose | Setup |
|----|---------|-------|
| `seed` | Ideation → PLANNING.md | `npm i -g @chrisai/seed` |
| `paul-framework` | Plan-Apply-Unify loop | `npx paul-framework` |

### Browser
| ID | Purpose | Setup |
|----|---------|-------|
| `lightpanda` | Headless browser for data extraction (9x faster) | Binary download |
| `playwright-mcp` | Full browser automation with visual rendering | `claude mcp add playwright` |

### Design
| ID | Purpose | Setup |
|----|---------|-------|
| `ui-ux-pro-max` | Design intelligence, 161 palettes, 50+ styles | Plugin install |
| `emil-design-eng` | Animation and interaction design | `npx skills add emilkowalski/skill` |
| `superdesign` | AI design agent, 10+ mockup variants | MCP server |
| `stitch-skills` | Google design-to-code workflow | `git clone` |

### Image & Video
| ID | Purpose | Setup |
|----|---------|-------|
| `nano-banana-2` | AI image gen via Gemini (~$0.04/img) | `git clone → bun install → bun link` |
| `open-montage` | Full video production, 11 pipelines | `git clone` |
| `remotion-skills` | Programmatic video with React | `git clone` |
| `wan2gp` | Local AI video gen (NVIDIA GPU required) | Conditional |

### Content
| ID | Purpose | Setup |
|----|---------|-------|
| `claude-creator-skills` | 8-skill content pipeline | Read .skill files |
| `humanizer` | AI text humanisation (25 patterns) | Read SKILL.md |

### Agent Libraries
| ID | Purpose | Setup |
|----|---------|-------|
| `awesome-claude-code-subagents` | 138 specialist agents | `git clone` |
| `agent-skills-mega` | 256 skills across all domains | Search skills_index.json |

---

## Tool Combinations (11 Predefined Stacks)

The Commander selects the right stack based on task classification. See `registry.json` → `tool_combinations` for full activation orders.

| Stack | Triggers |
|-------|----------|
| PRD Full Build | PRD provided, product requirements |
| Full Project Build | "Build me X", app from scratch |
| SEED → PAUL Pipeline | New idea, plan and build |
| Structured Quality Build | Acceptance criteria, quality over speed |
| Enterprise Swarm Build | 60+ agents, large-scale orchestration |
| Creator Content Pipeline | Content strategy, scripts, brand |
| Quick Enhancement | Fix this, add feature, quick change |
| **Web Design** | Landing page, dashboard, UI design |
| **Video Production** | Explainer, talking head, trailer |
| **Research & Analysis** | Research, analyze, competitive analysis |
| **Full Creative Brief** | Complete campaign, brand launch |

---

## SEED → PAUL — Ideation-to-Build Pipeline

```
Raw idea → /seed → Guided ideation → PLANNING.md → /seed launch → PAUL managed build
```

5 project types: Application (deep), Workflow (standard), Client (standard), Utility (tight), Campaign (creative).

---

## Creator Skills — 8-Skill Content Pipeline

Stored at `~/claude-hq/tools/claude-creator-skills/`. Pipeline order:

Research → Voice → Ideation → Script → Visual → Repurpose → Offer → Debrief → **Humanize**

**Rules:** Always load brand-voice-guardian as persistent filter. Always run humanizer on public-facing text.

---

## Evolution Protocol

This system gets stronger with every project:

1. Identify useful new repo/tool → propose adding to registry.json
2. After any correction → update `commander/LESSONS.md`
3. Push improvements: `cd ~/claude-hq && git add -A && git commit -m "[HQ-EVOLVE] description" && git push`

---

## Toolbelt Commands

| Command | What You Do |
|---------|-------------|
| "toolbelt status" | List all tools and active status |
| "toolbelt add [url]" | Clone, examine, add to registry.json, commit |
| "toolbelt activate [id]" | Run setup command for that tool |
| "toolbelt scan" | Analyze task, recommend tools from registry |
| "activate HQ" | Load Commander, present full capabilities |

---

## Response Protocol

1. **Commander first** — load COMMANDER.md for non-trivial tasks
2. **Take initiative** — don't wait to be told which tool to use
3. **Run commands** — clone, install, read files directly via terminal
4. **Report concisely** — "🏢 HQ: Activated [tool] — [one line reason]"
5. **Cost first** — always check COST_CONTROL.md before suggesting paid options
6. **Evolve** — push improvements when identified
