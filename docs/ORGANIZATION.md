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

## Project classification & capability layers

Before scaffolding a new project, decide what *type* of project it is. The type determines which **capability layers** apply, which determines which tools and patterns to wire in. Most mistakes come from applying heavyweight patterns where they don't belong — or from skipping resilience where it's needed.

### The four "self-X" layers (decision tree)

Walk this in order. Each "yes" adds the layer above to your toolset.

```
1. Will the project run a long-living process? (web server, bot, daemon, scheduler)
   YES → Layer A (process resilience) + Layer B (application resilience)
   NO  → skip A and B; layer 0 still applies

2. Will it make autonomous decisions without a human in the loop?
   YES → also Layer C (operational resilience)
   NO  → skip C

3. Will it run multiple independent agents competing for capital?
   YES → also Layer D (strategic resilience) — Fleet-shaped
   NO  → skip D
```

### Layer 0 — Cognitive infrastructure (always on, every project)

Universal across every project regardless of type. These run at HQ level and don't require per-project setup beyond registration:

| Tool | Job |
|---|---|
| `claude-mem` | Auto-captures session observations across all projects |
| HQ Watchdog (via `projects.json`) | Quality monitoring + plain-English Telegram alerts |
| MemPalace | Cross-session memory database |
| recall-stack primer | Session-start context auto-load |
| Obsidian vault + graphify | Knowledge graph + decisions captured |
| `code-review-graph` (per-project install) | Codebase exploration via MCP |
| Trust Gate | Supply-chain security on every install/clone |
| `commander/LESSONS.md` | Global rule accumulation across projects |

**Layer 0 setup per project:** add an entry to `~/claude-hq/watchdog/projects.json`; create vault `Projects/<name>/` folder with hub; run `mempalace init --yes` in project dir. That's it — Layer 0 is mostly "register and forget."

### Layer A — Process resilience (any project with long-running components)

**Goal:** auto-restart on crash; survive Mac reboot.

| Implementation | When to use |
|---|---|
| macOS **launchd plist** (`~/Library/LaunchAgents/com.<scope>.<service>.plist`, `KeepAlive=Crashed`) | Clean services with no exotic monitoring needs. Best default. |
| Per-project **`watchdog.sh`** shell script | When monitoring needs are richer than process-up/down (dependency checks, log-staleness detection, duplicate-instance kills). |
| Hosted supervisor (Vercel, PM2 on Hetzner, systemd) | When deployed off-Mac. |

**Existing examples:**
- PATS-Copy → `watchdog.sh` (also checks Ollama dep, log staleness, duplicate bots)
- Paperclip → launchd plist (no exotic needs)
- Mission Control → currently nohup-only — known gap; manual restart required if it stops

### Layer B — Application resilience (any serious codebase)

**Goal:** errors caught and handled gracefully; failures don't cascade.

**Patterns:**
- try/catch + retry-with-exponential-backoff at network boundaries
- Circuit breakers for unhealthy dependencies (PATS-Copy: 14% drawdown breaker)
- Fallback paths (PATS-Copy: Cerebras → OpenRouter AI fallback)
- Health/readiness endpoints
- TDD coverage via `everything-claude-code` skills

Always implement Layer A and B together — process auto-restart without good error handling just creates a crash loop.

### Layer C — Operational resilience (autonomous decision-making projects)

**Goal:** when the *strategy* isn't working, adapt before failing.

This applies whenever code makes decisions without a human reviewing each one. Trading bot picks trades. UGC ads agent picks outreach copy. Investments app auto-rebalances portfolios.

**Patterns:**
- **4-tier survival ramp** (Pattern 1 from Automaton, adopted 2026-04-27): Normal → Conserve → Critical → Dead. Degrade before death.
- **Hierarchical immutable laws** (Pattern 2 from Automaton): Law I (capital sovereignty) > Law II (commitment to outcome) > Law III (operational tempo). Higher law overrides on conflict.
- **Strategy circuit breakers** (PATS-Copy: HARD BLOCK at 20% rolling WR drops failing wallets)
- **Multi-strategy retry playbooks** (codified in a `HEALING_PLAYBOOK.md` per agent — Fleet pattern)
- **Mortality protocol** (project-level kill triggers + survival tier transitions)

