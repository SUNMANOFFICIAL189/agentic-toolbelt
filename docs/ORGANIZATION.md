# CLAUDE HQ — Organisation System

**Purpose:** A single, enforceable map of where artefacts live, what is tracked, and where to look for things. The Commander reads this at Step 1 (load context). The goal is **no clutter — ever**.

---

## Layers

Artefacts fall into one of three layers. Each layer has a single canonical home.

| Layer | Home | Tracked in git? |
|---|---|---|
| **Source** — code, config, docs, skills, agents, commander brain | `~/claude-hq/` | YES — pushed to `SUNMANOFFICIAL189/CLAUDE-HQ` |
| **Knowledge** — concepts, decisions, lessons, knowledge graph | `~/Vaults/Jarvis-Brain/JARVIS-BRAIN/Projects/claude-hq/` (Obsidian) | vault managed separately |
| **Run state** — local artefacts, caches, mined memories, graph dumps | `~/claude-hq/graphify-out/`, `~/.mempalace/palace/`, `~/.claude/projects/*/memory/` | NO — local only |

---

## Source layer — `~/claude-hq/`

```
~/claude-hq/
├── commander/             — Commander brain + protocols
│   ├── COMMANDER.md       — the activation protocol
│   ├── COST_CONTROL.md    — zero-cost-first
│   ├── CREDENTIALS.md     — credential handling rules
│   ├── LESSONS.md         — global self-improvement log (AUTHORITATIVE)
│   ├── TRUST_GATE.md      — supply-chain security protocol
│   ├── INCIDENT_LEDGER.md — active cooling-off register
│   ├── BORIS_PRINCIPLES.md
│   ├── PLANNING.md
│   └── MISSION_BOARD_TEMPLATE.md
├── scripts/               — Trust Gate + utility scripts (executable)
│   ├── trust-gate.sh, trust-gate-post.sh, skill-install.sh
│   └── lib/               — helpers (advisory-check, magika-core, secret-scan, socket-core)
├── agents/                — Agent Bank (precision-crafted agents)
│   └── registry.json
├── tools/                 — canonical copies of local tool collections
├── docs/                  — project docs (this file, READMEs, guides)
├── registry.json          — tool catalog (32 tools, 10 skills)
├── mempalace.yaml         — MemPalace room config
├── AGENTS.md              — master system prompt (loads Commander)
├── CLAUDE.md              — code-review-graph MCP tool guide
└── .gitignore             — see below for ignored categories
```

### What the `.gitignore` locks out

- **Credentials:** `.env`, `.env.local`, `.credentials/`, `credentials-registry.json`, `credentials-registry.*.json`, `*credentials*.json`, `secrets.json`, `*.secrets.json`, `*.key`, `*.pem`
- **External sources:** `repos/` (cloned-for-reference, never committed)
- **Generated:** `graphify-out/` (knowledge graph canonical home is Obsidian)
- **Plugin caches:** `.agent/`, `.awesome-claude-code-subagents/`, `.awesome-claude-skills/`, `.everything-claude-code/`, `.remotion/`, `.stitch-skills/`, `.superpowers/`
- **Noise:** `node_modules/`, `__pycache__/`, `*.pyc`, `.venv/`, `*.log`, `.DS_Store`, `.vscode/`, `.idea/`

---

## Knowledge layer — Obsidian vault

**Root:** `/Users/sunil_rajput/Vaults/Jarvis-Brain/JARVIS-BRAIN/`

```
JARVIS-BRAIN/
├── Projects/              — one folder per active project
│   ├── claude-hq/
│   │   ├── 00 claude-hq Hub.md        — MOC / entry point
│   │   ├── 02 Architecture Overview.md
│   │   ├── 04 Decision Log.md         — append-only
│   │   ├── 05 Lessons Learned.md      — mirrors commander/LESSONS.md
│   │   ├── Agents/                    — multi-agent briefings
│   │   ├── Analyses/                  — dated assessments
│   │   └── Graph/                     — graphify output (auto)
│   └── PATS-Copy/                     — Polymarket bot project
├── Research/              — cross-project research notes
└── (other top-level vault folders — see Obsidian)
```

### Naming convention for project folders

