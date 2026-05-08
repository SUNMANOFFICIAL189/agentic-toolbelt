# scripts/ INDEX

> One-line summary per script. The unified RAG probe (`memory-probe.sh`)
> greps this file when keywords match — without it, "I need a script
> that does X" lookups silently miss existing tools.
>
> Convention: when adding a new script under `scripts/`, append a row here
> in the same commit. New scripts that don't appear in this index are
> invisible to the probe and effectively don't exist for retrieval purposes.

---

## scripts/ (top-level)

| Script | One-line purpose |
|---|---|
| `fetch-page.sh` | Unified web-page fetcher — Jina Reader for routine fetches, Crawl4AI for JS-heavy / anti-bot escalations. Modes: `quick`, `deep`, `auto`. |
| `mcp-migrate-to-keychain.sh` | One-shot migration of plaintext MCP secrets out of `claude_desktop_config.json` into macOS Keychain (Lesson 14/15). |
| `memory-probe.sh` | Unified RAG probe across HQ memory banks (Decision Log, BACKLOG, LESSONS, MemPalace, Hindsight, registry/agents/commander/scripts/patterns). |
| `mempalace-precheck.py` | Read-only sqlite integrity check that runs before `mempalace mine`. Aborts mine if segment_id drift or orphan UUID dirs detected. |
| `model-router.sh` | PreToolUse hook applying `commander/MODEL_ROUTING.md` doctrine to Agent dispatches (haiku/sonnet/opus tier choice). |
| `paperclip-burn-tracker.py` | Manual CLI for snapshotting Paperclip token spend per agent + computing burn-rate delta vs baseline. |
| `paperclip-comment.sh` | JSON-safe wrapper for posting comments via the Paperclip control-plane API. |
| `route-preview.sh` | Dry-run preview of the model-router decision for a hypothetical task description (no actual dispatch). |
| `skill-install.sh` | Trust Gate Tier C full pipeline for skills.sh installs — all 5 layers (advisory + Magika + secret-scan + Socket + reputation). |
| `trust-gate-post.sh` | PostToolUse hook that runs Magika + secret-scan on freshly-cloned directories (defence-in-depth after PreToolUse). |
| `trust-gate.sh` | PreToolUse hook that blocks `git clone` / `npm install` / `pip install` / `cargo install --git` / `npx skills add` from unknown-author / cooling-off vendors. |

---

## scripts/lib/ (helpers used by the top-level scripts)

| Helper | One-line purpose |
|---|---|
| `advisory-check.sh` | Cooling-off + author-allowlist + self-hosted check (the gating logic behind `trust-gate.sh`). |
| `fetch-page.py` | Python implementation of the fetch-page wrapper — Jina + Crawl4AI dispatch. |
| `magika-core.sh` | Magika file-type detection helper used by `trust-gate-post.sh`. |
| `model-router.py` | Python implementation of the model routing decision algorithm (called by `model-router.sh`). |
| `secret-scan.sh` | Pattern-based secret detection over a directory tree (used by `trust-gate-post.sh`). |
| `secret-scrub.sh` | Session-end scrubber that redacts known-secret-shaped strings from local logs, transcripts, claude-mem, and MemPalace. |
| `socket-core.sh` | Socket.dev / pip-audit-based dependency vulnerability check helper (Trust Gate Layer 3). |

---

## scripts/mcp-launchers/ (MCP server launchers — Keychain-sourced secrets pattern)

| Launcher | What it spawns |
|---|---|
| `claude-code-bridge.sh` | Bridge MCP for cross-session Claude Code communication. |
| `exa-mcp.sh` | Exa neural search MCP (API key from Keychain `claude-mcp-exa-api-key`). |
| `gemini-bridge.sh` | Gemini bridge MCP (free-tier Gemini for tasks where Claude is overkill). |
| `github-mcp.sh` | GitHub MCP for repo / PR / issue operations (token from Keychain). |
| `paperclip-launcher.sh` | Spawns the Paperclip control-plane (`pnpm dev`) with OPENROUTER + GEMINI keys sourced from Keychain. |
| `reddit-mcp.sh` | Reddit MCP for posting / search / subreddit research. |

---

## Patterns this directory illustrates

(Cross-reference to `~/claude-hq/docs/PATTERNS.md`:)

- Every MCP launcher follows the **Keychain + launcher pattern** (Lesson 15) — config references the launcher, secrets stay in Keychain, env stays empty in `claude_desktop_config.json`.
- Hook scripts (`trust-gate.sh`, `trust-gate-post.sh`, `model-router.sh`) follow the **PreToolUse / PostToolUse ambient hook pattern** — fail-soft, log via stderr, never break Claude Code.
- `mempalace-precheck.py` and `paperclip-burn-tracker.py` follow the **read-only probe pattern** — query state via sqlite or REST without mutating, structured exit codes consumed by hooks.
