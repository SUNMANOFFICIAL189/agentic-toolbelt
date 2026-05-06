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

## [Open] — 2026-05-06 — Wire weekly Telegram routing digest

**What:** Implement the weekly digest spec in `commander/MODEL_ROUTING.md` §8. Every Sunday 09:00 local: query `run/cost-ledger.sqlite` for last-7-days routing decisions, aggregate per project/tier/agent kind, format as a Lesson-16-compliant PlainAlert, send via existing `watchdog/telegram.py`.

**Why:** Phase 1 of the multi-model build shipped doctrine + routing hook + cost ledger, but the user-facing weekly visibility loop is not wired. Without it we have data but no proactive surfacing — defeats the "spot regressions early" intent that drove Q5.

**Estimate:** ~3–4 hours. Generator script, launchd plist, dry-run mode, jargon-linter validation.

**How to start:**
1. Wait until ~Sunday May 12 — by then we'll have ~7 days of real ledger rows to test against (today's data is mostly synthetic from the Phase 1 verification).
2. Read `watchdog/telegram.py` for the `PlainAlert` send pattern + jargon-linter behaviour.
3. Author `~/claude-hq/scripts/routing-digest.py`: queries ledger, aggregates, builds PlainAlert per the §8 template.
4. Add `~/Library/LaunchAgents/com.claude-hq.routing-digest.plist` for Sunday 09:00 trigger.
5. Run dry-run mode against current ledger, confirm output passes the linter.
6. Install launchd, verify on the next Sunday firing.

**Depends on:** ideally Watchdog Telegram listener fix (next item) so the digest's "reply 'details'" loop actually works. Without the listener, the digest still goes out — user just can't reply via Telegram. Acceptable degraded mode.

**Acceptance:** First Sunday digest lands in Telegram with no jargon-linter errors. Reading it tells the user something useful about the prior week's routing.

---

## [Open] — 2026-05-06 — Fix Watchdog Telegram listener (launchd path mismatch)

**What:** `com.claude-hq.watchdog.listener` plist references `listener.py` but launchd can't find it ("[Errno 2] No such file or directory" repeated in `listener.err.log`). The file exists; suspect a working-directory mismatch in the plist.

**Why:** Watchdog can still alert via email (verified — sent 2 reminder emails 2026-05-05). But the conversational layer — replying "show" or "why" or "details" to alerts in Telegram — is broken. Less urgent than the memory issue we already fixed today, but it's a real degradation. Affects future routing digest's reply flow.

**Estimate:** 30–45 min — diagnose + restart service.

**How to start:**
1. Read `watchdog/com.claude-hq.watchdog.listener.plist` — check `WorkingDirectory`, `ProgramArguments` paths, `EnvironmentVariables`.
2. Compare to where `listener.py` actually lives.
3. Either correct the plist path OR set `WorkingDirectory` to the watchdog dir.
4. `launchctl unload + load` to restart.
5. Verify by checking `listener.err.log` — errors should stop, listener should start polling Telegram.

**Acceptance:** No more "can't open file" errors in `listener.err.log`. Sending a Telegram message to the bot gets a routed response.

---

## [Open] — 2026-05-06 — Phase 2: cross-provider routing gateway

**What:** Decide between LiteLLM (BerriAI) and claude-code-router (musistudio) as the localhost proxy that lets the routing hook fall back to non-Anthropic providers (Gemini, Groq, Cerebras). Run as Docker container on `127.0.0.1:<port>`. Wire into the routing decision algorithm so when a tier is chosen, the actual call lands on the cheapest viable provider.

**Why:** Phase 1 captures within-Anthropic routing (Opus / Sonnet / Haiku). The full ~70–85% cost reduction comes from cross-provider — Gemini Flash for bulk summarisation is ~200× cheaper than Opus. Doctrine §13 already specifies the Trust Gate intersection; just need to pick the proxy.

**Estimate:** 1–2 days. Trust Gate Tier C evaluation of whichever proxy we pick, Docker pinning, key migration to Keychain (Lessons 14-15), routing hook integration.

