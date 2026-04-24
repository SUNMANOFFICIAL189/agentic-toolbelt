# Recipe Cookbook

Adapted workflow recipes from the Goose cookbook (Agentic AI Foundation / Apache 2.0).

## What's here

The recipes are installed as **Claude Code slash commands** in `~/claude-hq/.claude/commands/`. This folder is the **library / provenance record** — it documents what was ported, where it came from, and how it was adapted.

## Current recipes

The **RPI pipeline** — Research → Plan → Implement → Iterate. A 4-stage workflow for non-trivial features:

| Slash command | Stage | What it does |
|---|---|---|
| `/rpi-research` | 1 | Explore the codebase for a specific topic. Produces a dated research doc in `thoughts/research/`. |
| `/rpi-plan` | 2 | Turn research + context into a detailed implementation plan. Produces a dated plan doc in `thoughts/plans/`. |
| `/rpi-implement` | 3 | Execute an approved plan phase by phase with verification pauses between phases. |
| `/rpi-iterate` | 4 | Update an existing plan based on feedback, with surgical edits and fresh research only if needed. |

All four are standalone — you can run just `/rpi-research` for a pure exploration task, or chain them end-to-end for a full feature lifecycle.

## How to use

```
/rpi-research <topic>
/rpi-plan <ticket or context path>
/rpi-implement <path/to/plan.md> [phase]
/rpi-iterate <path/to/plan.md> <feedback>
```

## Adaptations from the original Goose recipes

The originals are YAML workflow recipes for the Goose agent. The adaptations for Claude HQ:

- **Goose subrecipes → Claude Code subagents.** The original recipes spawn "subrecipe" tools for parallel research (`find_files`, `analyze_code`, `find_patterns`). In Claude Code, these become parallel invocations of the `Explore` subagent.
- **Jinja2 templating → slash-command `$ARGUMENTS` convention.** The original uses `{% if topic %} ... {% endif %}`. Claude Code slash commands use `$ARGUMENTS` substitution.
- **Goose extensions block removed.** No `type: builtin` / `timeout: 300` / etc. — Claude Code tools are intrinsic.
- **Integration with Commander protocol.** When a recipe is invoked within the HQ context, it respects `commander/LESSONS.md`, the Boris principles (plan first, verify, be skeptical), and Trust Gate when anything external is involved.
- **Output path flexibility.** Originals write to `thoughts/research/` and `thoughts/plans/`. We keep that as the default — simple, portable, git-friendly — but allow override.

## Attribution

See [`NOTICE`](NOTICE) for the Apache 2.0 attribution.

## Source

- Original repo: https://github.com/aaif-goose/goose
- Recipes: `documentation/src/pages/recipes/data/recipes/rpi-*.yaml`
- Ported: 2026-04-24
