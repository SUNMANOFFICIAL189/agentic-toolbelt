# LESSONS — Global Self-Improvement Log

> After ANY correction from the user, add a preventive rule here.
> Review this file at the start of every engagement.
> Rules should prevent mistakes, not just describe them.

---

## Rules

### 1. Never install external code without the Trust Gate
- **Rule:** Every `git clone`, `npm install`, `pip install`, `pipx install`,
  `cargo install --git`, and `npx skills add` passes through the Trust Gate
  (Tier B ambient hook + Tier C full pipeline for skills.sh).
- **Why:** Snyk Feb 2026 audit — 13.4% of skills.sh + ClawHub skills have
  critical issues (malware, prompt injection, secrets). Skill-based prompt
  injection succeeds 95.1% of the time vs 10.9% direct. The ecosystem is
  actively hostile.
- **How to apply:** The PreToolUse hook at `scripts/trust-gate.sh` is
  ambient — do not edit it away. For skill discovery, always use `/scout`,
  never `npx skills add` directly.

### 2. Install counts are a weak signal, not proof
- **Rule:** A skill with 1M installs is no more trustworthy than one with 100.
  Reputation is a tie-breaker when other layers pass, never an auto-pass.
- **Why:** Snyk data shows issue prevalence is roughly flat across install
  counts. The `find-skills` skill itself (1.1M installs) is published by
  vercel-labs — currently in cooling-off.
- **How to apply:** Trust Gate Layer 4 (reputation) runs AFTER Layers 0.5-3
  and only affects the auto-pass vs manual-review decision.

### 3. Allowlists decay — cooling-off overrides trust
- **Rule:** Any author/vendor with a publicly disclosed security incident in
  the last 90 days is demoted from allowlist to full Tier C scrutiny until
  90 days post-incident + published post-mortem + verified supply chain.
- **Why:** Vercel 2026-04-19 — compromised via a third-party AI tool
  (Context.ai) breaching an employee's Google Workspace. "We believe the
  supply chain is safe" is not "we have verified every artefact."
- **How to apply:** `commander/INCIDENT_LEDGER.md` holds active cooling-off.
  The advisory layer checks this BEFORE the allowlist — cooling-off wins.

### 4. Security-research skills will trigger Layer 2 false positives
- **Rule:** Skills authored by security research firms (trailofbits, snyk,
  lakera, etc.) will match prompt-injection/secret regex patterns because
  their documentation discusses the very patterns they're designed to detect.
  Treat Layer 2 FAIL from an allowlisted security author as manual-review
  required, not auto-block.
