# CLAUDE HQ — Improvements Backlog

**Purpose:** Deferred improvements to Claude HQ. Items here are not scheduled — they are captured so we don't forget them when we next sit down to improve the system. Revisit during any HQ tune-up session or when a listed item becomes blocking.

**Convention:**
- Add new items at the bottom with `## [Open] — YYYY-MM-DD — <title>`
- When an item is picked up, change `[Open]` → `[In progress]` and add owner
- When done, change to `[Done] — YYYY-MM-DD` and leave the entry in place (do not delete; it's our audit trail)

---

## [Open] — 2026-04-22 — Audit TECCP once, fold rules into AGENTS.md

**What:** Read through `~/claude-hq/tools/token-efficiency/.source` target repo (`https://github.com/SUNMANOFFICIAL189/token-efficiency-context-continuity`). Extract the rules that actually reduce waste (token discipline, context buffer monitoring, anti-hallucination patterns, GitHub-backed task tracking). Fold them into `~/claude-hq/AGENTS.md` as first-class HQ directives.

**Why:** TECCP's real value is its rules, not a plugin wrapper. Hoisting rules into AGENTS.md gives them to every session without a separate install, startup cost, or maintenance drift against an upstream. After the hoist, the standalone repo can be retired as a reference.

**Estimate:** 1–2 hours. Mostly reading + distilling, one-pass edit to AGENTS.md, commit.

**How to start:**
1. `git clone` the repo via Trust Gate (owner is self, allowlisted).
2. Read README + any `rules.md` / `principles.md` / skill files.
3. Draft a TECCP section for AGENTS.md with the rules that pass the "would this change Claude's behaviour on a real task?" test. Drop the rest.
4. Commit: `feat(agents): fold TECCP rules into HQ directives`.
5. Delete `tools/token-efficiency/.source` stub (or leave a note pointing to where the rules landed).

**Acceptance:** AGENTS.md has a TECCP rules section. A new session shows the rules applied. Stub removed or annotated.

---

## [Open] — 2026-04-22 — Lift 3–4 best templates from seed into ~/claude-hq/templates/

**What:** Walk the already-cloned `~/claude-hq/repos/seed/` for its best templates (micro-task decomposition prompts, error-handling patterns, any scaffolding that maps to how we actually work). Copy the keepers into `~/claude-hq/templates/` with a short `README.md` describing when to use each.

**Why:** seed is a methodology, not a daemon — installing it as a framework is overkill. But the 3–4 best templates are genuinely reusable. Having them as HQ-native files means the Commander can cite them directly in plans without loading seed's whole world.

**Estimate:** ~30 minutes once we're in the repo.

**How to start:**
1. `ls ~/claude-hq/repos/seed/templates ~/claude-hq/repos/seed/examples` (or equivalent — explore structure first).
2. Read candidates, pick the 3–4 that actually match how we decompose work.
3. Copy into `~/claude-hq/templates/seed-<name>.md` with a one-line header noting origin and licence.
4. Add a short `~/claude-hq/templates/README.md` indexing them.
5. Commit: `feat(templates): lift seed micro-task + error-handling templates`.

**Acceptance:** `templates/` has 3–4 new files plus an index. Commander's planning step can reference them by path.

---

## [Open] — 2026-04-22 — Write Commander-specific slash commands for our recurring patterns

**What:** Identify the 3–5 patterns we actually repeat across projects (e.g., PATS-Copy scraper cycle, PRD → build bootstrap, end-of-session sync, wallet/signal investigation loop, dashboard regression pass). Encode each as a slash command in `~/claude-hq/commands/` (or project-scoped `.claude/commands/` where it's project-specific).

**Why:** Custom slash commands for *our* patterns are higher ROI than installing someone else's generic framework. They capture institutional knowledge, reduce per-session prompt overhead, and make the Commander's "Step 2 classify" faster because the triggers are explicit.

**Estimate:** 1–3 hours total, depending on how many commands. Each command is small.

**How to start:**
1. Review the last 5 sessions' summaries (claude-mem search) and list prompts/flows that repeated verbatim or near-verbatim.
2. For each repeat: define the trigger phrase, the steps, the expected output, what gets committed, and knowledge-layer updates.
3. Draft as markdown files in `~/claude-hq/commands/<name>.md` with frontmatter (`name`, `description`, `category`).
4. Register in `registry.json` so Commander picks them up on activation.
5. Commit: `feat(commands): add <n> recurring-pattern slash commands`.

**Candidate commands (from memory — refine when picking this up):**
- `/pats-cycle` — wallet scan → signal eval → copy decision → mission-board update
- `/prd-bootstrap` — Step 0 bootstrap flow in one command
- `/session-sync` — checkpoint: git commit + mempalace mine + graphify update + vault push
- `/investigate` — wallet/flaw investigation with agent orchestration

**Acceptance:** `commands/` has the new files, registry.json lists them, one real task has been run through a new command end-to-end to validate.

---

## [Open] — 2026-04-22 — Measure before adding: baseline HQ's current token spend per task

**What:** Before installing anything else (ruflo, paul, etc.) establish a baseline of what each task class actually costs in tokens today. Break it down: how much goes to file reads vs. agent coordination vs. hook output vs. actual reasoning.

**Why:** Adding tools without measurement is guessing. Today we have no idea which part of HQ is token-heavy — is it skills loading at session start? Redundant Grep/Read before code-review-graph does its job? Hook output noise? Until we can answer that, any "let's install X to save tokens" decision is faith-based.

**Estimate:** Unclear — could be 2 hours (eyeball transcripts) or a day (build a proper measurement harness). Start with eyeball.

**How to start:**
1. Pick 3 representative past sessions of different sizes (short/medium/long).
2. For each, estimate or count: session-start hook/skill load tokens, tool-call tokens, reasoning tokens, final output tokens.
3. Identify the top 3 token sinks.
4. Draft a cheap fix for each sink (e.g., "trim session-start hooks output," "prefer code-review-graph over Grep in AGENTS.md," "compact tool results in claude-mem").
5. If there's value in repeatability: add a `scripts/measure-session.sh` that parses session JSON and reports token breakdown.
6. Record findings in `docs/TOKEN_AUDIT_<date>.md`.

**Acceptance:** A token-spend baseline doc exists for at least 3 session classes. Top 3 sinks are named with proposed fixes. A rule goes into LESSONS.md: "don't install a new tool for token efficiency without citing baseline data."

---

## Source

Captured 2026-04-22 during HQ activation conversation. User (Sunil) asked whether to install ruflo / seed / paul / TECCP into HQ. Conclusion was that adding more frameworks adds overhead without clear gain — these four actions are the higher-leverage alternatives. Full reasoning is in that session's transcript.
