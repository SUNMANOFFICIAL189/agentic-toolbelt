<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.

---

## Trust Gate — Supply-Chain Security (active since 2026-04-21)

**Every external code clone/install runs through the Trust Gate.** Full protocol in
`commander/TRUST_GATE.md`. Do not bypass except with `HQ_TRUST_OVERRIDE=1` (logged).

### Ambient (Tier B) — automatic via hooks
- PreToolUse hook blocks `git clone` / `npm install` / `pip install` / `pipx install` /
  `cargo install --git` from authors not on the allowlist or in cooling-off.
- PostToolUse hook runs Magika + secret-scan on cloned directories and warns on issues.

### Discovery (Tier C) — via `/scout`
- To find and install skills from skills.sh, use `/scout <query>` — never
  `npx skills add` directly. The PreToolUse hook blocks raw `npx skills add`.
- Tier C runs all 5 layers (advisory, Magika, secret-scan, Socket/pip-audit, reputation).

### Audit — via `/skill-audit`
- Retrospective scan over all installed skills (global + project).
- Run periodically, especially after manual edits or dependency refreshes.

### Cooling-off register
- `commander/INCIDENT_LEDGER.md` — vendors on 90-day elevated-scrutiny.
- Current active: `vercel/*`, `vercel-labs/*` (until 2026-07-20, Apr 2026 incident).
- Cooling-off blocks allowlist — it overrides trust, never the other way around.

### Data that motivated this gate
Snyk audit of 3,984 skills (Feb 2026): 13.4% contain critical security issues;
36.8% have at least one flaw; 76 actively malicious; skill-based prompt injection
95.1% success rate. Install counts are weak signals. Build the gate.