- **Why:** Shakedown 2026-04-21 on `trailofbits/skills` — flagged by Layer 2
  for YARA jailbreak detection docs, Firebase vulnerability research docs,
  Python sharp-edges notes (`subprocess shell=True` documented as DON'T).
  All legitimate security research content.
- **How to apply:** For allowlisted security research authors, review the
  specific file paths flagged. If all hits are in `references/` or `docs/`
  directories discussing patterns educationally, override with
  `HQ_TRUST_OVERRIDE=1`. Never auto-override for non-allowlisted authors.

### 5. Always query skills.sh before authoring a new skill
- **Rule:** Before building a new skill or slash command, run `/scout <task>`
  to check if the capability already exists in the ecosystem.
- **Why:** The ecosystem has ~91K skills. Most common needs are covered.
  Authoring duplicates wastes time and creates maintenance burden.
- **How to apply:** In Commander Step 2.5, skills.sh fallback runs after
  registry and Agent Bank scan. Only build new skills when `/scout` returns
  no adequate match (or all matches are low-reputation / in cooling-off).

### 6. Postinstall scripts run before hooks can stop them
- **Rule:** Our PreToolUse hook runs BEFORE the command, but `npm install`
  and `pip install` execute postinstall scripts AS PART OF the install, not
  after. PostToolUse scanning is retrospective for these.
- **Why:** Structural limitation of how package managers work — the hook
  cannot split install-time execution.
- **How to apply:** For npm/pip installs from unknown authors, prefer
  `--ignore-scripts` flag when available. For unknown authors, clone first
  (Tier B gated), scan with Tier C tools manually, then install.

### 7. Parse `git clone` with a tokeniser, not a single regex
- **Rule:** Never use a one-shot bash regex to extract the URL from a
  `git clone` command line. Use `shlex` (or equivalent) to tokenise, then
  walk the tokens skipping flags-with-values (`--branch NAME`, `--depth N`,
  `-b NAME`, etc.).
- **Why:** 2026-04-21 PATS-Copy relay-push incident — the original regex
  `(--[a-z-]+[[:space:]]+)*([^[:space:]]+)` only consumed `--flag ` (no
  value), so `git clone --branch strategy/hybrid-v1 root@SERVER:/path`
  mis-identified `strategy/hybrid-v1` as the URL. `extract_owner` then
  returned `strategy` and the whole clone was blocked as UNKNOWN. The
  actual server URL was never inspected. `trust-gate.sh` now uses a Python
  shlex parser with an explicit `FLAGS_WITH_VAL` set.
- **How to apply:** Any future change to install-command parsing must
  tokenise first. Add new flags-with-values to `FLAGS_WITH_VAL` in
  `trust-gate.sh:parse_git_clone_url`.

### 8. `HQ_TRUST_OVERRIDE=1` inline prefix is parsed from the command string
- **Rule:** PreToolUse hooks cannot see env vars set on the command line
  (the hook runs before the command executes, so the assignment never
  reaches a child process). Inline `HQ_TRUST_OVERRIDE=1` is detected by
  pattern-matching the command string itself, not by reading the
  environment.
- **Why:** Same 2026-04-21 incident — user retried with
  `HQ_TRUST_OVERRIDE=1 bash -c '...'` and the override was silently
  ignored because the hook only checked `${HQ_TRUST_OVERRIDE:-0}` from
  its own env. Two paths now: (a) string-detection in the command, or
  (b) `export HQ_TRUST_OVERRIDE=1` in the shell before launching Claude.
- **How to apply:** When documenting override mechanics, always explain
  both paths. Don't tell users to "prefix" without noting that it's a
  string-pattern detection, not a real env-var pass-through.

### 9. Self-hosted infra needs a separate allowlist from the author allowlist
- **Rule:** `SUNMANOFFICIAL189` (GitHub username) and `204.168.204.247`
  (server IP) are both operator-owned but belong in different lists.
  Author allowlist is for GitHub owners. Self-hosted is for hosts/IPs
  extracted from SCP-style (`user@host:/path`) and non-GitHub URL clones.
  Do not conflate them.
- **Why:** Extending the author allowlist to include IPs would make
  `extract_owner` confused about whether `192.168.x.x` is a dotted owner
  name or an IP. Separate list, separate matcher.
- **How to apply:** Add new servers to `SELF_HOSTED=(…)` in
  `advisory-check.sh`. Match runs after cooling-off, before author
  allowlist. Post-clone Magika + secret-scan still execute — this is
  defence-in-depth, not blind trust.

### 10. Verify backup BEFORE consolidating to a single canonical home
- **Rule:** Never untrack, delete, or "centralise" to one location without
  first confirming that location is itself backed up. If you're about to
  say "X is now the single source of truth," verify that X has its own
  backup before taking the consolidation step.
- **Why:** 2026-04-21 — removed `graphify-out/` from claude-hq tracking,
  declaring the Obsidian vault the canonical knowledge-graph home.
  Vault had NO backup (no iCloud, no Obsidian Sync, no Time Machine, no
  git). Sunil caught it in the next message. One disk failure and the
  entire vault would have been lost. The consolidation was correct in
  principle but premature in sequence.
- **How to apply:** Before any `.gitignore` addition that removes a
  previously-tracked artefact, or any "canonical home" declaration,
  explicitly audit the new home's backup: iCloud / git remote / cloud
  sync / Time Machine. If none, set one up FIRST, then consolidate.

### 11. Don't invent vault taxonomy — extend what exists
- **Rule:** Before proposing a new top-level folder or structure in the
  Obsidian vault, check what conventions already exist. Extend those;
  don't invent parallel hierarchies.
- **Why:** 2026-04-21 — proposed moving `claude-hq` out of `Projects/`
  and into a new `System/` folder to reflect infrastructure vs project
  distinction. Sunil correctly pushed back: `System/` did not exist in
  the vault, PATS-Copy already sat in `Projects/`, and inventing a new
  tree fragmented the taxonomy for a purely semantic reason. Resolution:
  keep in `Projects/`, differentiate via file naming convention
  (descriptive vs numbered) instead.
- **How to apply:** When unsure whether to add a new vault folder, ask
  "does this map to a convention already used for another project?"
  If yes, extend. If no, the right fix is usually a file-naming tweak
  or a sub-folder, not a new top-level.

### 12. Duplicating source in vault violates "no duplicates" even when framed as a summary
- **Rule:** If you find yourself writing a vault-native file whose header
  says "mirrors X" or "summary of X" where X is a source-controlled
  file, stop. Use a symlink to X instead, or just wikilink from the Hub.
  A summary copy always drifts from source.
- **Why:** 2026-04-21 — created `05 Lessons Learned.md` in the vault as
  a "summary" of `~/claude-hq/commander/LESSONS.md`, then 20 minutes later
  wrote the anti-duplication rule in `docs/ORGANIZATION.md`. The same
  session. Sunil caught the contradiction. Resolution: delete the
  duplicate, symlink `Commander/` → `~/claude-hq/commander/` so all
  source files (LESSONS, TRUST_GATE, etc.) surface in Obsidian without
  copies.
- **How to apply:** If a file's justification is "easier to browse" —
  use a symlink. If the justification is "summarise for Obsidian" —
  don't; the source is already markdown and Obsidian-native. Write a
  wikilink from the Hub pointing at the source.

### 14. Plaintext-secret config files are landmines — read them only via redirected tools
- **Rule:** If a file is known to contain plaintext secrets (`claude_desktop_config.json`,
  `.env`, credentials registries), never surface its contents directly through the `Read`
  tool. Route secrets via scripts that touch them in-memory only and write to a secure
  store (macOS Keychain, a gitignored mode-600 file). If a `Read` is unavoidable for
  structural inspection, pair it with an immediate scrub + acknowledge the secondary
  leak into session transcripts and claude-mem.
- **Why:** 2026-04-21 → 2026-04-22 — reading `claude_desktop_config.json` to diagnose
  why the Reddit MCP wasn't available surfaced 4 live secrets (Anthropic, Gemini,
  GitHub, Reddit client secret) into tool output, which flowed into claude-mem
  observations (1 row) and 8 local session transcripts before we caught it. Sunil
  opted against rotation, so we migrated to Keychain + launchers + session-end
  scrubber. The local leak was fully scrubbable; the Anthropic-backend leak is not.
