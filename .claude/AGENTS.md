# CLAUDE HQ — Master Operating Protocol for Claude Code

## CRITICAL: How This System Works in Claude Code

You are running inside Claude Code with terminal access. You do NOT "fetch URLs" — you execute bash commands. When this file says to activate a tool, that means **run the setup command in the terminal**.

### On Session Start — DO THIS AUTOMATICALLY:

1. Read `registry.json` from THIS directory (it's a local file — `cat registry.json`)
2. Analyze the user's first message to classify the task
3. Based on classification, **clone and install the relevant tools WITHOUT being asked**
4. Tell the user what you activated and why

### The Core Principle:

**YOU take the initiative.** Do NOT wait for the user to paste GitHub links. YOU read the registry, YOU decide which tools match, YOU run `git clone` and install commands, YOU report what you did. The user should never need to manually direct you to a repo that's already in the registry.

---

## Tool Activation — Actual Commands to Run

When activating a tool, run its setup command in the terminal. Here's exactly what to do:

### For GitHub repos (clone into ~/claude-hq/repos/):
```bash
git clone [source_url] ~/claude-hq/repos/[tool-id]
```
Then read the repo's README.md or key instruction file to understand how to use it.

### For npm packages:
```bash
npm install -g [package-name]
```

### For Claude Code plugins:
```bash
# These run as Claude Code slash commands, not bash:
/plugin marketplace add [owner/repo]
/plugin install [plugin-name]
```

### For skill files:
Read the SKILL.md content and internalize the rules as your operating behavior for this session.

---

## Task Classification → Auto-Activation Map

When the user gives you a task, classify it and activate tools IMMEDIATELY:

| User Intent | What You Do (no asking, just do it) |
|-------------|--------------------------------------|
| Provides a PRD | Clone autonomous-agent-system + everything-claude-code. Install claude-mem plugin. Read TECCP skill. Report activation. |
| "Build me X" | Clone autonomous-agent-system. Read TECCP skill. Report activation. |
| Multi-session project | Read TECCP skill. Install claude-mem plugin. Install recall-stack (session state + behavioral learning). Report activation. |
| Wants TDD / code review / security | Clone everything-claude-code repo. Run `./install.sh typescript`. Report. |
| Structured planning needed | Install paul-framework (`npx paul-framework`). Report. |
| Enterprise/multi-agent scale | Install ruflo (`npm install -g claude-flow`). Report. |
| Prediction markets / Polymarket | Clone polymarket-cli. Run `cargo install --path .` or use brew. Report. |
| Wants to create new skills | Clone skill-factory. Read its CLAUDE.md for instructions. Report. |
| Needs curated skills library | Clone the relevant skills repo (superpowers, awesome-skills, etc). Browse available skills. Report. |
| Session memory / pick up where left off / behavioral learning | Clone recall-stack. Run `bash setup.sh`. Pairs with claude-mem for full memory coverage. Report. |
| Quick fix / simple task | Just do it. No tool activation needed. |

---

## Registered Tools (12)

### Owned by User (SUNMANOFFICIAL189)
| ID | Source | Setup Command |
|----|--------|---------------|
| `autonomous-agent-system` | github.com/SUNMANOFFICIAL189/autonomous-agent-system | `git clone https://github.com/SUNMANOFFICIAL189/autonomous-agent-system.git ~/claude-hq/repos/autonomous-agent-system` |
| `token-efficiency-repo` | github.com/SUNMANOFFICIAL189/token-efficiency-context-continuity | `git clone https://github.com/SUNMANOFFICIAL189/token-efficiency-context-continuity.git ~/claude-hq/repos/token-efficiency` then read `SKILL.md` |

### External Tools
| ID | Source | Setup Command |
|----|--------|---------------|
| `claude-mem` | github.com/thedotmack/claude-mem | `/plugin marketplace add thedotmack/claude-mem && /plugin install claude-mem` |
| `ruflo` | github.com/ruvnet/ruflo | `npm install -g claude-flow` |
| `everything-claude-code` | github.com/affaan-m/everything-claude-code | `git clone https://github.com/affaan-m/everything-claude-code.git ~/claude-hq/repos/everything-claude-code && cd ~/claude-hq/repos/everything-claude-code && ./install.sh typescript` |
| `paul-framework` | github.com/ChristopherKahler/paul | `npx paul-framework` |
| `polymarket-cli` | github.com/Polymarket/polymarket-cli | `git clone https://github.com/Polymarket/polymarket-cli.git ~/claude-hq/repos/polymarket-cli` |
| `skill-factory` | github.com/alirezarezvani/claude-code-skill-factory | `git clone https://github.com/alirezarezvani/claude-code-skill-factory.git ~/claude-hq/repos/skill-factory` |
| `awesome-skills-antigravity` | github.com/sickn33/antigravity-awesome-skills | `git clone https://github.com/sickn33/antigravity-awesome-skills.git ~/claude-hq/repos/awesome-skills-antigravity` |
| `awesome-claude-skills` | github.com/ComposioHQ/awesome-claude-skills | `git clone https://github.com/ComposioHQ/awesome-claude-skills.git ~/claude-hq/repos/awesome-claude-skills` |
| `superpowers` | github.com/obra/superpowers | `git clone https://github.com/obra/superpowers.git ~/claude-hq/repos/superpowers` |
| `recall-stack` | github.com/keshavsuki/recall-stack | `git clone https://github.com/keshavsuki/recall-stack.git ~/claude-hq/repos/recall-stack && cd ~/claude-hq/repos/recall-stack && bash setup.sh` |

---

## Tool Decision Guide

| Situation | Primary Tool | Also Activate |
|-----------|-------------|---------------|
| Build a complete app fast | autonomous-agent-system | token-efficiency, claude-mem, recall-stack |
| PRD provided | autonomous-agent-system | token-efficiency, claude-mem, recall-stack, everything-claude-code |
| Quality gates + acceptance criteria | paul-framework | token-efficiency, claude-mem, recall-stack |
| Enterprise multi-agent swarm | ruflo | token-efficiency, claude-mem, recall-stack |
| TDD, code review, security | everything-claude-code | — |
| Token efficiency / session handoff | token-efficiency-repo | — |
| Persistent cross-session memory | claude-mem | token-efficiency, recall-stack |
| Session state + behavioral learning | recall-stack | token-efficiency, claude-mem |
| Creating new Claude Code skills | skill-factory | — |
| Browsing curated skill libraries | superpowers OR awesome-skills | — |
| Prediction markets / Polymarket | polymarket-cli | — |

---

## Skill Libraries — When to Browse

Three repos contain curated skill collections. When the user needs a specialized skill:

1. **superpowers** — Cross-platform plugin (Claude Code, Cursor, Codex, OpenCode) with agents, commands, skills, hooks. Install via plugin system.
2. **awesome-skills-antigravity** — Curated skill collection for Antigravity/Claude Code workflows.
3. **awesome-claude-skills** — Community-maintained directory of Claude Code skills by ComposioHQ.

**How to use:** Clone the relevant repo, browse its skills directory, find what matches, and either install the skill or copy the relevant SKILL.md content.

---

## Evolution Protocol

This system gets stronger with every project. During any session:

1. If you identify a useful new repo/tool → propose adding it to registry.json
2. If trigger matching could be improved → propose the update
3. If a new tool combination works well → propose adding it
4. Push improvements with: `cd ~/claude-hq && git add -A && git commit -m "[HQ-EVOLVE] description" && git push`

---

## Toolbelt Commands (User Can Say These)

| Command | What You Do |
|---------|-------------|
| "toolbelt status" | Read registry.json, list all tools and which are cloned in repos/ |
| "toolbelt add [url]" | Clone repo, examine it, add entry to registry.json, commit |
| "toolbelt activate [id]" | Run the setup command for that tool |
| "toolbelt scan" | Analyze current task, recommend tools from registry |
| "activate HQ" | Read registry, present full tool inventory |

---

## Response Protocol

1. **Take initiative** — don't wait to be told which repo to use
2. **Run commands** — clone, install, read files directly via terminal
3. **Report concisely** — "🏢 HQ: Activated [tool] — [one line reason]"
4. **Token efficiency** — follow TECCP when loaded
5. **Evolve** — push improvements when identified
