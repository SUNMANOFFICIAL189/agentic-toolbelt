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

## [Open] — 2026-05-07 — PATS-Copy: proportional sizing for copy-trader

**What:** Currently the copy-executor opens every copied position at a flat $20–$100 regardless of how much the leader put on. Leaders make money via asymmetric sizing — small probes ($50) when uncertain, big conviction bets ($5k–$20k) when sure. Their winning trades are large; their losing trades are small. Net positive. Flat-sized copying produces the leader's hit rate without the asymmetric upside, leading to net losses even on profitable leaders.

**Why:** Empirically demonstrated on 2026-05-07. Wallet `0x2005d16a...` has +$151k lifetime realized PnL on Polymarket. We copied 92 of their trades at flat sizing → our PnL on that subset: −$811 with 17.4% WR. Mean entry slippage was 0.32% (negligible). Stop-loss flushed only 4/92 trades. The remaining 88 closed naturally — same direction, similar entry, similar exit, but we lost $888. Conclusion: their edge is asymmetric sizing; flat sizing destroys it.

**Estimate:** 3–5 days. Real engineering work — touches risk-manager, copy-executor sizing logic, capital concentration safeguards.

**How to start (after convergence-copy is validated and shipped):**
1. Pull leader's recent bet-size distribution via `data-api.polymarket.com/positions?user=X` → for each position, `totalBought` / leader's portfolio value gives bet-as-fraction-of-portfolio
2. Add `our_size_factor` to copy-executor: `our_position = our_portfolio × leader_position_pct × scaling_factor`
3. Cap at risk-manager limits — never let any single copy exceed `MAX_POSITION_PCT` of our portfolio (e.g., 20%)
4. Backtest combined with convergence-copy filter: do convergence-confirmed + proportional-sized copies turn the strategy net-positive?
5. If validated, ship behind a feature flag (`PROPORTIONAL_SIZING=true`) so it's reversible

**Acceptance:** Backtest shows PnL improvement vs flat-sizing baseline of at least +$0.50/trade on the same 714 historical trades, with no single position exceeding `MAX_POSITION_PCT` of capital.

**Connection to other items:** Should ship AFTER convergence-copy (item below) is validated, because convergence-copy filters to higher-conviction trades and proportional sizing amplifies the captured edge. Together they're the two halves of "capture leader edge."

---

## [Open] — 2026-05-07 — PATS-Copy: convergence-copy filter (validate via backtest first)

**What:** Currently copy-executor copies any tracked leader's move when filters pass. Proposed: only copy when 2+ tracked leader wallets independently trade the same market in the same direction within a 30-min window — i.e., consensus among smart-money traders, not single-wallet noise.

**Why:** Wisdom-of-crowds principle — N independent skilled traders converging on a position is statistically a stronger signal than any single trader acting alone. Used in equity markets (13F filings consensus), crypto whale tracking. Should filter copy trades to high-conviction moments and avoid "probe" trades.

**Estimate:** Validation backtest 1 day; if validated, build 1–2 days. If not validated, abandon (Lesson 20).

**How to start:**
1. **Validation phase (1 day)** — replay our 714 historical copy_trades. For each, check if 2+ DIFFERENT leader wallets traded the same market within 30 min before our entry. Tag as "convergence-confirmed" vs "single-wallet". Compare PnL distributions.
2. Pre-committed test parameters (anti-overfit): 30-min window, 2+ distinct wallets, exact market match, same side direction.
3. **Independence check** — also measure time gaps between first-mover and second-mover. If consistently <60s → wallets are correlated (1 alpha + copytraders), not independent. Convergence isn't real signal in that case.
4. **If validated** — build convergence detector module that maintains rolling 30-min window of leader trades, fires "convergence" event when 2+ wallets align, copy-executor only acts on convergence events (not single-wallet events).
5. **If not validated** — drop the idea. Combine with proportional sizing as Phase 5 enhancement instead.

**Acceptance:** Convergence-confirmed copies show PnL > 0 across the historical sample, AND meaningfully better PnL/trade than single-wallet copies, AND wallets pass independence check (median gap > 5 min between first and second mover).

---

## [Open] — 2026-05-07 — Re-evaluate `uzucky/watchdog-ai` if it matures