- **How to apply:** When an MCP/credential question forces config inspection, prefer
  `security find-generic-password`, `env | grep`, or a helper script that reads the
  config, stores in Keychain, and rewrites the file — all in one pass with no stdout
  echo of values. The one-pass migration script is at
  `~/claude-hq/scripts/mcp-migrate-to-keychain.sh`. Session-end scrubber is at
  `~/claude-hq/scripts/lib/secret-scrub.sh`. Both are idempotent.

### 15. macOS Keychain + launcher scripts is the right home for MCP secrets
- **Rule:** Any MCP that needs an API key, token, or client secret must be launched
  via a script in `~/claude-hq/scripts/mcp-launchers/` that fetches the secret from
  Keychain at spawn time. The Claude Desktop config references the launcher path;
  the config's `env: {}` block stays empty (or contains only public identifiers like
  OAuth client IDs).
- **Why:** Desktop config sits at a known path, is world-readable by anything with
  your user permissions, and gets read by skills/agents for diagnostics. Keychain
  entries are encrypted at rest and require your login. Launchers keep the spawn
  command short and the config clean.
- **How to apply:** New MCP with a secret → (1) `security add-generic-password -U -a "$USER" -s "claude-mcp-<name>" -w <value>`; (2) copy an existing launcher from `~/claude-hq/scripts/mcp-launchers/`, adapt the service name and exec line; (3) update `claude_desktop_config.json` to point to the launcher with `env: {}`; (4) restart Claude Desktop.

### 13. `.gitignore` patterns with `/` are anchored to the gitignore's location
- **Rule:** In a multi-level repo (where the `.gitignore` sits above
  the actual content dir), patterns like `.obsidian/workspace.json`
  will NOT match `<subdir>/.obsidian/workspace.json`. Use `**/` prefix:
  `**/.obsidian/workspace.json`.
- **Why:** 2026-04-21 — created `jarvis-brain` repo with `.gitignore`
  at `~/Vaults/Jarvis-Brain/` and vault content at
  `~/Vaults/Jarvis-Brain/JARVIS-BRAIN/`. Initial commit accidentally
  tracked `JARVIS-BRAIN/.obsidian/workspace.json` because the pattern
  without `**/` was interpreted relative to the repo root only.
- **How to apply:** If your repo root is one level above the actual
  content, prefix subdirectory-anchored patterns with `**/`. Test:
  `git check-ignore -v <file>` should report the matching pattern.

### 16. All user-facing alerts must be in plain English — no jargon, ever
- **Rule:** Any system built under the HQ umbrella that sends messages to
  Sunil (Telegram, email, push, SMS, anything) MUST describe what happened
  and what to do in natural language a non-technical reader can understand
  at a glance. Technical detail stays in logs, SQLite, or audit files —
  it never reaches the phone. This applies to every alerting system, not
  just Watchdog.
- **Why:** 2026-04-24 — while building the HQ Watchdog, Sunil explicitly
  asked to hardwire this constraint because technical alerts force a
  context switch: read jargon → decode it → figure out what to do. That
  defeats the point of an alert. The Polymarket Telegram pipe already
  follows this pattern (short, readable status messages). HQ alerts must
  match. Without code-level enforcement, every alert author (human or
  agent) will slowly drift toward technical shorthand.
- **How to apply:** When any new alerting path is built:
  1. Every outgoing message goes through a `PlainAlert` (or equivalent)
     with two REQUIRED fields: `what_happened` (plain English) and
     `what_to_do` (one concrete action).
  2. A jargon-linter must block banned words at construction time —
     `threshold`, `regression`, `baseline`, `delta`, `rolling`, `stdev`,
     `p-value`, `FP/TP`, unit shorthand (`7d`, `24h`), raw metric IDs, etc.
  3. Metric definitions (yaml/json) must carry a `plain_language` block
     with `what_it_means`, `why_it_matters`, `alert_template`. No metric
     loads without it.
  4. The template enforces the three-part shape: emoji headline →
     what happened (1-3 plain sentences) → one clear "What to do: …".
  5. Reference implementation lives at `~/claude-hq/watchdog/telegram.py`
     (`PlainAlert` dataclass) and `watchdog/STYLE_GUIDE.md` (banned-word
     list + template examples). Copy this pattern when building the next
     alerting system.
