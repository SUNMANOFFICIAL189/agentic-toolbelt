#!/usr/bin/env bash
# /route preview helper — invokes the router in dry-run mode for a given task description.
#
# Usage: route-preview.sh "<task description>"
#
# Output: the transparency banner showing which tier would be chosen.
set -euo pipefail

HQ_ROOT="${HQ_ROOT:-$HOME/claude-hq}"
TEXT="${*:-}"

if [ -z "$TEXT" ]; then
  echo "Usage: $(basename "$0") <task description>" >&2
  echo "Example: $(basename "$0") 'design the auth module'" >&2
  exit 1
fi

python3 -c '
import json, sys
text = sys.argv[1]
payload = {
    "tool_name": "Agent",
    "tool_input": {"subagent_type": "general-purpose", "prompt": text}
}
print(json.dumps(payload))
' "$TEXT" | HQ_DRY_RUN=1 python3 "$HQ_ROOT/scripts/lib/model-router.py" 2>&1
