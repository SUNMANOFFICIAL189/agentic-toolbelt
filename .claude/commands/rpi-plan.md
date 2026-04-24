---
description: "RPI Stage 2 — create a detailed implementation plan through iterative dialogue"
---

# RPI Stage 2 — Create a Plan

You are creating a detailed technical implementation plan through an interactive, iterative process. Be skeptical, thorough, and work collaboratively with the user.

## CRITICAL: YOUR JOB IS TO PLAN. DO NOT IMPLEMENT.

---

## Process

### Step 1 — Context gathering & initial analysis

1. **Read all mentioned files FULLY.** If the user references a ticket file, research doc (from `thoughts/research/`), or related plan, read each one completely. Never use offset/limit on these — you need the entire context.

2. **Spawn initial research subagents in parallel** (via `Agent` tool, `subagent_type: "Explore"`):
   - Find the files related to the task (entry points, current implementation)
   - Analyse current implementation to understand what exists
   - Find similar features or patterns in the codebase to model after

3. **Read all files surfaced by the subagents** FULLY into your own context.

4. **Analyse and verify understanding**:
   - Cross-reference the requirements with actual code
   - Identify discrepancies or gaps between what was asked for and what exists
   - Note assumptions that need human verification
   - Determine the real scope based on codebase reality

5. **Present informed understanding and focused questions**:

   ```
   Based on the ticket and my research, I understand we need to <summary>.

   I've found:
   - <current implementation detail with file:line>
   - <relevant pattern or constraint discovered>
   - <potential complexity identified>

   Questions my research couldn't answer:
   - <specific technical question requiring human judgment>
   - <business logic clarification>
   ```

   Only ask questions you genuinely cannot answer through code investigation.

### Step 2 — Research & discovery (if needed)

- If the user corrects your understanding, DO NOT just accept. Spawn new research subagents to verify.
- Read any specific files or directories they reference before incorporating their correction.
- Wait for all subagent results before presenting design options.
- Present design options (at least 2) with pros/cons each, then ask which aligns best.

### Step 3 — Plan structure development

Once the approach is agreed:

```
Here's my proposed plan structure:

## Overview
<1-2 sentence summary>

## Implementation Phases:
1. <Phase name> — <what it accomplishes>
2. <Phase name> — <what it accomplishes>
3. <Phase name> — <what it accomplishes>

Does this phasing make sense? Should I adjust order or granularity?
```

Get feedback on structure BEFORE writing details.

### Step 4 — Write the detailed plan

After structure approval, write the plan to `thoughts/plans/YYYY-MM-DD-HHmm-description.md` using this template:

```markdown
# <Feature/Task Name> Implementation Plan

## Overview
<Brief description of what we're implementing and why>

## Current State Analysis
<What exists now, what's missing, key constraints discovered>

## Desired End State
<Specification of desired end state and how to verify it>

### Key Discoveries
- <important finding with file:line reference>
- <pattern to follow>
- <constraint to work within>

## What We're NOT Doing
<Explicitly out-of-scope items to prevent scope creep>

## Implementation Approach
<High-level strategy and reasoning>

## Phase 1: <Descriptive Name>

### Overview
<What this phase accomplishes>

### Changes Required

#### 1. <Component/File Group>
**File**: `path/to/file.ext`
**Changes**: <summary of changes>

\`\`\`<language>
// specific code to add/modify
\`\`\`

### Success Criteria

#### Automated Verification
- [ ] Tests pass: `<command>`
- [ ] Linting passes: `<command>`
- [ ] Type checking passes

#### Manual Verification
- [ ] Feature works as expected
- [ ] No regressions in related features

**Implementation Note**: After completing this phase and automated verification passes, pause for manual confirmation before proceeding.

---

## Phase 2: <Descriptive Name>
<Similar structure…>

---

## Testing Strategy

### Unit Tests
- <what to test>
- <key edge cases>

### Integration Tests
- <end-to-end scenarios>
```

If `thoughts/plans/` doesn't exist, create it.

---

## Success-criteria guideline — ALWAYS split into two categories

1. **Automated Verification** (can be scripted): commands to run, files that should exist, compilation/type checks.
2. **Manual Verification** (requires a human): UI/UX, performance under real conditions, edge cases hard to automate.

Never conflate them. Automated items can be ticked by an implementation agent; manual items only by the human.

---

## Common patterns (quick reference)

- **Database changes** → schema/migration → store methods → business logic → API → clients
- **New features** → research existing patterns → data model → backend logic → API → UI last
- **Refactoring** → document current behaviour → incremental changes → backwards compat → migration strategy

---

## Ticket / context

$ARGUMENTS

If arguments are empty, ask the user:
"Please provide (1) the task/ticket description or a path to a ticket file, (2) any relevant context or constraints, and (3) links to related research or previous implementations. If you have a research doc from `/rpi-research`, that's ideal context."

Adapted from Goose's `rpi-plan.yaml` recipe (Apache 2.0, AAIF). See `recipes/cookbook/NOTICE`.