**How to start:**
1. After ~30 days of cost-ledger data (~early June): query ledger to see the actual spend pattern. If Anthropic-only spend is low, this becomes lower priority. If high, high priority.
2. Re-evaluate LiteLLM vs claude-code-router: by then, claude-code-router's CVE-2025-57755 status, BerriAI's Trust Gate posture, and any new contenders in the space.
3. Run Trust Gate Tier C on the chosen proxy (Magika + secret-scan + Socket + reputation).
4. Pin Docker image SHA. Document in `commander/INCIDENT_LEDGER.md` if any vendor enters cooling-off during the eval.
5. Update `model-router.py` to consult provider chain after tier choice.
6. Update `MODEL_ROUTING.md` §13 with the chosen provider chain.

**Depends on:** ~30 days of Phase 1 cost-ledger data. Doctrine is already written.

**Acceptance:** A Haiku-class task routed by the hook actually lands on Gemini Flash via the gateway, observable in ledger. Cross-provider fallback works on 429.

---

## [Open] — 2026-05-06 — Phase 3: quality gate sample-and-grade

**What:** Implement the sampling spec in `MODEL_ROUTING.md` §9. 10% of cheap-tier outputs (Haiku, Gemini Flash post-Phase-2) get spot-graded by next tier up. Disagreement → escalate the whole batch + log `quality_escalated`. Persistent disagreement → surface as doctrine-revision suggestion in weekly digest.

**Why:** Without quality gate, silent regression risk: Gemini Flash returns garbage, Sonnet synthesis silently consumes garbage, output looks plausible. Catching this early via sampling is much cheaper than catching it after a delivered report turns out to be wrong.

**Estimate:** 2–3 days. Sampling logic in routing hook, grader prompt design, ledger schema extension, weekly-digest aggregation hook.

**How to start:**
1. After Phase 2 ships + ~30 days of mixed-tier ledger data.
2. Add `quality_grade` + `grader_model` columns to ledger (migration).
3. In routing hook: 10% sampling on Haiku/Flash dispatches; on completion, async-fire a grader call from the next tier up.
4. Define disagreement threshold (e.g., grader judges output as "would not approve in a code review" → escalate).
5. Extend weekly digest to surface "doctrine row X had >30% disagreement over 50 samples — consider re-mapping."

**Depends on:** Phase 2 shipped (so we have cross-provider data, not just Anthropic-only).

**Acceptance:** Ledger has `quality_grade` populated on ~10% of cheap-tier rows. Synthetic test where deliberately-wrong cheap output is escalated.

---

## [Open] — 2026-05-06 — Phase 4: quota-aware degradation

**What:** Implement the spec in `MODEL_ROUTING.md` §7. Monitor Anthropic Max 5-hour rolling window; when >80% consumed, degrade Sonnet→Haiku and Opus→Sonnet (skipping hard-floor agents). Send PlainAlert via Telegram. User reply "keep big" sets `HQ_QUOTA_AWARENESS=off` for the session.

**Why:** The 2026-04-28 quota incident (Paperclip Fleet on subscription mode + claude-mem CLI mining blew Max 5h window) is exactly what this prevents. We have the doctrine; we don't have the enforcement. Until we do, the next sustained-heavy session is a re-incident risk.

**Estimate:** 1 day. The monitoring source of truth is the unsolved part — see "How to start."

**How to start:**
1. Trigger: either after the next quota incident OR proactively before sustained heavy usage.
2. Identify monitoring source. Candidates: (a) `claude usage` CLI subcommand if exposed, (b) Claude Code's local usage telemetry files, (c) periodic Anthropic API ping with token-counting endpoint. Pick the one that's cheapest + most accurate.
3. Add a polling loop (cron / launchd / inline in routing hook) that updates `run/quota-state.json`.
4. Routing hook reads `quota-state.json`; if `>80% used`, applies degradation per §7.
5. Add PlainAlert template (already drafted in §7) — verify it passes the watchdog jargon linter.
6. Test: simulate >80% state, dispatch a Sonnet task, confirm it runs as Haiku.

**Acceptance:** A simulated >80%-consumed state causes the routing hook to degrade tiers, alert plain English, and respect "keep big" override.

---

## [Open] — 2026-05-06 — Move trust-gate test cases from /tmp into the repo

**What:** Today's session added test cases to `/tmp/test-trust-gate.sh` and `/tmp/test-trust-gate-post.sh` while fixing the eval bug (commits `7e45c3b`, `c6006ab`). Move them into `~/claude-hq/scripts/tests/` as committed regression tests.