Either implementation form works:
- Modules in code (PATS-Copy's `risk-manager.ts`, `position-lifecycle.ts`, etc.)
- Specialist agents in a control plane (Fleet's "Healer" + "Validator" Paperclip agents)

### Layer D — Strategic resilience (portfolios of independent agents)

**Goal:** terminate non-performing agents, archive lessons, redirect capital to winners.

Only applies when there are multiple autonomous agents competing for resources within one project. PATS-Copy doesn't qualify (one bot). Fleet does (Agent Alpha, future Beta/Gamma/etc.).

**Patterns:**
- Paperclip-style control plane (multi-company isolation, org charts, governance)
- FleetCommander reading every live agent's mission board
- Capital ledger + approval queue (real-time spend gating)
- Dead-agent archives in `lessons/deceased/`
- Cross-agent learnings repo (`LESSONS_FLEET.md`)
- Graduation criteria for agents that survive eval windows

### Project-type → typical layer mix

| Project shape | Layers needed | Typical tooling |
|---|---|---|
| Autonomous revenue agent (Fleet vertical) | 0 + A + B + C + D | Paperclip + specialist roster + mortality + capital ledger |
| Autonomous bot in single-agent mode (PATS-Copy) | 0 + A + B + C | `watchdog.sh` + circuit breakers + AI fallbacks + `risk-manager.ts` |
| Code project / web app (e.g. investments tool) | 0 + A + B | launchd + tests + `everything-claude-code` TDD |
| Static site / library / one-shot script | 0 + B (light) | tests if needed; deploy and forget |
| Research / analysis project | 0 only | Obsidian + graphify + claude-mem deep usage |
| Creative production (video, content campaigns) | 0 + A (if always-on) | Higgsfield, fal.ai, `content-engine`, `video-editing` skills |

### Anti-pattern checklist (avoid these)

- ❌ **Don't apply Layer C+D heaviness to a code project.** Building a static dashboard with mortality protocol and Paperclip agents is overengineering.
- ❌ **Don't skip Layer A+B on a long-running service.** Even "simple" daemons should auto-restart and handle errors. Cost is small; risk of skipping is large.
- ❌ **Don't assume "one Claude does everything" scales.** When operational complexity grows (multiple decisions per day, healing logic, cycle retrospectives), the specialist-agent roster pattern becomes worth its overhead.
- ❌ **Don't duplicate state in markdown when Paperclip / a real DB holds it.** Use markdown for *doctrine* (playbooks, plans, governance docs); use the DB for *state* (issues, costs, approvals). Single source of truth.
- ❌ **Don't fork external dependencies until you have actual customisations.** Pin upstream commits, document the pin, only fork when you have a patch to land.

### Example walks

**"I'm building an AI agent for B2B outreach (Agent Beta)" — Fleet vertical**
- Step 1: long-living? YES (heartbeat-driven). Add A + B.
- Step 2: autonomous decisions? YES (picks ICPs, drafts emails). Add C.
- Step 3: portfolio? YES (it's part of the Fleet alongside Alpha). Add D.
- Result: Layers 0+A+B+C+D. New "company" in Paperclip + 5 specialist agents + entry in Fleet board + watchdog `projects.json` registration (already covered by Fleet entry).

**"I'm building an investments tool web app for tracking portfolios"**
- Step 1: long-living? YES (web server). Add A + B.
- Step 2: autonomous decisions? Probably NO (UI for user, not auto-rebalance). Skip C.
- Step 3: portfolio? NO. Skip D.
- Result: Layers 0 + A + B. Mission Control or Cursor for session observability, launchd or Vercel for deployment, vitest+playwright for tests, code-review-graph + everything-claude-code for development. **NOT Paperclip, NOT mortality protocol, NOT 5 specialist agents.**

**"I want to research the latest LLM evaluation benchmarks"**
- Step 1: long-living? NO.
- Step 2: autonomous? NO.
- Step 3: portfolio? NO.
- Result: Layer 0 only. Heavy use of Obsidian, graphify, deep-research skills, claude-mem to capture findings across sessions. No process management, no test infrastructure, no orchestration.

---

## Checklist — starting a new project

0. **Walk the project classification decision tree** (above) to determine which capability layers apply. The rest of this checklist scaffolds Layer 0 + your chosen layers (A/B/C/D as applicable).
1. Decide: **deliverable-producing** (pattern a, numbered) or **infrastructure/orchestration** (pattern b, descriptive)? Pick naming accordingly.
2. `mkdir ~/projects/<name>` (or wherever the user wants)
3. `git init` + create `.gitignore` copying relevant sections from claude-hq
4. GitHub repo via `gh repo create` (or MCP)
5. Obsidian: `mkdir JARVIS-BRAIN/Projects/<name>` + create hub note (`00 <name> Hub.md` for pattern a, `Hub.md` for pattern b)
6. Symlink any canonical source files into the vault (e.g. `ln -s ~/<repo>/docs Projects/<name>/Docs`)
7. `mempalace init --yes .`
8. **Register in HQ Watchdog** — add an entry to `~/claude-hq/watchdog/projects.json` with `name` (must match dir basename so session-file ingestion works), `display_name`, `repo_path`, and `lessons_path`. This wires Layer 0 quality monitoring + Telegram alerts. Required for every project.
9. Add to `claude-hq/registry.json` if reusable, or leave as one-off
10. **Layer-specific scaffolding** based on classification (above):
    - Layer A → drop in launchd plist or `watchdog.sh`
    - Layer B → wire test framework + error-handling patterns
    - Layer C → draft `HEALING_PLAYBOOK.md`, `MORTALITY_PROTOCOL.md` (if applicable)
    - Layer D → provision Paperclip company + specialist roster
11. First commit: "feat: project scaffold"

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
