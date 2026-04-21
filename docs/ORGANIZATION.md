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

**Path:** `/Users/sunil_rajput/Vaults/Jarvis-Brain/JARVIS-BRAIN/`
**Backup:** `github.com/SUNMANOFFICIAL189/jarvis-brain` (private). Session-end commit + push.

```
JARVIS-BRAIN/
├── Projects/              — one folder per active project or infrastructure
│   ├── claude-hq/                            — this system
│   │   ├── Hub.md                            — MOC / entry point
│   │   ├── Architecture.md                   — system map
│   │   ├── Decision Log.md                   — append-only with provenance tags
│   │   ├── Commander/ → ~/claude-hq/commander/   — SYMLINK to source repo
│   │   ├── Graph/                            — graphify output (auto)
│   │   ├── Agents/                           — multi-agent briefings
│   │   └── Analyses/                         — dated assessments
│   └── PATS-Copy/                            — Polymarket bot
│       ├── 00 PATS-Copy Hub.md               — numbered pattern (product project)
│       ├── 01 PRD.md → Desktop/POLYMARKET.../prd-pats-copy-full.md   — SYMLINK
│       ├── 02 Architecture Overview.md
│       ├── 03 Mission Board.md
│       ├── 04 Decision Log.md
│       ├── 05 Lessons Learned.md
│       ├── Agents/ Analyses/ Docs/           — Analyses contain more symlinks
│       └── Graph/
├── Research/              — cross-project research
└── (historical graphify dumps at root — legacy, cleanup pending)
```

### Two file-naming patterns, pick the right one

Projects are of two kinds. Pick the pattern that matches the shape of the work, not PATS-Copy-by-default.

**(a) Deliverable-producing projects** — a product, a codebase being built, a campaign. Use the numbered pattern:
- `00 <Project> Hub.md` — MOC
- `01 PRD.md` — product requirements (symlink to repo if source lives elsewhere)
- `02 Architecture Overview.md`
- `03 Mission Board.md` — active tasks
- `04 Decision Log.md` — append-only
- `05 Lessons Learned.md` — mirrors repo's LESSONS.md (or symlink to repo file)

Example: `PATS-Copy/` (the Polymarket bot is a product).

**(b) Infrastructure / orchestration systems** — the brain, meta-tools, long-lived ops. Use descriptive filenames, no artificial numbering:
- `Hub.md` — MOC
- `Architecture.md` — system map
- `Decision Log.md` — append-only with provenance tags
- no artificial "01 PRD" or "03 Mission Board" — infrastructure doesn't have a PRD

Example: `claude-hq/` (the orchestration brain is infrastructure).

Both kinds share: `Agents/`, `Analyses/`, `Graph/`.

### Symlinks over duplication (the PATS-Copy pattern)

When a file lives in a source repo, surface it in the vault via symlink — don't copy it into the vault.

- PATS-Copy example: `01 PRD.md` → `~/Desktop/POLYMARKET_TRADING_3.0/prd-pats-copy-full.md`
- claude-hq example: `Commander/` → `~/claude-hq/commander/`

Benefits: zero drift (one file on disk), bidirectional edits (Obsidian edits the repo file directly), wikilinks work (`[[Commander/LESSONS]]` resolves).

Caveat: symlinks break if the target is deleted or moved. When moving source files, update vault symlinks in the same commit.

### Graphify target

- **Working set:** `<project>/graphify-out/` in the source repo (run state, gitignored).
- **Canonical export:** at session end or after major architecture change:
  ```
  /graphify . --obsidian --obsidian-dir "/Users/sunil_rajput/Vaults/Jarvis-Brain/JARVIS-BRAIN/Projects/<project>/Graph"
  ```
- The per-project `Graph/` folder in the vault is the authoritative knowledge graph.

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
| Vault git backup | Session end | `cd ~/Vaults/Jarvis-Brain && git add -A && git commit -m "Session <timestamp>" && git push` |

---

## Checklist — starting a new project

1. Decide: **deliverable-producing** (pattern a, numbered) or **infrastructure/orchestration** (pattern b, descriptive)? Pick naming accordingly.
2. `mkdir ~/projects/<name>` (or wherever the user wants)
3. `git init` + create `.gitignore` copying relevant sections from claude-hq
4. GitHub repo via `gh repo create` (or MCP)
5. Obsidian: `mkdir JARVIS-BRAIN/Projects/<name>` + create hub note (`00 <name> Hub.md` for pattern a, `Hub.md` for pattern b)
6. Symlink any canonical source files into the vault (e.g. `ln -s ~/<repo>/docs Projects/<name>/Docs`)
7. `mempalace init --yes .`
8. Add to `claude-hq/registry.json` if reusable, or leave as one-off
9. First commit: "feat: project scaffold"

---

## Checklist — ending a session

1. Git (source repo): commit scoped, push
2. Obsidian: append to Decision Log if any architectural decision was made (tag with provenance: `[Sunil · strategic]` / `[Claude · implementation]` / `[Joint]`)
3. Obsidian: update Hub's "Current State" section if facts changed
4. MemPalace: `mempalace mine .`
5. graphify: run `/graphify --update` (incremental) and if any INFERRED edges were added, export to vault `Graph/` folder
6. LESSONS.md: append any new rules from corrections this session
7. Git (vault): `cd ~/Vaults/Jarvis-Brain && git add -A && git commit -m "Session $(date +%F-%H%M)" && git push`

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
