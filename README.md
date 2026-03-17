# 🔧 Agentic Toolbelt

**The ultimate command center for Claude-powered autonomous development**

> A curated arsenal of GitHub repos, MCP servers, custom skills, and automation tools that Claude autonomously selects and activates based on task requirements.

---

## 🎯 What Is This?

This repo is a **meta-registry** — it doesn't contain tool code, it contains **references** to tools and the intelligence layer that tells Claude:

1. **What tools exist** → `registry.json`
2. **When to use each** → activation triggers
3. **How to activate them** → fetch from GitHub raw URLs
4. **Which combinations work** → predefined tool stacks

Claude reads `registry.json` at session start and uses the Tool Selection Algorithm in `.claude/AGENTS.md` to match tasks to optimal tools.

---

## 🚀 Quick Start

### With Claude Code

```bash
git clone https://github.com/SUNMANOFFICIAL189/agentic-toolbelt.git
cd agentic-toolbelt
claude   # reads .claude/AGENTS.md automatically
```

### With Claude Desktop / Claude.ai

```
Fetch and load:
https://raw.githubusercontent.com/SUNMANOFFICIAL189/agentic-toolbelt/main/.claude/AGENTS.md

Then fetch the registry:
https://raw.githubusercontent.com/SUNMANOFFICIAL189/agentic-toolbelt/main/registry.json

Confirm you understand and list available tools.
```

---

## 📦 Registered Tools

| ID | Name | Category | When It Activates |
|----|------|----------|-------------------|
| `autonomous-agent-system` | [Autonomous Build System](https://github.com/SUNMANOFFICIAL189/autonomous-agent-system) | orchestration | Full app builds from scratch |
| `token-efficiency-repo` | [TECCP System](https://github.com/SUNMANOFFICIAL189/token-efficiency-context-continuity) | efficiency | Multi-session projects |

## ➕ Adding New Tools

```
toolbelt add https://github.com/owner/repo-name
```

Claude examines the repo, generates triggers, and commits the registry entry. Works for your own repos AND any external repos.

Or manually: copy `templates/tool-registration-template.json`, fill it in, add to `registry.json`.

---

## 🏗️ Architecture

```
agentic-toolbelt/
├── .claude/AGENTS.md          ← Master system prompt
├── registry.json              ← Tool catalog (Claude reads this)
├── tools/                     ← Source references per tool
│   ├── autonomous-agent-system/.source
│   └── token-efficiency/.source
├── repos/                     ← Cloned on-demand (gitignored)
└── templates/                 ← Registration templates
```

**Key:** Tools are referenced, not duplicated. `repos/` is gitignored.

---

## 🔄 Toolbelt Commands

| Command | Action |
|---------|--------|
| `toolbelt status` | All tools + active status |
| `toolbelt add [url]` | Register new tool |
| `toolbelt remove [id]` | Deregister tool |
| `toolbelt activate [id]` | Manual activation |
| `toolbelt scan` | Analyze task → recommend tools |

---

## 📜 License

MIT

**Maintained by:** SUNMANOFFICIAL189
