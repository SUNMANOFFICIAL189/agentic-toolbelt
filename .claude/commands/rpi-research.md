---
description: "RPI Stage 1 — research the codebase for a specific topic, produce a dated research doc"
---

# RPI Stage 1 — Research

You are executing a structured codebase research workflow. Follow these steps exactly in order. Do not improvise, do not skip steps.

## YOUR ONLY JOB: DOCUMENT THE CODEBASE AS IT EXISTS TODAY

- DO NOT suggest improvements or changes
- DO NOT critique the implementation
- ONLY describe what exists, where it exists, and how it works
- You are creating a technical map, not a code review

---

## Mandatory workflow — execute in order

### Step 1 — Read any mentioned files FULLY
If the user's topic references specific files, paths, or documents, read them completely before anything else. Do not use offset/limit — you need full context.

### Step 2 — Decompose the research question
Break the topic into 3–5 specific research areas that can be investigated in parallel.

### Step 3 — Spawn parallel subagents (REQUIRED)
Use the `Agent` tool with `subagent_type: "Explore"` to run research areas in parallel. Send a single message with multiple Agent tool invocations. Each subagent should be briefed with:
- A clear question it is answering (one sub-area)
- Any known file paths or entry points
- A request for file:line references in its output

Do NOT do the research yourself in this stage. Use the subagents.

### Step 4 — Wait for all subagent results and synthesise
Collect every subagent's report. Cross-reference findings. Resolve any contradictions by reading the actual code.

### Step 5 — Gather git metadata
Run:
```bash
date -Iseconds
git rev-parse HEAD
git branch --show-current
basename $(git rev-parse --show-toplevel)
```

### Step 6 — Write the research document
Create `thoughts/research/YYYY-MM-DD-HHmm-topic.md` (e.g., `2026-04-24-1500-auth-flow.md`) with this structure:

```markdown
---
date: <ISO date from step 5>
git_commit: <commit hash>
branch: <branch name>
repository: <repo name>
topic: "<Research Topic>"
tags: [research, codebase, <relevant-tags>]
status: complete
---

# Research: <Topic>

## Research Question
<Original query>

## Summary
<High-level findings, 3-5 sentences>

## Detailed Findings

### <Component 1>
- What exists (file:line references)
- How it connects to other components

### <Component 2>
...

## Code References
- `path/to/file.py:123` — <description>

## Open Questions
<Areas needing further investigation>
```

If `thoughts/research/` doesn't exist, create it.

### Step 7 — Present summary to the user
Show a concise summary with key file references and a link to the doc you wrote. Ask if they have follow-up questions.

---

## Hard rules

- Use subagents for parallel research — don't do it serially yourself
- Document what IS, not what SHOULD BE
- Every finding should include a specific file:line reference
- Write the research doc to `thoughts/research/`

---

## Topic

$ARGUMENTS

If the arguments are empty, ask the user: "What would you like me to research? Provide the topic and I'll run the full workflow."

Adapted from Goose's `rpi-research.yaml` recipe (Apache 2.0, AAIF). See `recipes/cookbook/NOTICE`.