**Why:** The /tmp files are ephemeral — next system reboot erases them. The trust-gate scripts are security-critical; we want regression tests that run on every change to those files. Both fixes today were caught by these tests; codifying them prevents the next regression.

**Estimate:** ~30 min — copy, parameterise paths, add a runner.

**How to start:**
1. `mkdir ~/claude-hq/scripts/tests/`
2. Move `test-trust-gate.sh` and `test-trust-gate-post.sh` from `/tmp/` to `scripts/tests/`.
3. Update HQ_ROOT references to use `${HQ_ROOT:-$HOME/claude-hq}`.
4. Add `scripts/tests/run-all.sh` that invokes both.
5. Optional: add a pre-commit hook that runs the tests if either trust-gate script changed.
6. Commit: `test(trust-gate): codify regression tests from 2026-05-06 fix`.

**Acceptance:** `scripts/tests/run-all.sh` exits 0 with all tests passing. Tests are checked into git.

---

## [Open] — 2026-05-06 — HQ root cleanup: orphan .rtf files + DB backup

**What:** Clean up four pre-existing untracked items in `~/claude-hq/` root that surfaced during today's `git status` review:
- `watchdog_commands.rtf`
- `watchdog_reminders.rtf`
- `watchdog_reminders_2.rtf`
- `watchdog/history.db.pre-migration-backup`

**Why:** The .rtf files look like personal scratch notes accidentally saved into the repo root. The `pre-migration-backup` is a stale DB dump from a past Watchdog migration. Neither should be tracked or even visible in git status. Clutter accumulates → real changes get lost in noise → eventually someone commits something they shouldn't.

**Estimate:** 5–10 min — triage decision per file.

