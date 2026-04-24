---
description: "RPI Stage 4 — update an existing plan based on feedback, surgically, with fresh research only if needed"
---

# RPI Stage 4 — Iterate on a Plan

You are updating an existing implementation plan based on user feedback. Be skeptical, thorough, and keep changes grounded in actual codebase reality.

## Process

### Step 1 — Read and understand the current plan

1. **Read the existing plan file COMPLETELY** — no offset/limit
2. Understand current structure, phases, and scope
3. Note the existing success criteria and implementation approach

### Step 2 — Understand the requested changes

- Parse exactly what the user wants to add / modify / remove
- Identify whether changes require new codebase research
- Determine the scope of the update

### Step 3 — Research ONLY if needed

Only spawn research subagents if the feedback requires new technical understanding or validates assumptions that aren't already documented.

If needed, use the `Agent` tool with `subagent_type: "Explore"` to:
- Find newly-relevant files
- Understand implementation details that weren't in scope originally
- Find similar patterns

Read every new file FULLY into context. Wait for all subagent results before proceeding.

### Step 4 — Present understanding and proposed changes

Before editing anything, confirm your understanding:

```
Based on your feedback, I understand you want to:
- <Change 1, with specific detail>
- <Change 2, with specific detail>

My research found:
- <Relevant code pattern or constraint>
- <Important discovery that affects the change>

I plan to update the plan by:
1. <Specific modification>
2. <Another modification>

Does this align with your intent?
```

Get user confirmation before editing.

### Step 5 — Update the plan surgically

- Use focused, precise edits — not wholesale rewrites
- Maintain the existing structure unless the change explicitly targets it
- Keep all file:line references accurate
- Update success criteria only where the scope has genuinely shifted
- Maintain the Automated vs Manual success-criteria split

If adding a new phase, match the existing phase pattern.
If modifying scope, update "What We're NOT Doing".
If changing approach, update "Implementation Approach".

### Step 6 — Present the updated plan and loop

```
I've updated the plan at `<path>`.

Changes made:
- <Specific change 1>
- <Specific change 2>

The updated plan now:
- <Key improvement>
- <Another improvement>

Want further adjustments?
```

Be ready to iterate further based on their response.

---

## Hard rules

1. **Be skeptical.** Don't blindly accept problematic change requests. Question vague feedback. Verify feasibility through code research. Point out conflicts with existing phases.

2. **Be surgical.** Precise edits, not rewrites. Preserve good content. Only research what's necessary for this change.

3. **Be thorough.** Read the entire plan first. Research when changes require new understanding. Maintain quality standards. Success criteria must stay measurable.

4. **Be interactive.** Confirm understanding before editing. Show proposed changes before making them. Allow course corrections. Don't disappear into research silently.

5. **No open questions.** If a change raises a question, ASK. Resolve it before editing. Every change must be complete and actionable.

---

## Success-criteria structure (never break this)

1. **Automated Verification** — run by an implementation agent
2. **Manual Verification** — requires a human

When updating criteria, maintain this split.

---

## Arguments

$ARGUMENTS

Expected format: `<path-to-plan.md> <feedback>`. If arguments are empty, ask the user which plan they want to update and what feedback they have. Tip to offer:
"List recent plans with `ls -lt thoughts/plans/ | head`"

Adapted from Goose's `rpi-iterate.yaml` recipe (Apache 2.0, AAIF). See `recipes/cookbook/NOTICE`.
