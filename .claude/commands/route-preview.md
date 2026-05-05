---
description: Preview which model tier the routing hook would choose for a given task description (dry run, no dispatch).
argument-hint: <task description>
---

Run this command via the Bash tool and display the output to the user:

```bash
~/claude-hq/scripts/route-preview.sh "$ARGUMENTS"
```

The output is a single line in the form `→ Routed general-purpose → <tier> (reason)`. Show the full output verbatim and add a one-sentence interpretation if the chosen tier is unexpected (e.g. "This routes to Haiku because of the keyword 'summarise' — if you wanted Sonnet, rephrase with 'synthesise' or 'review'").

If `$ARGUMENTS` is empty, ask the user for a task description first; do not run the command with an empty argument.
