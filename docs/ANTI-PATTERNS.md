# ANTI-PATTERNS — what we tried and dropped, with reasons

> **Things we tried that didn't work, plus things that look tempting but
> are actively dangerous.** Read at task start (via `memory-probe.sh`)
> so RAG doesn't surface a dropped pattern as if it were live, and so
> we don't re-invent a problem we already solved by walking away.
>
> An entry earns a place here when (a) we adopted the approach and
> later dropped it, OR (b) we considered the approach and rejected it
> with explicit reasoning we want to remember.
>
> **When to add an entry:** the moment a pilot is killed, or a
> tempting-but-wrong approach is rejected. Capture the why while it's
> fresh.

---

## ❌ Goose RPI recipes (research/plan/implement/iterate slash commands)

**What we tried:** Ported four `/rpi-*` slash commands from `aaif-goose/goose` (Apache 2.0) and adapted them as Claude Code slash commands to enforce a research-then-plan-then-implement workflow.

**Why it failed:** Twelve days after deployment (2026-04-24 → 2026-05-06), zero invocations. Three reasons: (a) project-scoped to `~/claude-hq` cwd, invisible everywhere else; (b) Commander's Steps 2-6 already provided the same shape; (c) no measurement was wired so we couldn't even objectively prove non-use until the manual review.

**Lesson captured:** Rule 19 (mid-complexity tasks get a brief plan-aloud before first edit) — keep the discipline as *behaviour*, not as parallel infrastructure that requires the user to remember another command.

**Don't suggest re-introducing this.** If you find yourself reaching for a "research → plan → implement → iterate" slash command, the answer is: do that *as behaviour* in conversation, per Lesson 19.

---

## ❌ `mempalace repair` subcommand (segfaults on real corruption)

**What it claims:** mempalace ships a built-in `repair` subcommand that should fix corrupted palaces.

**Why it doesn't help:** On the 2026-05-08 chroma segment_id drift incident, `mempalace repair` itself segfaulted with the same `hnswlib::HierarchicalNSW::searchBaseLayer` crash as `mine` and `search`. The repair logic loads the corrupt HNSW index in the same way the broken commands do, so it inherits the crash.

**Use instead:** the recovery procedure in `~/claude-hq/docs/mempalace-corruption-runbook.md` — Path A (surgical SQL retarget) or Path B (clean reset + re-mine). Path B is the proven recovery.

**Don't suggest `mempalace repair` as a fix** for any palace problem until / unless upstream mempalace addresses this. If you do try it, expect a segfault.

---

## ❌ `graphify --update ~/claude-hq` without excluding `repos/`

**What goes wrong:** As of 2026-05-08, running `graphify --update` on `~/claude-hq` detects 2,158 changed files because `~/claude-hq/repos/` (cloned reference repos, gitignored) has accumulated 2,079 files since the last regen. Graphify doesn't natively respect `.gitignore`, so a naive update would burn ~60 subagents and 30+ minutes re-extracting reference material that isn't ours.

**Use instead:** wait for the BACKLOG item "graphify clean regen with `repos/` excluded" — needs either an exclude-config patch upstream or a wrapper script that mv's repos/ aside before invoking graphify.

**Don't run** `/graphify --update` on `~/claude-hq` until that exclude mechanism is in place. Single-directory invocations (e.g. `/graphify ~/claude-hq/commander`) are safe in the meantime.

---

## ❌ Auto-invoking automations / recipes / matchers without explicit user consent

**What's tempting:** When the system detects that a task matches a pre-built automation, just *run* the automation. Saves the user typing.

**Why it's wrong:** Lesson 17 (2026-04-24). Auto-invocation destroys measurement integrity (no control group), violates user expectations of explicit control, and creates a class of bugs where the automation runs on tasks that *kinda* match but shouldn't. The Goose recipes pilot was killed partly because the team that built them at AAIF had auto-invoke as the default — we explicitly inverted that to propose-and-confirm and the principle survived even though the recipes didn't.

**Use instead:** propose-and-confirm. Show the matched automation, explain the trigger, wait for explicit user yes/no. Auto-invoke only after a specific named automation has been explicitly opted into for auto-mode (rare, never the default).

**This applies forward-looking** to automations we haven't built yet — security-audit pipelines, full-stack initialisers, cleanup workflows.