**What:** [uzucky/watchdog-ai](https://github.com/uzucky/watchdog-ai) is a Python runtime verification framework with 6 check types (process, freshness, log_scan, assertion, http, script) that map closely to what we need for the architectural watchdog. Discovered during 2026-05-07 PATS-Copy session research. Not adopted because of Trust Gate concerns: 0 stars, 1 contributor, 1-month-old (created March 2026). Per Lessons 1-2, unproven solo-dev tools are high-risk for production trading bot monitoring.

**Why:** If the project gains traction (≥50 stars, ≥5 contributors, ≥6 months operating cleanly), it becomes a genuine candidate. Its 6 check types are well-designed for AI-built systems and could replace much of our custom rule-runner work. Saves us long-term maintenance if we adopt a maintained upstream rather than rolling our own.

**Estimate:** 1-2 hours re-evaluation when triggered. Trust Gate Tier C if adopted (Magika scan, secret scan, Socket dependency check, reputation review).

**How to start (when triggered):**
1. Re-check stars/contributors/release cadence at https://github.com/uzucky/watchdog-ai
2. If Trust Gate passes, prototype against 1-2 of our existing PATS-Copy watchdog rules — does it catch the same issues our custom rules do?
3. If it works, evaluate migrating from custom Python checks → watchdog-ai checks
4. Decision: keep custom (safer), migrate (less maintenance), or hybrid

**Trigger conditions to re-evaluate** (any one):
- watchdog-ai gains 50+ stars
- watchdog-ai has stable commit cadence > 6 months
- We're maintaining 10+ custom runtime rules and need a framework
- We're spawning 2+ project-native watchdogs and need shared tooling

**Acceptance:** Either we adopt watchdog-ai (replacing our custom Python scripts) and back-port any specific rules upstream, OR we document why it doesn't fit and stop revisiting.

---

## [Done] — 2026-05-08 — PATS-Copy: SELL-aware position sizing (max-loss cap, not just dollar cap)

**Resolved:** Two-part rule shipped at PATS-Copy commit `935d44f` (branch `fix/sell-aware-sizing` merged to `strategy/buy-optimization`):

1. **SELL entry-price floor at $0.05** (`MIN_SELL_ENTRY_PRICE`) — added to `signal-executor.ts` after the existing `MIN_SIGNAL_ENTRY_PRICE` check. Calibrated against 116 historical signal-bot SELLs: the ≤$0.05 bucket accumulated −$840 (driven by a single −$943 event) while $0.05–$0.10 bucket was +$104 with no large losses. Floor removes the catastrophic class while preserving the profitable mid-cheap one.

2. **5% max-loss-per-trade cap** (`MAX_LOSS_PCT_PER_TRADE`) — new `RiskManager.capByMaxLoss()` helper. Computes `max_loss_per_share = (1 − entry)` for SELL, `entry` for BUY. Reduces size if the would-be max-loss exceeds 5% of current balance; rejects entirely if reduction drops below $5 economic floor. Wired into both `signal-executor.ts` and `copy-executor.ts` as the final size step before execute.

**Backtest** against 156 historical signal-bot trades at $5,289 balance:
- Floor-rejected: 32 (avoid −$840 of historical losses)
- Cap-rejected: 0 (floor catches all catastrophic-class first)
- Size-reduced: 25 (small drag: +$16 → −$31 after scaling)
- Untouched: 99 (+$371 unchanged)
- Counterfactual outcome: −$452 → +$340 = **+$792 improvement**
- The 2026-05-07 −$943 BTC trade: FLOOR-REJECTED ✓

**Originally proposed cap was 1.5%; recalibrated to 5% during analysis.** User pushed back on the 1.5% cap as drastic for what looked like a "blue moon" event; the data showed that while catastrophic events ARE rare (1 in 50 cheap SELLs, ~2%), the strategy is still net-negative because each rare event wipes ~50 small wins. The right line was at the entry-price bucket, not at a portfolio-percentage. 5% serves as a backstop for outsized exposures in $0.05–$0.10 range without rejecting the profitable bucket entirely.

**Connection to other 2026-05-08 work:** Together with Phase C Signal v2 (BUY drop + SELL <24h cap) and the pnl-write reliability fix (commit 58d8257), the structural conditions that produced the −$943 event no longer exist in any layer — accounting accurate, sizing capped, position lifetime bounded. Phase G live-trading no longer blocked by this class of risk.

**Original entry (kept for audit trail):**

## [Open — historical] — 2026-05-07 — PATS-Copy: SELL-aware position sizing (max-loss cap, not just dollar cap)

**What:** Position sizer currently treats every trade as if max-loss = dollar amount committed. That is true for BUY (size = max-loss) but false for SELL (max-loss = (1 − entry_price) × shares = much larger when entry is low). On 2026-05-07 a $75 SELL at entry 0.041 carried up to $1,754 max-loss exposure and stopped out at −$943 in a single event — 12.5× the position dollar amount. Add a SELL-aware sizing rule that caps max-loss as a fraction of portfolio (e.g., MAX_LOSS_PCT_PER_TRADE = 1.5% of equity) and reduces size when entry price is low.

**Why:** Surfaced 2026-05-07 Phase A balance investigation. The −$943 single-trade loss accounts for ~97% of the −$976 PnL swing in 11h. Side-aware stop-loss fix (`ef206c1`) is correct but only kicks in at 30% adverse — by then a low-entry SELL has already lost multiples of its size. Pre-fix, this risk was hidden because stop-loss never fired on losing SELLs at all. Sizing-aware-of-side is the structural answer; tuning stop-loss thresholds alone can't fix asymmetric SELL risk.

**Estimate:** 2-3 days. Touches `risk-manager.ts` sizing logic + new MAX_LOSS_PCT config + tests + verification of sizing on actual signal-bot historical sample.

**How to start:**
1. Compute `max_loss_per_share = (1 − entry_price)` for SELL, `entry_price` for BUY.
2. Compute `max_position_loss = max_loss_per_share × shares`.
3. Add config `MAX_LOSS_PCT_PER_TRADE` (start 1.5%, tunable).
4. In sizing path: cap `our_size` so `max_position_loss ≤ MAX_LOSS_PCT_PER_TRADE × current_balance`.
5. Backtest against last 14 days of signal-bot SELL trades — does the cap reject the catastrophic sizes while letting normal trades through?
6. Watchdog Tier 1 rule (Phase B): static check for any code path that opens positions without computing max-loss.

**Acceptance:** No SELL position can be opened where `(1 − entry_price) × shares > 1.5% × balance`. Catastrophic loss class (>5% balance hit per single trade) becomes structurally impossible.

**Connection:** Independent of Signal v2 (Phase C) and proportional-sizing (item above) but should ship before either if sizing math is being touched anyway.

---

## [Done] — 2026-05-08 — PATS-Copy: Supabase pnl-write reliability (audit-trail gap)

**Resolved:** Code fix at PATS-Copy commit `58d8257` (branch `fix/pnl-write-reliability` merged to `strategy/buy-optimization`). Two compound bugs:
- `copy-executor.ts:548` — closePosition called paperEngine.closeTradeByMarketId regardless of whether the marketId was tracked in this.openCopyTrades. For signal-bot trades (owned by signalExecutor per c0e44b9), the trade closed in paperEngine but the function returned null. Added an early-return guard.
- `runner.ts:168` — lifecycle closePosition closure wasn't async-aware. `if (copy)` checked the Promise (always truthy), so signalExecutor branch was dead code. Added async + await.

**Backfill:** `~/claude-hq/watchdogs/pats/scripts/backfill_pnl_writes.py` ran on 2026-05-08. 46 suspect rows total; 2 recoverable from PM2 logs (BTC-80k −$943.04, US-Iran-war −$0.18), applied. 44 unrecoverable (pre-2026-05-06 logs rotated, or reconciliation-only closures with no log line). Per user 2026-05-08 decision: leave the 44 at pnl=0; code fix prevents new occurrences.

**Audit gap closed:** db sum(pnl) was +$158.14, after backfill: −$785.08. Bot's pre-restart in-memory pnl was −$767.15 → residual gap ~$18 (acceptable, attributable to the 44 unrecoverable rows).

**2026-05-08 update — Layer 3 follow-up shipped:** Fixed the secondary pnl=0 source at PATS-Copy commit `6ef3553` (branch `fix/reconciliation-pnl-truthful`). The 15-minute reconciliation routine was overwriting orphan rows with `pnl=0` when its market-cache lookup missed (cache misses happen for resolved markets, slug/condition_id mismatches, or fresh fetches). New three-layer fallback: (1) read pnl from `paperEngine.getClosedTrades()` first — handles the common case where bot hasn't restarted between close and reconciliation, (2) MarketCache lookup as before, (3) leave `pnl` as null (skip the column update entirely) and Telegram-alert the user to investigate. The historical 44 unrecoverable rows are unaffected; this prevents new ones from being created. After this fix, every pnl=0 row in the audit log is intentional history, not future drift.

**Original entry (kept for audit trail):**

**What:** Stop-loss closures sometimes don't write `pnl` back to Supabase — the row stays at `pnl=0` while the bot's in-memory state has the real loss. Sample of 30 low-priced SELL stops in last 7 days: 11 (37%) have `pnl=0` in db. Includes the 2026-05-07 −$943 BTC-80k trade. Bot's in-memory accounting is the truth (balance + .bot-status.json reflect real losses), but the audit trail in `copy_trades` is incomplete. All-time `sum(pnl)` from db = +$158 vs bot reports −$767 → $925 audit gap.

**Why:** Surfaced during 2026-05-07 Phase A. Three downstream effects: (1) reconstruction queries (e.g., this Phase A investigation) undercount losses and create false-positive "regression" signals; (2) dashboard PnL is wrong because it reads db; (3) any future hydration-from-Supabase will mis-restore balance after restart — the bot only computes correct balance now because it had the right state in-memory. A fresh restart-from-cold could reload at the wrong balance.

**Estimate:** 1-2 days. Investigate which close path skips the pnl write (likely reconciliation orphan-close vs primary-path closure), add pnl to those writes, backfill the existing 11 known-bad rows.

**How to start:**
1. Diff the three close paths: `closeTrade` (paper-trading.ts:145), `closeTradeByMarketId` (paper-trading.ts:176), reconciliation orphan-close (somewhere in runner.ts or a reconciler).
2. Find which path doesn't call `updateCopyTrade({pnl})` or where the pnl arg is missing.
3. Fix the missing write.
4. Backfill: write a one-shot script that pulls in-memory closedTrades from a recent bot status snapshot (or recomputes from entry/exit price + size) and updates the 11 rows with correct pnl.
5. Watchdog Tier 1 rule (Phase B): runtime check that flags any `copy_trades.status='stopped'` row with `pnl=0` and `our_size > 0` (impossible state — a stop-loss closure should always have a non-zero pnl).

**Acceptance:** No new `status=stopped` rows with `pnl=0` after fix deploys. Existing 11 rows backfilled. Bot's in-memory PnL matches `sum(pnl)` from db within $5 tolerance.

**Connection:** Pairs naturally with the sizing item above — together they're "make the SELL accounting trustworthy." Watchdog runtime rule from this item directly supports Phase B step 3.

---

## [Open] — 2026-05-08 — Memory probe adoption metric in HQ Watchdog

**What:** Wire two new metrics into `~/claude-hq/watchdog/metrics.yaml`:
1. `memory_probe_invocations_per_session` — count of times `memory-probe.sh` is run per session.
2. `tasks_starting_without_probe` — sessions where I started non-trivial work without first running the probe (heuristic: substantial code/file edits in the first N tool calls without a preceding probe).

**Why:** Lesson 21 (added 2026-05-08) tells me to probe memory before non-trivial work. Without a measurement layer per Lesson 20, this becomes another un-instrumented behavioural rule that can silently drift to "memory of behaviour" rather than actual behaviour. The watchdog is the natural home for adoption signals.

**Estimate:** 1-2 hours. Most of the work is the heuristic for "task started without probe" — needs a sliding window over the session's first 5-10 tool calls and a check for memory-probe.sh invocation.

**How to start:**
1. Add the two metric definitions to `metrics.yaml` with `plain_language` blocks per Lesson 16.
2. Implement the detection in `watchdog/listener.py` or a metric-specific module.
3. Calibrate thresholds after 7 days of data — what's a "normal" probe rate?
4. After 14 days: if the probe rate is too low, surface as a Telegram nudge ("you've started 5 non-trivial tasks today without probing memory — check Lesson 21").

**Acceptance:** Two metrics in `metrics.yaml` with plain-language blocks. Watchdog logs invocations. After 14 days of soak: a baseline number we can use to flag drift.

**Connection:** Lesson 21 is the doctrine; this is the measurement. Without this, the lesson is half a system per Lesson 20.

---

## [Open] — 2026-05-08 — graphify clean regen with `repos/` excluded

**What:** The vault's `Projects/claude-hq/Graph/` was last regenerated 2026-04-21. As of today, `graphify --update` detects 2,158 changed files — but **2,079 of those are inside `~/claude-hq/repos/`** (cloned reference repos that have accumulated since April, not our source). A naive full re-extraction would burn ~60 subagents and 30+ minutes processing material that isn't ours and shouldn't be in our knowledge graph.

**Why:** The graphify skill doesn't natively respect `.gitignore`, even though `repos/` is gitignored. So re-extraction picks up the cloned trees alongside our actual source. We need either (a) a graphify config that excludes `repos/` or (b) a temporary mv-out / mv-back wrapper.

**Estimate:** 1-2 hours. Most of the work is finding / writing the exclude mechanism and validating the resulting graph still has good cross-area connections (commander ↔ watchdog ↔ scripts ↔ patches).

**How to start:**
1. Check graphify's actual file-walk code to see if `--exclude` or `.graphifyignore` exists; if not, propose upstream patch.
2. Alternative: write a wrapper script `~/claude-hq/scripts/graphify-update.sh` that temporarily renames `repos/` → `repos-snapshot/`, runs `/graphify --update --obsidian --obsidian-dir <vault path>`, renames back.
3. Run a clean regen producing `Projects/claude-hq/Graph/` in vault.
4. Commit vault + push.

**Acceptance:** A `graphify --update` invocation that produces a fresh graph covering only HQ source (commander, watchdogs, scripts, patches, docs, agents, tools) without re-extracting `repos/`. Total file count after exclude should be <120, not 2,158.

**Connection:** Hub.md and Decision Log narrative already cover the 2026-05-08 work for human readers — graphify is a nice-to-have visualisation, not blocking. Scheduled regen rather than session-end snapshot per Lesson 20 (don't ship un-instrumented work).

---

## [Open] — 2026-05-08 — Paperclip watchdog: deferred runtime rules (Phase 2)

**What:** Three rules deferred from the Tier 1 Paperclip watchdog build because they need API surface verification + soak data for calibration:
1. `stale_heartbeat.py` — agent that should have woken in last X minutes hasn't.
2. `failed_run_rate.py` — high failure percentage across runs in a window (warn at >20%, critical at >50%).
3. `stuck_queued_runs.py` — runs queued but not executing for >30 minutes.

**Why:** Tier 1 shipped 4 rules calibrated against the 2026-04-28 quota incident (server health, HC.io relay, token burn rate, agent quota threshold). The 3 above need: (a) Paperclip's `/agents/:id/runtime-state` and `/issues/:id/runs` response shapes mapped end-to-end, (b) a soak window of real Paperclip activity to know what "normal" looks like for stale-thresholds and failure-rate baselines. Shipping uncalibrated would mean alert noise on day one.

**Estimate:** 1 day. Most of the work is calibration during the 14-day soak (2026-05-08 → 2026-05-22), then writing the rules in the same shape as the existing four.

**How to start:**
1. After 2026-05-22 soak end: review `~/claude-hq/watchdogs/paperclip/audit.log` for what real Paperclip activity looks like.
2. For stale_heartbeat: pick a stale-window threshold (likely 2× the agent's configured heartbeat interval).
3. For failed_run_rate: confirm the failure-rate baseline from soak data, set warn at 2× normal, critical at 4×.
4. For stuck_queued_runs: confirm Paperclip's existing stale-run cancellation timeout in `heartbeat.ts`, set the watchdog threshold below it so we alert *before* Paperclip auto-cancels.
5. Write each rule following the pattern in `~/claude-hq/watchdogs/paperclip/rules/runtime/server_health.py`.

**Acceptance:** Three new rules in `rules/runtime/`, each tested with `--once-stdout`, plain-English findings, audit-log entries. Soak window for the new rules: 7 days each (shorter than initial soak because the orchestrator pattern is already proven).

---

## [Done] — 2026-05-08 — Paperclip dedicated watchdog (Tier 1)

**What:** Built `~/claude-hq/watchdogs/paperclip/` as the second tenant of the watchdogs framework (PATS was first). Four runtime rules: server_health, healthchecks_io_relay, token_burn_rate, agent_quota_threshold. Soak mode default for 14 days (ends 2026-05-22). launchd plist included but NOT auto-loaded — operator installs manually.

**Why:** The 2026-04-28 quota incident proved Paperclip needs per-project monitoring beyond its built-in `/health` and stale-run cleanup. Mirrors the dedicated PATS watchdog pattern. Replaces the manual `~/claude-hq/scripts/paperclip-burn-tracker.py` script (which stays as a one-off CLI tool but isn't on a timer).

**Resolution:** Files: `orchestrator.py`, 4 runtime rule scripts, `lib/{finding,alerts,paperclip_api}.py`, `com.claude-hq.paperclip-watchdog.plist`, README. Reminder set in `watchdog/reminders.json` for 2026-05-22 soak end. Telegram alerts prefixed `[Paperclip]` to distinguish from PATS.

**Healthchecks.io setup:** ✅ Done 2026-05-08. Two checks created in user's existing HC.io account: `paperclip-server` and `paperclip-watchdog`. URLs in `~/claude-hq/watchdog/healthchecks-urls.env`. Initial ping confirmed (HTTP 200 from both endpoints). Note: `_ping()` now uses certifi's CA bundle because macOS system Python doesn't link the SSL bundle by default — fix applied in `rules/runtime/healthchecks_io_relay.py`.

**Connection:** Tier 1 only — detect + alert, no auto-fix. Tier 2-4 deferred per the existing project-watchdog framework.

---

## [Open] — 2026-05-08 — Trust Gate: npm-registry-aware author resolution for bare packages

**What:** When a `npm install <pkg>` command is run with a bare package name (e.g. `npm install ethers@^6`, no `@scope/`), the Trust Gate's `extract_owner()` returns empty because there's no slash. The package always falls into UNKNOWN AUTHOR, even for trusted maintainers (e.g. ethers maintained by `ricmoo` / `ethers-io` org). This forces `HQ_TRUST_OVERRIDE=1` for legitimate installs every time.

**Why:** The npm registry `/{pkg}` endpoint returns repository URL + maintainer list as authoritative metadata. We can resolve `ethers@^6` → `github.com/ethers-io/ethers.js` → owner `ethers-io` and check that against the existing allowlist. Same flow as the GitHub URL parse, just one HTTP indirection.

**How:**
1. In `scripts/lib/advisory-check.sh`, add `resolve_npm_owner()`: cheap `curl https://registry.npmjs.org/{pkg}` (with timeout), parse `repository.url` field, run through existing `extract_owner` regex to pull github org.
2. Cache results to `/tmp/trust-gate-npm-cache.json` keyed by pkg name (TTL 24h) so we don't hit npm registry on every install.
3. If the registry resolution fails (network, 404, malformed), fall through to current UNKNOWN behavior — no regression.
4. Update `commander/TRUST_GATE.md` Layer 0.5 docs.

**Acceptance:** `npm install ethers@^6` auto-passes via the existing `ethers-io` allowlist entry (added 2026-05-08 for PATS Branch 2). `npm install some-typosquat` still falls into UNKNOWN as today. Cache invalidates correctly when a package's repository URL changes.

**Estimate:** 1–2 hours. Mostly bash + curl + jq.

**Source:** 2026-05-08 PATS-Copy Branch 2 build — needed `ethers@^6` for Polygon WS monitor, hit UNKNOWN AUTHOR despite ethers being one of the most-installed Ethereum libraries. Added `ethers-io` and `Polymarket` to the allowlist for git-clone path coverage but the npm-bare-package flow still requires registry-lookup to benefit.

---

## [Open] — 2026-05-09 — PATS-Copy: Branch 3 — geopolitics pipeline on Option D (replaces obsolete env-flag variant)

**What:** Implement Branch 3 (geopolitics copy revival) as a third pipeline on the post-Option-D architecture. Same wallet list (12 geopolitics leaders from convergence backtest), same edge thesis (+$168.79/trade per multi-category backtest), but as a first-class pipeline with its own `RiskManager`, capital pool, position cap, and risk gates — NOT as an env-flag-on-shared-bot retrofit.

**Why:** The original master-handoff Branch 3 design (`COPY_GEOPOLITICS_ENABLED=true`, `COPY_GEOPOLITICS_WALLETS=...`, ~30 min of work) is obsolete after the 2026-05-09 Option D architecture decision. Landing it on the shared-state design would re-create the cross-pipeline contagion problem Option D was designed to solve. The geopolitics edge (+$168.79/trade) is real and worth pursuing, but only on the better foundation. See Decision Log entry "Architecture decision: Option D" (2026-05-09).

**How:**
1. Pre-req: Option D refactor complete (BACKLOG entry above).
2. Add `geopolitics` as a pipeline ID in the post-Option-D `Map<PipelineId, RiskManager>`.
3. Capital allocation env var: `GEOPOLITICS_CAPITAL=<N>` (sum of all pipeline capitals ≤ `TOTAL_CAPITAL_USDC`).
4. Build `GeopoliticsPipeline` (or extend `CopyExecutor` with a pipeline-aware filter):
   - Watch the 12 wallets from the convergence backtest (list in master handoff)
   - Filter to geopolitics-category markets only (use existing `market-categoriser.ts` `categoriseMarket()` function)
   - Trade only when both wallet AND category match
5. Watchdog: add `geopolitics-cumulative-pnl` rule (the 5th rule from the master handoff Phase 5 list, deferred to here).
6. Paper-mode validation soak: ≥30 days with the pipeline running on paper, hitting the live-readiness combined bar (WR ≥55%, no single-day drawdown >10%, cumulative P&L positive).

**Acceptance:**
- Pipeline trades only when (wallet ∈ 12 geopolitics leaders) AND (market category == 'geopolitics')
- Per-pipeline P&L queryable via Supabase `pipeline='geopolitics'` filter
- Geopolitics pipeline's loss does NOT reduce signal-bot's drawdown headroom (Option D guarantee)
- Watchdog `geopolitics-cumulative-pnl` rule emits findings if rolling-7d P&L drops below a configured floor

**Estimate:** 1-2 days dev + 30 days paper soak (in parallel with Phase 4b Polymarket live ramp on signal-bot).

**Sequencing:** AFTER Option D refactor. BEFORE Phase 4b live trading goes wide (geopolitics paper soak runs concurrently with signal-bot's live test on Polymarket — they're independent gates).

**Source:** 2026-05-09 conversation — user asked to confirm Branch 3 status. Original env-flag plan superseded by Option D. Reframed plan documented and confirmed.

**Empirical priority anchor (added 2026-05-10):** Forensic on the March→April WR collapse + 30-day P&L data shows the bot's profitable era (March 2026: +$1,008 across 215 trades, 44.2% WR) was 100% from copy pipeline. Signal-bot solo is structurally break-even. Branch 3 is therefore the highest-priority profit lever — the structural path back to March-level monthly profits, not a side-experiment.

**Mandatory feature (NOT optional):** Branch 3 must mirror leaders' position size *relative to their typical* (their conviction signal), not absolute. Flat-copying is what destroyed April 2026 — leader `0x2005d16a` (lifetime +$151k PnL on Polymarket, asymmetric-edge sizing) ramped to 42 trades on 2026-04-07 and our flat-size copy lost −$470 on that wallet alone. Without proportional sizing, Branch 3 will reproduce April's loss pattern even with the F-series fixes in place.

**Full empirical justification:** Vault Decision Log entry "2026-05-10 — Forensic: March → April WR collapse + the case for restoring copy pipeline".

---

## [Open] — 2026-05-09 — PATS-Copy: Phase 4b — Polymarket live trading (signal-bot first)

**What:** Enable real-money execution on Polymarket CLOB for the signal-bot pipeline (most-validated pipeline). Add a Polymarket execution path alongside the always-running PaperEngine. Other pipelines (copy-bot, geopolitics) stay paper-only initially. Per-pipeline opt-in via `<pipeline>_LIVE_TRADING=true` env vars.

**Why:** Signal-bot has the most production track record (live since 2026-04-28, profitable +$287 across 55 trades pre-Phase-C, currently in Phase C with BUY disabled and SELL <24h-cap). The next step toward real revenue is moving signal-bot from paper to live with a small bankroll. Keep paper engine running as the always-on baseline for slippage/fee measurement (per Mission Board's dual-mode-parallel-execution architecture).

**How:**
1. Pre-req: Option D refactor complete + Branch 3 implemented (so per-pipeline live flags actually work).
2. Build Polymarket live-execution path:
   - CLOB order placement via `py-clob-client` or equivalent TS client
   - Authentication / API key / proxy wallet setup
   - Order types: limit orders only (no market orders for safety)
   - Fill tracking and reconciliation against Polymarket API
3. Per-pipeline opt-in env vars: `SIGNAL_LIVE_TRADING=true`, `COPY_LIVE_TRADING=false`, `GEOPOLITICS_LIVE_TRADING=false`.
4. Bankroll: $500 to start (Mission Board recommendation), separate Polymarket account from paper-tracked balance.
5. Paper engine continues running for ALL pipelines as baseline / control group — every live trade has a paper twin for slippage/fee measurement.
6. Watchdog rules: add `live-vs-paper-divergence` (alert if live fill price differs from paper expected fill by >X%), `live-execution-failure` (alert if live order placement fails), `polymarket-api-health` (alert on persistent CLOB API errors).
7. Daily reconciliation: live position book vs paper position book vs Supabase. Find drift early.

**Acceptance:**
- Signal-bot trades placed on real Polymarket against the $500 bankroll
- Paper engine continues to run with the same signals for direct slippage/fee comparison
- For ≥30 days: WR stays ≥55%, no single-day drawdown >10%, cumulative live P&L positive
- Daily reconciliation passes (live ↔ paper ↔ Supabase all match within $5 drift)
- After 30 days clean, this pipeline is eligible for the dYdX gate (Phase 4c)

**Estimate:** 3-5 days dev (CLOB execution path is non-trivial), then 30+ days observation.

**Sequencing:** AFTER Branch 3 (so all three pipelines exist on Option D). BEFORE Phase 4c (dYdX). Other pipelines (copy, geopolitics) stay paper-only during this phase — they go through their own Phase 4b later, on their own timeline, after they pass the live-readiness combined bar in paper.

**Risks to flag during implementation:**
- Polymarket CLOB has thin liquidity on long-tail markets — slippage on paper vs live can be material. Worth running a 1-week pre-flight where signals fire but DON'T execute live, just log "would have placed order at $X, current bid/ask is $Y/$Z" to estimate slippage.
- Real-money orders need explicit kill switches — add a `LIVE_TRADING_KILL_SWITCH` env that, when set, immediately cancels open orders and stops new placements. Wire to a manual command + watchdog auto-trigger.

**Source:** 2026-05-09 conversation — confirmed sequencing with Sunil. Combined-bar live gate + per-pipeline opt-in.

---

## [Open] — 2026-05-09 — PATS-Copy: Phase 4c-d — dYdX directional-mirror integration (post-Polymarket-live)

**What:** Add dYdX as a third execution venue (alongside paper + Polymarket live), per-pipeline opt-in. Use dYdX perpetual contracts to **mirror Polymarket trade direction with leverage** on the subset of Polymarket markets that have a dYdX analog. Phase 4c is the foundation (build path, validate at 2x leverage, minimum positions). Phase 4d is scale-up (increase position sizes and leverage once verified).

**Why:** dYdX perpetual contracts can amplify returns on directionally-correlated trades (e.g., Polymarket "Bitcoin above $78k by EOD" maps to dYdX BTC-PERP LONG). 2-20x leverage on the same conviction signal compounds the strategy's edge. Mission Board has the original architecture sketch from 2026-04 era; this entry consolidates and extends it to fit Option D + post-Branch-3 reality.

**Confirmed direction (2026-05-09):**
- **Use case: directional mirror with leverage** (NOT hedging, NOT standalone strategy). Same direction as Polymarket trade, leveraged 2-5x at start, on dYdX perpetual when an analog market exists.
- **Live gate (per-pipeline combined bar):** WR ≥55% sustained 30 days AND no single-day drawdown >10% AND cumulative P&L positive AND ≥1 month after that pipeline went Phase-4b live on Polymarket.
- **Sequencing:** AFTER Phase 4b (signal-bot Polymarket live). Each pipeline graduates independently to dYdX once it passes the gate.

**Identified gaps the Mission Board doesn't address (must solve in Phase 4c):**

1. **Market-mapping layer.** Most Polymarket markets have NO dYdX analog. Need a deterministic mapper:
   - Input: Polymarket slug (e.g. `bitcoin-above-78k-on`)
   - Output: dYdX market id (e.g. `BTC-USD`) + directional translation (Polymarket "BUY YES" = dYdX "LONG") + size translation
   - For markets with no analog: skip dYdX, Polymarket-only execution
   - Maintain mapping config in `dydx-market-map.json` with manual curation (high-confidence mappings only)

2. **Position-sizing math.** Polymarket "$75 size at $0.92" is NOT directly equivalent to "$75 notional on dYdX at 2x leverage."
   - Polymarket position has finite floor (-$X if NO resolves)
   - dYdX position has continuous mark-to-market and liquidation risk
   - Need a sizing rule: "match expected dollar P/L on a 1% adverse move" or similar
   - Document the math, validate against historical data before going live

3. **Funding rate accounting.** dYdX charges/pays funding every 8 hours.
   - For multi-day Polymarket positions (e.g. monthly markets), funding can accumulate to material % of position
   - Decision: cap dYdX hold duration to ≤24h (only mirror short-duration Polymarket positions)? Or track funding as a separate cost component?
   - Recommend: cap hold duration to match Polymarket position's expected hold, with a hard 7-day max.

4. **Per-pipeline subaccount strategy.** dYdX V4 has subaccounts.
   - Recommend: per-pipeline subaccount on dYdX (signal-bot subaccount, copy-bot subaccount, geopolitics subaccount). Matches Option D's capital-pool isolation.
   - Each subaccount has its own margin pool, position limits, P&L tracking.
   - dYdX SDK supports multi-subaccount; cleaner accounting.

5. **Liquidation safety.** Even at 2x, dYdX positions can liquidate on sharp moves.
   - Add `MAX_LEVERAGE_PER_PIPELINE` config (start: 2x for all, raise to 5x after 30 days clean, never above 10x)
   - Add a `dydxMarginBuffer` rule in RiskManager — never deploy more than 80% of subaccount equity to position margin
   - Watchdog rule: alert if any subaccount equity drops below the maintenance margin floor

**How (Phase 4c — foundation, 5-7 days dev + 30 days paper soak):**
1. Build dYdX execution path: REST + WebSocket SDK (Python or TS — dYdX V4 has good support for both)
2. Per-pipeline subaccount creation + funding (dYdX testnet first, mainnet after dev complete)
3. Build market-mapping layer (`dydx-market-map.json`)
4. Build sizing-translation logic (Polymarket size → dYdX notional)
5. Build position-management module (open / close / monitor / forced-close on liquidation risk)
6. Wire ExecutionRouter: signal → paper (always) + Polymarket live (if pipeline LIVE flag) + dYdX (if pipeline DYDX_ENABLED flag AND market has analog)
7. Per-pipeline env vars: `<pipeline>_DYDX_ENABLED=true`, `<pipeline>_DYDX_LEVERAGE=2`, `<pipeline>_DYDX_MAX_POSITION=100`
8. Watchdog rules: `dydx-funding-rate-spike` (alert on unusual funding), `dydx-margin-buffer-low` (alert <80% buffer), `dydx-liquidation-risk` (alert if position margin <120% maintenance), `dydx-vs-polymarket-price-drift` (alert if dYdX market price diverges from Polymarket by >X%)
9. Phase 4c starts on testnet, then minimum-position mainnet (e.g. $50 notional at 2x = $100 effective per trade)

**How (Phase 4d — scale, runs continuously after 4c proves out):**
1. After 30 days clean on Phase 4c (WR maintained, no liquidations, no funding-rate surprises), increase position sizes on a schedule (2x notional every 14 days)
2. Leverage stays at 2x until 90 days clean, then 3x, then re-evaluate
3. Cap on increase: don't exceed `<pipeline>_DYDX_MAX_ALLOCATION` of pipeline's total capital
4. Each leverage step is its own decision gate, NOT automatic

**Acceptance (Phase 4c):**
- dYdX execution path lives and tested on testnet
- Market-mapping layer covers ≥80% of price-of-asset Polymarket markets that signal-bot trades
- Per-pipeline subaccounts open and funded
- 30 days mainnet at minimum positions (2x leverage, $50 notional) without: liquidation event, funding-rate surprise >2% of position, dYdX-vs-Polymarket price drift >5%, or watchdog alert escalation
- Live P&L tracking integrated into bot status + Supabase

**Acceptance (Phase 4d):**
- Each scale-up step (2x → 4x notional, etc.) requires: prior 14 days clean + manual user confirmation. Not automatic.
- Pipeline never exceeds `<pipeline>_DYDX_MAX_ALLOCATION` of its total capital pool

**Estimate:** Phase 4c = 5-7 days dev + 30 days observation. Phase 4d = ongoing, no fixed end.

**Sequencing:** AFTER Phase 4b for any given pipeline. signal-bot likely first to hit dYdX (most-validated). copy-bot and geopolitics follow on their own timelines.

**Source:** 2026-05-09 conversation — Mission Board's original Phase 4c-d plan retrieved, gaps identified (market-mapping, sizing math, funding rates, subaccount strategy, liquidation safety), reframed for Option D + per-pipeline architecture. User confirmed: directional mirror, combined-bar gate, post-Polymarket-live sequencing.

---

## [Open] — 2026-05-09 — PATS-Copy: per-pipeline RiskManager + capital pools (Option D refactor)

**What:** Refactor the bot from one shared `RiskManager` (single balance, single drawdown breaker, single position cap, single max-loss cap) to per-pipeline `RiskManager` instances (one each for signal, copy, future Branch 3 geopolitics). Each pipeline gets a fixed capital allocation from total $6,300 (e.g. signal $4000, copy $2000, reserve $300). Single Node process, single pm2, single watchdog — but isolated capital pools and risk gates per pipeline.

**Why:** Verified 2026-05-09 by direct code inspection (`risk-manager.ts:23-35`, `runner.ts:144`, `position-lifecycle.ts`): `paperEngine` + `riskManager` are single instances shared by both `signalExecutor` and `copyExecutor`. The `MAX_OPEN_POSITIONS` cap, drawdown breaker, max-loss cap, balance, and peakBalance are all *shared state*. The 2026-05-07 −$943 SELL incident drained the shared balance, reducing risk gates that copy pipeline would have computed against — bad outcomes propagate across uncorrelated strategies, the opposite of why you run multiple strategies. The Branch 3 master-handoff plan (env-flag-on-shared-bot) would land on this same flawed foundation. Splitting now means Branch 3 (and any future strategy) plugs in cleanly.

**Why not full split (separate Hetzner / separate pm2 / separate repo):** Operationally expensive (2x infra, 2x watchdog, 2x heartbeat, 2x debugging surface) for diminishing returns. In-process pipeline isolation captures the value (capital + risk separation, independent tuning, trivial attribution) without the operational tax. This matches how multi-strategy hedge funds actually run: isolated capital pools, shared infrastructure.

**How:**
1. `RiskManager` constructor takes `(pipelineId, capital, riskDial, opts)`. State stays per-instance.
2. `Runner` holds `Map<PipelineId, RiskManager>` instead of `private riskManager: RiskManager`.
3. Each executor (`signalExecutor`, `copyExecutor`) receives its own `RiskManager` via constructor, not the shared one.
4. Capital allocation at startup from env vars: `SIGNAL_CAPITAL`, `COPY_CAPITAL`, `RESERVE_CAPITAL` (sum ≤ `TOTAL_CAPITAL_USDC`).
5. Supabase: add `pipeline` column to `copy_trades`, default backfill `leader_wallet === 'signal-bot' ? 'signal' : 'copy'`.
6. Position cap becomes per-pipeline (e.g. signal cap=3, copy cap=2). `maxOpenPositions` config moves under `risk.<pipeline>` namespace.
7. Drawdown breaker becomes per-pipeline. peakBalance persistence file gets a per-pipeline JSON structure.
8. STATUS log shows a row per pipeline.
9. Watchdog rules become pipeline-aware. The existing `low_priced_sell_max_loss` rule already groups by `leader_wallet` so it's halfway there — needs a pipeline column read.
10. Branch 3 (geopolitics copy revival) plugs in as a third pipeline (or as a sub-mode of the copy pipeline with its own RiskManager).

**Acceptance:** A −$1000 loss on the signal pipeline does NOT reduce the copy pipeline's available capital, drawdown headroom, or max-loss-dollar cap. Per-pipeline P&L is queryable directly from Supabase via the `pipeline` column without `leader_wallet` string filtering. The bot survives a 30-min stress test where one pipeline is forced to trade aggressively while the other remains healthy.

**Estimate:** 1–2 days focused work, plus a 24h paper-mode validation soak before live.

**Sequencing:** Do AFTER Phase 6 verdict on Branch 2 (don't refactor concurrently with shadow validation). Do BEFORE Branch 3 build (so Branch 3 lands on the better foundation, not retrofitted onto shared).

**Source:** 2026-05-09 conversation during Branch 2 deploy. User asked whether signal + copy should run as separate entities or share state. CTDD verification confirmed shared design is the architectural shape today (see Decision Log entry "Architecture decision — Option D: per-pipeline RiskManager + capital pools" in `JARVIS-BRAIN/Projects/PATS-Copy/04 Decision Log.md`). User preference confirmed for Option D.

---

## [Open] — 2026-05-09 — Re-evaluate GitNexus + Composio if specific gaps surface

**What:** Two HQ integration candidates evaluated 2026-05-09 and skipped. Park here so future-self can revisit without re-deriving the analysis. Full evaluation memory: `~/.claude/projects/-Users-sunil-rajput/memory/reference_gitnexus_composio_eval_2026_05_09.md`.

**Why skipped:**
- **GitNexus** (https://github.com/abhigyanpatwari/GitNexus) — ~80% of its 16 MCP tools duplicate code-review-graph already wired into HQ. PolyForm Noncommercial 1.0.0 licence permits use only "without any anticipated commercial application," which technically blocks application across PATS-Copy, Artist Video Tool, Wasserman, Corporate Brains. Two genuinely-new features (multi-repo group analysis, auto-generated per-repo skills via community detection) but no current pain point demanding them.
- **Composio** (https://docs.composio.dev) — Hosted credential broker. Direct violation of Lessons 14 + 15 (API keys, OAuth tokens live in macOS Keychain via local launchers, never on third-party servers). No SOC-2 / data-handling disclosure below enterprise tier. Free tier 20k calls/month exists but any HQ project crossing that line hits $29/month and a COST_CONTROL.md Tier 4 approval gate. Self-host enterprise-only.

**Revisit triggers (specific, measurable):**
1. **GitNexus revisit:** code-review-graph proves blind to multi-repo / cross-project queries during Option D refactor or Branch 3 build. Concretely — if user finds themselves manually correlating changes across `~/claude-hq/scripts/` and a project repo and wishing for a single graph query that spans both, that is the moment.
2. **Composio revisit:** Specific throwaway prototype needs ≥5 SaaS integrations in <1 day with no production credential exposure (e.g., Corporate Brains investor demo). OR: Composio publishes self-host + SOC-2 + clear data-handling at a reasonable tier.

**How to start:** Re-read the evaluation memory file, re-run `WebFetch` on both URLs to refresh state (releases / pricing / licence may have moved), re-test the specific pain point that surfaced, decide integrate / skip-permanently.

**Acceptance:** Decision logged either way. If integrated, add to `~/claude-hq/registry.json` with activation triggers + cost flag + Trust Gate exception note. If skipped permanently, mark this entry `[Done]` with the reason.

**Estimate:** 30-60 min to re-evaluate when triggered, plus integration time if proceeding.

**Source:** 2026-05-09 conversation. User asked for CTDD evaluation, accepted skip verdict, requested log for future reference rather than action. Full reasoning preserved in memory file above.

---

## Source

Captured 2026-04-22 during HQ activation conversation. User (Sunil) asked whether to install ruflo / seed / paul / TECCP into HQ. Conclusion was that adding more frameworks adds overhead without clear gain — these four actions are the higher-leverage alternatives. Full reasoning is in that session's transcript.

Items 5–11 added 2026-05-06 during the multi-model routing build session (Phase 0 + Phase 1 shipped, Trust Gate eval bug fixed). Items 5–9 are the Phase 2/3/4 + Watchdog listener + digest deferrals; items 10–11 are housekeeping found during the build.

Items 12–13 added 2026-05-06 after the claude-mem paid-tier flip exposed two upstream quirks during backlog drain. Both non-blocking.

Item 14 added 2026-05-06 after evaluating ScrapeGraphAI for HQ integration. Captures the Apify-class gap with three concrete paths so future-self doesn't redo the eval. ScrapeGraphAI itself was ruled out for HQ — see the entry's "Why ruled out" subsection.

---

## [Done] — 2026-05-11 — [PATS-Copy] Branch 3 Geopolitics Specialist Research Sprint

**Outcome (resolved 2026-05-11 same day):** Verdict **SWAP** — drop `0x5d05b1f5` from primary watch list, lead with `0x24c8cf69a0e0a17eee21f69d29752bfa32e823e1` (Phase 2 v2 passer: 149 geo positions, 62.4% WR overall, 69.6% resolved-only WR, +$142K all-time truePnl, +$116K resolved-only realized P&L, median bet $167). Keep `0x44c1dfe4` as Tier-2 candidate. Recommended sizing: **flat $75** (out-performed proportional in every cut). Sprint findings doc: `~/Desktop/POLYMARKET_TRADING_3.0/_NEXT_STEPS/branch-3-research-2026-05-11.md`. Decision Log entry: 2026-05-11 "Branch 3 research sprint COMPLETE — SWAP verdict" in `~/Vaults/Jarvis-Brain/JARVIS-BRAIN/Projects/PATS-Copy/04 Decision Log.md`.

**Big surprise:** the 2026-05-11 baseline measurement was structurally biased. `gamma-api/markets?condition_ids=` silently omits resolved markets, so the original backtest could only see still-open positions — which were systematically the wallet's still-winning bets. The unbiased `/positions?user=X` endpoint reveals `0x5d05b1f5` is actually NET NEGATIVE on its own track record (−$2,405 / 53.6% WR / median bet $5.44). This bug created 4 follow-up BACKLOG items (below).

**Build NOT yet started** — verdict is recommendation only, user-decision boundary respected per sprint constraints.

---

## [Done] — 2026-05-11 — [PATS-Copy] Fix `market-categoriser.ts` politics keyword gaps

**Outcome (resolved same day):** Landed in bot repo as commit `fix(categoriser): add Iran/Israel/Gaza/Netanyahu keywords to politics filter`. 28 keywords added (iran, israel, gaza, palestine, hamas, hezbollah, lebanon, syria, taiwan, north korea, jerusalem, west bank, middle east, venezuela, netanyahu, zelensky, erdogan, kim jong, starmer, lutnick, noem, rubio, hegseth, epstein, treaty, embassy, ambassador, diplomatic). Conservative scope: skipped bare ambiguous terms (war, strike, coup, invasion, occupation, china, russia) to avoid false positives on non-political contexts — sports keywords iterate first anyway. Verification: `scripts/verify-categoriser.ts` pins 36 sprint-discovered fixtures, all pass; `tsc --noEmit` clean. Branch 3 wallet-eligibility gate now sees Iran/Israel/Netanyahu titles correctly.

**What (original):** Add missing geopolitics keywords to `src/signals/market-categoriser.ts:KEYWORDS.politics`: `iran`, `israel`, `gaza`, `palestine`, `hamas`, `hezbollah`, `netanyahu`, `taiwan`, `north korea`, `jerusalem`, `west bank`, `middle east`, `lebanon`, `syria`, `erdogan`, `kim jong`, `coup`, `invasion`, `occupation`, `treaty`, `embassy`, `ambassador`, `diplomatic`, and several Trump-cabinet figures (`lutnick`, `noem`, `rubio`, `hegseth`). Same applies to `detectSpecialistCategory` consumer code if it has any dependent thresholds.

**Why:** The categoriser under-counts geopolitics activity. During the 2026-05-11 research sprint we found that a specialist with 26 broad-geopolitics positions only registered ~14 of those as "politics" via the current keyword list — the Iran/Israel/Netanyahu/Gaza titles fall through to 'other'. This skewed the Phase 1b watchlist audit and the Phase 3 backtest narrowing. Patch BEFORE Branch 3 ships — it currently uses the buggy categoriser for the wallet-eligibility gate.

**Estimate:** 30 min. Drop new keywords into the array, run `npm test` if any exist, commit.

**How to start:**
1. Open `src/signals/market-categoriser.ts`.
2. Extend the `politics` keyword array with the list above (full set in `scripts/research/phase2v2-screen-via-positions.ts:GEO_KW`).
3. Run any unit tests touching `categoriseMarket` (if absent, add a few examples from the sprint: "US forces enter Iran by March 31?", "Netanyahu out by June 30?", "Iranian regime fall before 2027?" — each should categorise as `politics`).
4. Commit: `fix(categoriser): add Iran/Israel/Gaza/Netanyahu keywords to politics filter`.

**Acceptance:** the 3 sprint-discovered test titles classify as politics. No regression on existing categorisation.

**Source:** 2026-05-11 Branch 3 research sprint (Phase 2 v2 deep-dive). Sprint findings doc has full surfaced keyword set.

---

## [Done] — 2026-05-11 — [PATS-Copy] Branch 3 backtest harness — replace Gamma MTM with combined `/positions` + `/trades`-flow aggregation

**Outcome (resolved same day):** Closed. Both the screening layer (`scripts/research/phase2v3-screen-combined.ts`) and the backtest harness (`scripts/backtest/branch3-geopolitics.ts`) now use the canonical truePnl measurement (per-position cashPnl + realizedPnl from `/positions`, with trade-flow cashflow fallback for sell-out positions).

Verdict reversal on the 3-wallet shortlist over the same 30-day window:

| | Old harness (Gamma-biased) | New harness (positions+trade-flow) |
|---|---|---|
| leader truePnl total | −$14,178 | +$173,348 |
| combined proportional | +$52 | +$11,505 |
| combined flat $75 | +$693 | +$31,163 |
| `0x24c8cf69` proportional | −$52 (the artifact) | +$10,794 (129% ROI) |

The corrected measurement reveals `0x24c8cf69`'s $82K April-22 Iran-peace redemption + $32K Iranian-regime-fall + $9.7K Trump-Iran-ops-end that Gamma had hidden. Same wallet, same trades, just the right tool.

Small follow-up flag: 212 positions skipped as "open w/o /positions entry" in the test run — probably small share balances under /positions' threshold or partially-redeemed positions. Worth a tiny investigation if maximum coverage matters; not blocking any current decision.

**What (original):** `scripts/backtest/branch3-geopolitics.ts` STAGE 3a uses `gamma-api.polymarket.com/markets?condition_ids=<cid>` to compute MTM. Gamma silently omits resolved markets — so the harness systematically excludes the wallet's longest-standing realised wins/losses. Replace this MTM source with combined `/positions` + `/trades`-flow logic (see `scripts/research/phase2v3-screen-combined.ts` for the canonical implementation pattern).

**Why:** This bias is what produced the misleading 2026-05-11 baseline verdict. Sprint Phase 3 re-run with new shortlist suffered from the same bias (119/177 positions skipped). The harness CANNOT measure cumulative geopolitics-specialist edge without this fix. Without it, every future Branch 3 calibration run will repeat the bias.

**Estimate:** 2-3 hours. Refactor STAGE 3a-b to fetch /positions per leader, join trades by conditionId+outcomeIndex, use truePnl = cashPnl + realizedPnl as the position outcome.

**How to start:**
1. Build a `fetchPositions(wallet)` helper modelled on `scripts/research/phase2v2-screen-via-positions.ts:fetchPositions`.
2. For each leader, fetch /positions ONCE, build a map keyed by `${conditionId}|${outcomeIndex}` → { cashPnl, realizedPnl, isResolved }.
3. In the per-position economic accounting (STAGE 3b/4), use truePnl from this map instead of (cashFlow + netShares × Gamma price).
4. Keep the current Gamma path as a fallback or remove entirely.
5. Re-run with the same WATCHED_WALLETS as Phase 3 sprint to verify the result matches /positions reality.

**Acceptance:** Backtest verdict for the sprint shortlist `[0x24c8cf69, 0x5d05b1f5]` matches the /positions data direction: challenger > baseline by a wide margin.

**Source:** 2026-05-11 Branch 3 research sprint Phase 3 — full caveat documented in sprint findings doc.

---

## [Done] — 2026-05-11 — [PATS-Copy] Fix leaderboard fetcher DOM virtualisation cap

**Outcome (resolved same day):** Solved via the SSR API instead of fixing the DOM scrape. Discovered the underlying route pattern: `polymarket.com/_next/data/<buildId>/en/leaderboard/<category>/<window>/<sort>.json` — one fetch returns the React Query dehydrated state with all 3 sort variants (profit / volume / biggestWins) for that (category × window). For politics across 4 windows: **134 unique wallets** with rich metadata (rank, name, pseudonym, amount, pnl, volume, realized, unrealized) vs the v1 DOM scrape's 71. Replaces the Puppeteer + DOM virtualisation path entirely — no browser needed.

Implementation: `scripts/research/phase1a-v2-politics-leaderboard.ts`. Build ID discovered automatically from the leaderboard HTML (regex `build-[A-Za-z0-9_-]+`). Output: `_NEXT_STEPS/branch-3-phase1a-v2-politics.json`. Unlocked the diversified-shortlist verdict for Branch 3 (12 passers vs 1 — see 2026-05-11 Decision Log "Branch 3 verdict UPGRADED").

**What (original):** `scripts/research/phase1a-leaderboard-fetch.ts` (and by extension the production `src/leaderboard/scraper.ts` Puppeteer path) scrapes wallet addresses from the rendered DOM. React virtualised lists only render visible rows — so the scrape caps at 27-35 wallets per time window, not the full top-100. Fix the fetcher to either (a) programmatically scroll past the virtualisation buffer, or (b) intercept the lazy XHR the leaderboard frontend MUST be making for paginated rows (recon script `scripts/research/phase1-leaderboard-recon.ts` captured no obvious leaderboard XHR but a fresh deeper inspection might find it).

**Why:** Sprint Phase 1a only got 71 unique candidates across 3 windows. With proper top-100 across 3 windows the candidate pool would be 200-250 (after overlap dedup), giving Phase 2 v2 much more material to find diversified specialists. The current SWAP recommendation rests on 1 strong wallet + 1 tier-2 — exactly the concentration risk the sprint was meant to address.

**Estimate:** 2-3 hours. Scroll-to-load approach is simpler; XHR-intercept is cleaner.

**How to start:**
1. Re-run `scripts/research/phase1-leaderboard-recon.ts` with response-body capture enabled (currently captures URLs + first-200-chars previews — extend to full bodies > 1KB for the candidate URLs).
2. Look for any URL that returns >100 wallet addresses or a clearly paginated structure (`{results: [...], next: '...'}` or similar).
3. If no XHR is found, implement scroll-to-bottom-N-times in `phase1a-leaderboard-fetch.ts` (the existing scroll loop has maxScrolls=8 but the leaderboard may need 20+ to load row 100).

**Acceptance:** Each time window yields ≥80 wallets. Combined unique pool ≥200.

**Source:** 2026-05-11 Branch 3 research sprint Phase 1a observation.

---

## [Open] — 2026-05-11 — [PATS-Copy] Adopt `/positions` as first-class leader-evaluation signal

**What:** Polymarket's `data-api.polymarket.com/positions?user=<wallet>&limit=500` returns per-position `cashPnl + realizedPnl` for every position a wallet currently holds, including resolved-but-redeemable ones. This is the closest thing to ground-truth wallet edge measurement on Polymarket. Currently the bot's leader scoring (`src/leaderboard/scorer.ts`) uses composite of WR + profit factor + frequency + recency derived from leaderboard scrape data. /positions data is richer and more decisive.

**Why:** Both the 2026-05-11 baseline and the Phase 3 backtest re-run produced misleading verdicts because they relied on trade-derived or Gamma-derived position-state inference. The /positions endpoint resolves this directly. Should become part of the leader-eligibility flow, not just an ad-hoc research tool.

**Estimate:** 3-4 hours for an MVP integration. Cache /positions per wallet for 5-10 minutes, expose `getLeaderEdgeSummary(wallet)` returning `{ totalGeoPositions, resolvedWr, allTimeTruePnl, medianBet, lastTradeAge }`. Optionally fold into the composite score (would need tuning).

**How to start:**
1. Lift `fetchPositions` + `isGeopolitics` helpers from `scripts/research/phase2v2-screen-via-positions.ts` into a new `src/leaderboard/positions-evaluator.ts`.
2. Add a unit test pinning the helpers' output against a known fixture (capture the live response from `0x24c8cf69` into `tests/fixtures/positions-0x24c8cf69.json`).
3. Wire into the watcher promotion/demotion logic OR expose as a stand-alone CLI for ad-hoc audits.

**Acceptance:** A new wallet can be audited via `node-script-or-CLI <wallet>` returning the per-position edge summary in <2 seconds.

**Source:** 2026-05-11 Branch 3 research sprint — the /positions endpoint was the discovery that resolved the baseline ambiguity.

---

## [Open] — 2026-05-11 — [PATS-Copy] Branch 3 Tier-1 auto-promotion loop (Phase A → B → C)

**What:** Close the loop on the static Tier-1 geopolitics watchlist by making it self-maintaining. Today (post Branch 3 build, commit `eb56980`), the Tier-1 list is hardcoded in `src/geopolitics/watchlist.ts` and requires manual edit + redeploy to change. As new geopolitics specialists emerge on Polymarket, we need a system that (a) detects them, (b) decides whether to promote, (c) acts on the decision — with watchdog backstop monitoring runtime performance afterwards. Build staged across three phases, each with its own kill-switch verification gate.

**Why:** The static-list architecture has a real gap — nothing today is automatically surfacing "a new wallet appeared that passes our filters". Without a closing mechanism, the watchlist quietly drifts out of date as the trader population evolves. Manual re-screening depends on Sunil remembering to do it.

Doctrinally (per feedback memory `feedback_automate_when_rules_airtight.md`, 2026-05-11): if rules are airtight and Claude would recommend on rule-pass, automate the promotion. Manual gates that don't add signal are ceremony. The right architecture is rich-rules + auto-execute + watchdog backstop + safety rails (churn cap, watchlist snapshotting). NOT a permanent manual approval gate.

**Why staged (not all-at-once):** Building full auto-promote today means locking in rules based on one observed miss (`yyyy77777` Tier-2 case). Not enough observation to be confident. CTDD says: don't ship automation faster than observation supports.

**Scope (sequenced, each phase gated):**

### Phase A — Watchdog weekly diff alert (~1–2h, schedule: NEXT SESSION)
- Cron runs `scripts/research/phase1a-v2-politics-leaderboard.ts` + `phase2v3-screen-combined.ts` weekly
- Diffs result against current `TIER_1` in `src/geopolitics/watchlist.ts`
- Telegrams plain-English alert: new passers + existing Tier-1 underperformers
- Zero impact on the bot. Pure visibility.
- Each weekly diff is a test case for Phase B (would current rules promote this? would I override? why?)
- Verification gate: runs cleanly, alerts useful, no false-positive flood

### Phase B — Rule set v2 (~3h, schedule: WEEK 2 OF PAPER SOAK)
- Use Phase A diff data to identify rules currently missing
- Extract implicit human judgements into deterministic rules. Initial candidate set:
  - `truePnl > 0` (deal-breaker even at high WR — catches `yyyy77777`)
  - WR consistency: ≥55% in BOTH last-30d AND last-90d windows (catches lucky streaks)
  - Sample size: ≥30 positions (was ≥15 — too noisy)
  - Wallet age: ≥60 days (catches Sybils / brand-new accounts)
  - Cooling-off check: internal `geopolitics-cooling-off` list maintained when wallets pull stunts
  - Strategy-type sanity: flag wallets whose P&L is heavily from disputed-market UMA resolutions (different mechanism than directional prediction)
- Verification gate: enriched rule set, applied retroactively to Phase A diffs, correctly identifies wallets that would have been manually rejected

### Phase C — Auto-promote + churn cap + snapshotting (~3–4h, schedule: AFTER PAPER SOAK PASSES)
- Cron wraps Phase A+B into a single decision pipeline
- New passer found AND not in TIER_1 → auto-add (commit + push + watchdog alert)
- Existing Tier-1 fails rules → auto-remove
- Every change: snapshot `watchlist.ts` to date-stamped backup (`watchlist-snapshots/2026-XX-XX.ts`) for one-command revert
- **Churn cap:** if >2 changes pending in any cycle → PAUSE auto-action, alert with full diff, require manual `ack` to apply. Catches regime shifts where the whole landscape is moving.
- Watchdog rules running in parallel: per-wallet truePnl ≥ 0 rolling 30d, activity ≥1 trade/14d, alert on Tier-1 entry/exit events
- Verification gate: dry-run auto-promote against last 4 weeks of Phase A diffs → confirm it produces same decisions a manual reviewer would

**Estimate:** ~7–10h total spread across three sessions. Phase A blocks B (uses A's data). B blocks C (rules need to be enriched first). C blocks live activation (requires soak verdict to confirm Branch 3 itself works).

**Acceptance per phase:** see verification gates above. Final acceptance for full loop: 4-week trailing dry-run matches manual decisions ≥95% of cases, churn cap fires correctly on synthetic regime-shift test, snapshot-based revert verified working.

**Source:** 2026-05-11 — conversation about whether the Branch 3 static watchlist can incorporate new wallets. Sunil pushed back on Claude's default of "manual approval forever"; Claude's CTDD-honest concession produced the staged automation plan. Doctrine captured in `feedback_automate_when_rules_airtight.md`.

---

## [PATS-Copy] Branch 3 Geopolitics Specialist Research Sprint — 2026-05-11 (HISTORICAL — sprint definition)

**What:** Time-boxed 4-6h research sprint to validate whether geopolitics copy edge generalises beyond wallet `0x5d05b1f5` before committing to Branch 3 build. The 2026-05-11 backtest showed MIXED verdict — positive PnL but all 8 sample positions came from one wallet, which is a single point of failure for the entire pipeline economics. Build cannot start until verdict is in.

**Context:** Option D shipped 2026-05-11 (per-pipeline RiskManagers + Supabase pipeline col + capital pools), which unblocks Branch 3 architecturally. Branch 3 itself is the path back to March-level monthly profits (~$1k/mo from copy pipeline alone per 2026-05-10 forensic). But the backtest sample is too thin and concentrated to ship to paper mode without first knowing whether `0x5d05b1f5` is one specialist of many or the only one.

**Why this matters:** Building Branch 3 with the current 11-wallet list risks shipping a pipeline whose entire P&L depends on a single wallet's continued performance. If that wallet goes silent, changes strategy, or regresses, Branch 3 dies. Research cost (4-6h) is small relative to the cost of post-build discovery.

**Scope (Phase 1-3):**

1. **Phase 1 — Source candidates (1-2h):**
   - Polymarket leaderboard top 100 wallets (last 30d, 90d, all-time)
   - Cross-check current 11-wallet watch list — which ones were actually active in geopolitics markets in last 90d?
   - Optional: Dune Polymarket dashboards for geopolitics-tagged markets

2. **Phase 2 — Screening filter (1-2h):**
   - Hard filters: ≥15 geopolitics-market trades in last 90d, win rate ≥55%, avg trade size $10-$500, active in last 14 days
   - Output: ranked shortlist of 5-10 candidates

3. **Phase 3 — Backtest validation (1-2h):**
   - Re-run `~/Desktop/POLYMARKET_TRADING_3.0/scripts/backtest/branch3-geopolitics.ts` with new shortlist
   - Compare proportional vs flat sizing on the diversified sample

**Decision criteria (set in advance, no goalpost-shifting):**

- Diversified positive PnL → **BUILD** Branch 3 with new wallet pool, flat sizing v1
- `0x5d05b1f5` remains the only consistent specialist → small-cap test ($200) or **KILL** Branch 3
- Shortlist outperforms `0x5d05b1f5` → **SWAP** in stronger wallets, build with new list

**Deliverables:**

- Updated `scripts/backtest/branch3-geopolitics.ts` with researched wallet list
- Research findings doc at `~/Desktop/POLYMARKET_TRADING_3.0/_NEXT_STEPS/branch-3-research-<date>.md`
- Obsidian Decision Log entry with verdict + provenance
- This BACKLOG entry marked `[Done]` with outcome

**Acceptance:** Verdict locked in Decision Log. If BUILD: Branch 3 build spec scoped + ready for next-session implementation. If KILL: rationale documented + Branch 3 removed from forward sequencing. If SWAP: shortlist locked + backtest harness re-validated.

**Estimate:** 4-6 hours total, single session.

**Source:** 2026-05-11 conversation. User asked "maybe we should research alternative geopolitics specialists first?" — CTDD analysis confirmed research-first beats build-first on this evidence. Recovery context in `~/.claude/projects/-Users-sunil-rajput/memory/project_session_handoff_2026_05_11.md` and `~/Desktop/POLYMARKET_TRADING_3.0/_NEXT_STEPS/2026-05-11-master-handoff.md`.