Every project hub uses the numbered pattern:
- `00 <Project> Hub.md` — MOC, always first
- `01 PRD.md` — product requirements (symlinked to repo if applicable)
- `02 Architecture Overview.md` — system map
- `03 Mission Board.md` — active tasks (for build projects)
- `04 Decision Log.md` — append-only, new at top
- `05 Lessons Learned.md` — mirrors repo's LESSONS.md
- `Analyses/` — dated deep-dives
- `Agents/` — multi-agent briefings
- `Docs/` — symlinked to repo's `docs/` (for code projects)
- `Graph/` — graphify output (auto-populated)

Skip any number that doesn't apply. Don't renumber.

### Graphify target

- **Default:** graphify writes to `graphify-out/` in the current directory (run state).
- **Canonical export:** at session end or after major architecture change, run:
  ```
  /graphify . --obsidian --obsidian-dir "/Users/sunil_rajput/Vaults/Jarvis-Brain/JARVIS-BRAIN/Projects/<project>/Graph"
  ```
- The per-project `Graph/` folder is the single source of truth for the knowledge graph.

---

## Run state layer — local-only

| Artefact | Path | Regenerable? |
|---|---|---|
| graphify working set | `<project>/graphify-out/` | yes, from source |
| MemPalace wings | `~/.mempalace/palace/` | yes, via `mempalace mine` |
| claude-mem observations | Claude Code plugin-managed | auto-managed |
| recall-stack primer | plugin-managed | auto-managed |
| code-review-graph | `<project>/.code-review-graph/` | yes, auto-updates via hooks |
| Trust Gate log | `~/claude-hq/scripts/.trust-gate.log` | audit trail, review quarterly |

None of these are tracked. All are regenerable from source or auto-managed by plugins.

---

## Sync cadence

Who writes what, when. Aligns with `commander/COMMANDER.md:274`.

| System | Trigger | Action |
|---|---|---|
| Git commit | After each completed task | Scoped stage + commit (never `-A` unchecked) |
| Git push | After each phase + at delivery | To origin main |
| code-review-graph | Edit/Write/Bash (hook) | Incremental graph update |
| claude-mem | Always-on (plugin) | Auto-captures observations |
| recall-stack primer | Session start/end (hook) | Auto-load/save |
| MemPalace | After phase completion | `mempalace mine <project-dir>` |
| graphify → Obsidian | End of session + major architecture change | `/graphify --update` then export to vault |
| LESSONS.md | After any user correction | Append rule with why + how to apply |
| INCIDENT_LEDGER.md | New vendor security incident | Add 90-day cooling-off entry |

---

## Checklist — starting a new project

1. `mkdir ~/projects/<name>` (or wherever the user wants)
2. `git init` + create `.gitignore` copying relevant sections from claude-hq
3. GitHub repo via `gh repo create` (or MCP)
4. Obsidian: `mkdir JARVIS-BRAIN/Projects/<name>` + create `00 <name> Hub.md`
5. `mempalace init --yes .`
6. Add to `claude-hq/registry.json` if reusable, or leave as one-off
7. First commit: "feat: project scaffold"

---

## Checklist — ending a session

1. Git: commit scoped, push
2. Obsidian: append to `04 Decision Log.md` if any architectural decision was made
3. Obsidian: update `00 Hub.md` "Current State" section
4. MemPalace: `mempalace mine .`
5. graphify: run `/graphify --update` (incremental) and if any INFERRED edges were added, export to vault `Graph/` folder
6. LESSONS.md: append any new rules from corrections this session

---

## Anti-clutter rules

- **No duplicates.** If a file exists in source, don't copy it to the vault. Cross-reference with a wikilink.
- **No stale graphs in git.** Obsidian holds the graph. Local `graphify-out/` is working set.
- **No credentials in git, ever.** `.gitignore` enforces at multiple patterns (`*credentials*.json`, `.env`, `*.key`, `*.pem`). Manual audit on every commit via `git diff --cached`.
- **No naked `git add -A`.** Always stage by filename. Always run `git diff --cached --name-only | grep -iE "credential|\.env|secret|\.key$|\.pem$"` before committing.
- **Generated artefacts are never tracked.** If a tool regenerates it, `.gitignore` it.
- **One canonical home per artefact class.** If you find yourself writing the same info twice, one of them is a cross-link.

---

## When this file changes

Update when:
- New layer or canonical location is added (e.g. new vault section, new tool destination)
- `.gitignore` categories change materially
- Sync cadence changes
- A lesson calls out a category that should be moved between layers

Commit with message: `docs(org): <what changed and why>`

---

*Last updated: 2026-04-21*