---

## ❌ Pilots without deadline + signal + default action

**What's tempting:** Adopting a new tool, pattern, agent, or framework "to see if it helps" — implicitly assuming we'll evaluate later.

**Why it's wrong:** Lesson 20 (2026-05-06). The Goose recipes pilot ran for 12 days as "let's see how it goes" with no measurable signal and no default action — when we finally evaluated, no one had built the watchdog metric to even measure adoption. The pilot ran in *name only*. Cost: cognitive load + branch staleness + ambient feeling of "we have X" while X is dormant.

**Use instead:** every pilot ships with three explicit fields in the same proposal: **(a) hard deadline** (e.g., 14 days), **(b) measurable adoption signal** (file existence, command-usage count, watchdog metric, observable artefact), **(c) default action** when the deadline arrives if the signal is null (drop / globalise / promote / extend — pick one; "reassess" is not a default action).

If a proposal doesn't have all three, refuse to ship it.

---

## ❌ Backgrounded `mempalace mine` without `nohup` in session-end hook

**What we did:** The session-end hook originally did `mempalace mine "$PROJECT_DIR" > /dev/null 2>&1 &` — backgrounded with `&` only, no `nohup`.

**Why it caused problems:** When you close Terminal mid-session-end, the parent shell exits and sends SIGHUP to its job table. Without `nohup`, the backgrounded mine receives SIGHUP and dies mid-write to chroma's HNSW index → corrupted vector segments → next mine segfaults. This is exactly the 2026-05-08 incident shape.

**Use instead:** the hardened pattern from `~/.claude/hooks/session-end.sh` (post-2026-05-08): pre-mine integrity check via `mempalace-precheck.py` → atomic noclobber lockfile (`~/.mempalace/.mine.lock`) → `nohup` + `disown` so the mine survives parent exit. See `~/claude-hq/docs/mempalace-corruption-runbook.md` for the full incident write-up.

**Don't background long-running stateful writes without `nohup`** in any future hook.

---

## ❌ Reading config files that contain plaintext secrets via the `Read` tool

**What's tempting:** When debugging an MCP issue, read `claude_desktop_config.json` to inspect the configuration.

**Why it's wrong:** Lesson 14 (2026-04-22). On 2026-04-21, reading `claude_desktop_config.json` to diagnose a missing MCP surfaced four live API keys (Anthropic, Gemini, GitHub, Reddit) into tool output, which then flowed into the claude-mem observation database and into 8 local session transcripts before being caught. The local leak was scrubbable; the Anthropic-backend transcript leak was not.

**Use instead:** `security find-generic-password` for Keychain entries, `env | grep` for env vars, or scripts that touch secrets in-memory only and write to a secure store. Never route a known-plaintext-secret config through `Read`. Migration script for moving old plaintext configs to Keychain: `~/claude-hq/scripts/mcp-migrate-to-keychain.sh`.

---

## ❌ Inventing new vault folders / file naming conventions before checking existing taxonomy

**What's tempting:** When organising a new project in the Obsidian vault, propose a fresh top-level folder structure that "fits this project's nature."

**Why it's wrong:** Lesson 11 (2026-04-21). On 2026-04-21 I proposed creating a new `System/` top-level folder for claude-hq because it felt different from product projects. Sunil correctly pushed back: PATS-Copy already lived in `Projects/`, inventing a parallel hierarchy fragmented the taxonomy for a purely semantic reason.

**Use instead:** check `docs/ORGANIZATION.md` for the current taxonomy — `Projects/` for both products and infrastructure, with file-naming convention (`Hub.md` vs `00 Project Hub.md`) used to differentiate within. Extend, don't invent.

---

## ❌ Summarising / mirroring source files into the vault

**What's tempting:** When a vault page describes a system whose canonical docs live in a source repo, write a vault-native summary "for easy browsing in Obsidian."

**Why it's wrong:** Lesson 12 (2026-04-21). Summary copies always drift from source. The vault becomes a stale mirror that contradicts the actual code.

**Use instead:** symlink from the vault to the source file (`Commander/` → `~/claude-hq/commander/`, `01 PRD.md` → `~/Desktop/.../prd.md`). Bidirectional edits, zero drift, wikilinks resolve.