**How to start:**
1. Open each .rtf — decide: (a) move to `~/Desktop/` if personal notes, (b) move into a proper docs file if useful, (c) delete if obsolete.
2. For `history.db.pre-migration-backup`: check `git log -p -- watchdog/history.db.pre-migration-backup` (it shouldn't appear; if it does, remove from history). Delete the file or move to `~/.archive/` if you want to keep the snapshot.
3. Add patterns to `.gitignore` if any class of file should never be tracked at root.
4. `git status` should be clean of these four after the pass.

**Acceptance:** `cd ~/claude-hq && git status` shows none of these four files.

---

## [Open] — 2026-05-06 — claude-mem upstream quirk: ChromaSync uses add not update

**What:** When claude-mem worker restarts after a crash and re-processes observations that were partially synced before the crash, the ChromaSync layer fails with "IDs already exist in collection" because it calls `chroma_add_documents` instead of `chroma_update_documents`. Observed during the 2026-05-06 paid-tier flip restart — obs IDs 653, 654, etc. tripped this on retry.

**Why:** Not blocking — SQLite primary store is fine, the worker continues with remaining batches. But the ChromaDB vector index ends up with stale-or-duplicate entries for any observations that span a restart. Affects semantic-search recall quality slightly. Will accumulate noise over time as claude-mem restarts happen.

**Estimate:** ~1 hour upstream. Either patch claude-mem locally or PR upstream.

**How to start:**
1. Locate the ChromaSync code in `~/.claude/plugins/cache/thedotmack/claude-mem/<version>/scripts/` — likely `worker-service.cjs` or a Chroma-specific module.
2. Find the `chroma_add_documents` call that produces this error.
3. Wrap with try-existing-then-update, or use `chroma_upsert_documents` if available.
4. Test by deliberately mid-flight crashing the worker on an observation, then restarting.

**Acceptance:** No "IDs already exist" errors after a restart with mid-flight observations. ChromaDB query returns clean unique vectors.

---

## [Open] — 2026-05-06 — claude-mem upstream quirk: parser cleans observation type from concepts array

**What:** Gemini occasionally includes an observation-type label (e.g. `discovery`) inside the structured `concepts` array of a generated observation. The parser logs `[PARSER] Removed observation type from concepts array` and silently strips it. Cosmetic but suggests prompt conditioning could be tightened upstream.

**Why:** Soft data-quality issue — concepts list is meant to be domain concepts, not observation-type metadata. Stripping is correct, but the log noise + the underlying prompt drift is worth a fix.

**Estimate:** ~30 min — review the prompt template that conditions Gemini, add a stronger negative example.

**How to start:**
1. Find the prompt template in claude-mem's plugin cache that conditions the Gemini observation-extraction call.
2. Add a negative example showing what NOT to put in the concepts array (specifically: "don't include observation type labels like discovery, decision, etc.").
3. Test with a session that previously triggered the warning.

**Acceptance:** No `Removed observation type from concepts array` warnings in claude-mem logs over 1 week of normal usage.

---

## [Open] — 2026-05-06 — Apify-equivalent capability for locked-down platform scraping

**What:** Today's Layer 0 stack (Crawl4AI + Jina + Exa + Puppeteer + Reddit MCP) handles public web pages well but cannot scrape **locked-down social platforms** — Twitter/X, Instagram, Facebook, LinkedIn, TikTok. These sites combine login walls, anti-bot challenges (Cloudflare, Arkose Labs, custom JS challenges), and IP/behaviour fingerprinting that defeats any local-Playwright-plus-LLM-extraction architecture. The gap is "Apify-class capability" — site-specific maintained scrapers running through rotating residential/datacenter/mobile proxies. ScrapeGraphAI was evaluated 2026-05-06 and ruled out (same fetch-and-parse architecture as Crawl4AI, hits the same walls).

**Why:** The gap is real but currently latent — Corporate Brains Phase 1 doesn't need locked-down social data (public sources cover competitor research). For any future project requiring Twitter sentiment, Instagram brand monitoring, LinkedIn employee/funding signals, Facebook page scraping, or TikTok content harvesting, we'd hit the wall. Documenting the three concrete paths now means future-Sunil doesn't redo the eval — just picks the right path for the use case.

**Estimate:** Open-ended — depends entirely on which path. Cheapest to costliest:
- **Pay Apify Actor per-platform** ($30–50/mo): trivial, no engineering work, cancel after use
- **Wire official APIs** (Twitter Basic $100/mo, YouTube free, Reddit free, LinkedIn very expensive): 1–2 hours per platform, sustainable but limited scope
- **Crawlee + self-hosted proxies** (Apify's own open-source actor framework, MIT): 1–2 weeks to set up + ongoing $5–15/GB residential proxy costs

**How to start (when triggered):**
1. **Trigger condition:** a real use case demands locked-down social-platform data that public sources cannot supply. Until then, do NOT pre-build per Lesson 20 — instrument the need first, build second.
2. When triggered: identify the specific platform(s) and the data volume (one-off vs. ongoing recurring).
3. Pick the path:
   - One-off / low volume / single platform → Apify Actor for that platform ($30–50/mo, cancel after)
   - Recurring need on Twitter / YouTube / Reddit only → official APIs (sustainable, ToS-clean)
   - Multi-platform recurring at scale → evaluate Crawlee + proxy infrastructure vs. ongoing Apify subscription
4. **Trust Gate considerations at adoption time:**
   - Apify (the company) — not currently allowlisted; review their security posture, postmortems, and Trust Gate Tier C
   - Crawlee — published by Apify under MIT; run through Tier C
   - `snscrape` / `Instaloader` / `facebook-scraper` — MIT, but fragile (break when platforms update); ToS-grey for some
5. Update `~/claude-hq/registry.json` with the chosen tool(s) at the appropriate Layer.

**Why ScrapeGraphAI was ruled out (so we don't re-evaluate it):** It fetches with local Playwright + extracts with an LLM. That's mechanically identical to Crawl4AI which we already have. Both hit the same walls on Twitter/Instagram/Facebook/LinkedIn — the bottleneck is *getting through the door* (proxies + site-specific Actors), not LLM extraction. Adding it would duplicate Crawl4AI under a different brand without bridging the gap.

**Acceptance:** When the trigger fires, the implementer picks a path from this entry without redoing the evaluation. The chosen path delivers the specific platform data needed for the specific use case, with an entry in registry.json, Trust Gate clearance, and (if recurring spend) a cost-ledger note.

---

## [Open] — 2026-05-06 — Gamma `slug_contains` returns garbage; lifecycle Strategy 3 unreliable

**What:** During PATS-Copy session-start health check on 2026-05-06, queried Gamma API with `slug_contains=hormuz` and got 20 unrelated markets back (Rihanna album, GTA-VI release, Stanley Cup, Harvey Weinstein sentencing — none containing "hormuz" in slug). Either the parameter is silently ignored or it's been deprecated. `position-lifecycle.ts:267` uses this exact parameter as Strategy 3 (broad text search fallback), then takes `markets[0]` as the result — meaning if Strategies 1 and 2 fail, lifecycle silently grabs an arbitrary market and checks ITS resolution status against our position. Currently low-impact because (a) most positions resolve via Strategy 1 (exact slug), and (b) the wrong market is usually `closed=false` so it's a no-op skip; but if the wrong market ever returns `closed=true`, lifecycle would close OUR position at THAT market's settlement price.

**Why:** Silent correctness bug. Mostly inert today, but a one-bad-luck-market away from a wrong-settlement close. Worth fixing or removing the fallback entirely.

**Estimate:** 30 min. Either drop Strategy 3 (preferred — Strategy 1+2 cover the real cases), or replace `slug_contains` with `?q=` if Gamma supports a real text-search parameter.

**How to start:**
1. Probe Gamma's documented parameters — `?q=`, `?slug_starts_with=`, `?text_search=` — to find one that actually filters.
2. If none works, delete Strategy 3 entirely from `position-lifecycle.ts:266-271`. The warn log "Could not find market" will fire instead, which is the correct behaviour.
3. Add a unit test that confirms `_gammaLookup('slug=non-existent')` returns null.

**Acceptance:** Either a working text-search parameter is wired in, or Strategy 3 is removed and Strategy 1/2 become the only paths. No silent wrong-market matches possible.

---

## [Open] — 2026-05-06 — MemPalace `mine` blocked from Claude Code subprocess

**What:** Running `mempalace mine .` from within a Claude Code session against `~/Desktop/POLYMARKET_TRADING_3.0` produces inconsistent failures: first attempt segfaults (exit 139), subsequent attempts return exit 0 silently with no `polymarket_trading_3.0` wing created in the palace. `mempalace status` works fine. `mempalace mine --dry-run` produces correct output. This blocked the same step in the previous session (2026-05-05) too — at that time attributed to TCC (macOS Transparency, Consent, Control) permission issues with the Terminal hosting Claude Code not having Full Disk Access.

**Why:** Memory-layer sync drift. Each blocked session means Phase 3.5 trade observations don't make it into the cross-session palace, weakening the next session's recall.

**Estimate:** 1–2 hours. Mostly diagnostic.

**How to start:**
1. Compare TCC permissions on the Terminal app vs. iTerm vs. Warp — whichever one is hosting Claude Code needs Full Disk Access to `~/.mempalace/palace/`.
2. Reproduce by running `mempalace mine ~/Desktop/POLYMARKET_TRADING_3.0` from a fresh native Terminal window outside Claude Code. If that works, confirms the harness is the issue.
3. Either grant Claude Code's host Terminal Full Disk Access, OR add a session-end hook that runs the mine via a launchd helper outside the harness.
4. Verify by checking `mempalace status` afterward shows the wing populated.

**Acceptance:** `mempalace status` shows a `polymarket_trading_3.0` wing with non-zero drawer counts after a session.

---

## Source

Captured 2026-04-22 during HQ activation conversation. User (Sunil) asked whether to install ruflo / seed / paul / TECCP into HQ. Conclusion was that adding more frameworks adds overhead without clear gain — these four actions are the higher-leverage alternatives. Full reasoning is in that session's transcript.

Items 5–11 added 2026-05-06 during the multi-model routing build session (Phase 0 + Phase 1 shipped, Trust Gate eval bug fixed). Items 5–9 are the Phase 2/3/4 + Watchdog listener + digest deferrals; items 10–11 are housekeeping found during the build.

Items 12–13 added 2026-05-06 after the claude-mem paid-tier flip exposed two upstream quirks during backlog drain. Both non-blocking.

Item 14 added 2026-05-06 after evaluating ScrapeGraphAI for HQ integration. Captures the Apify-class gap with three concrete paths so future-self doesn't redo the eval. ScrapeGraphAI itself was ruled out for HQ — see the entry's "Why ruled out" subsection.
