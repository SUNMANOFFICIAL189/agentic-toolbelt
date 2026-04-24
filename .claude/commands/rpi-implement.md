---
description: "RPI Stage 3 — implement an approved plan phase by phase with verification pauses"
---

# RPI Stage 3 — Implement a Plan

You are implementing an approved technical plan from `thoughts/plans/`. These plans contain phases with specific changes and success criteria.

## Getting started

When given a plan path:

1. **Read the plan COMPLETELY** — check for any existing checkmarks (`- [x]`) to know what's done
2. **Read the original ticket and all files referenced in the plan** — fully, never with offset/limit
3. Think through how the pieces fit together
4. Create a task list with `TaskCreate` to track progress
5. Start implementing if you understand what needs doing

If no plan path is provided, ask for one.

## Implementation philosophy

Plans are carefully designed, but reality can be messy. Your job:

- Follow the plan's intent while adapting to what you find
- Implement each phase fully before moving to the next
- Verify your work makes sense in the broader codebase context
- Update checkboxes in the plan file as you complete sections

When things don't match the plan, think about why and communicate clearly. The plan is your guide, but your judgment matters.

**Trust the plan — don't re-search documented items.** If the plan specifies exact file paths, code to remove, or specific changes, use that information directly. Don't "rediscover" what's already documented. Only search when the plan is ambiguous or when verifying completeness.

## Handling mismatches

If the plan doesn't match reality:

1. **STOP** and think about why
2. Present the issue clearly:

   ```
   Issue in Phase <N>:
   Expected: <what the plan says>
   Found:    <actual situation>
   Why this matters: <explanation>

   How should I proceed?
   ```

3. Wait for the user's direction before continuing.

## Verification approach

After implementing a phase:

### 1. Run automated checks
- Run every automated-success-criterion command from the plan
- Fix issues before proceeding
- Update progress in both your tasks and the plan file (tick `- [x]`)

### 2. Pause for human verification

After all automated checks pass, pause and tell the user:

```
Phase <N> complete — ready for manual verification.

Automated verification passed:
- <list of automated checks that passed>

Please run the manual verification steps listed in the plan:
- <list of manual verification items from the plan>

Let me know when manual testing is complete so I can proceed to Phase <N+1>.
```

**Do NOT tick manual verification items yourself** — only after the user confirms.

If instructed to run multiple phases consecutively, skip the pause until the final phase. Otherwise, assume one phase at a time.

## If you get stuck

- Make sure you've read every relevant file FULLY first
- Consider whether the codebase has evolved since the plan was written
- If a referenced file has changed meaningfully, flag it
- Use subagents sparingly — mainly for targeted debugging or exploring unfamiliar territory

## Resuming previous work

If the plan has existing checkmarks:

- Trust that completed work is done
- Pick up from the first unchecked item
- Verify previous work only if something seems off

You're implementing a solution, not just ticking boxes. Keep the end goal in mind.

---

## Arguments

$ARGUMENTS

Expected format: `<path-to-plan.md> [phase]` — e.g., `thoughts/plans/2026-04-24-1500-auth.md Phase 1` — or just the path to implement whatever's next. If no arguments given, ask for the plan path.

Adapted from Goose's `rpi-implement.yaml` recipe (Apache 2.0, AAIF). See `recipes/cookbook/NOTICE`.
