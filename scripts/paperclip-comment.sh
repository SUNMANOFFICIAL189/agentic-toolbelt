#!/bin/bash
# Paperclip comment poster — handles JSON encoding safely
# Usage:
#   paperclip-comment.sh <issue_id>   (reads body from stdin)
#   paperclip-comment.sh              (reads issue_id from $PAPERCLIP_TASK_ID, body from stdin)
#
# Required env vars: PAPERCLIP_API_KEY, PAPERCLIP_API_URL, PAPERCLIP_RUN_ID
# Optional: PAPERCLIP_TASK_ID (used if first arg omitted)
#
# This wrapper exists because the Planner agent's run_shell_command tool
# rejects long curl commands with embedded single-quote characters in -d '...'
# JSON bodies. By writing the encoded body to a tmp file and using -d @file,
# we sidestep the quoting issue entirely.

set -euo pipefail

ISSUE_ID="${1:-${PAPERCLIP_TASK_ID:-}}"
if [ -z "$ISSUE_ID" ]; then
    echo "ERROR: no issue_id (pass as arg or set PAPERCLIP_TASK_ID)" >&2
    exit 1
fi

# Read body from stdin
BODY=$(cat)
if [ -z "$BODY" ]; then
    echo "ERROR: empty body (pipe content via stdin)" >&2
    exit 1
fi

# JSON-encode using python (handles all escaping including quotes, newlines, etc.)
TMP_FILE=$(mktemp /tmp/paperclip-comment-XXXXXX.json)
trap "rm -f $TMP_FILE" EXIT
python3 -c "import json,sys; print(json.dumps({'body': sys.stdin.read()}))" <<<"$BODY" > "$TMP_FILE"

# POST it
curl -s -X POST \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Paperclip-Run-Id: $PAPERCLIP_RUN_ID" \
  -d "@$TMP_FILE" \
  "$PAPERCLIP_API_URL/api/issues/$ISSUE_ID/comments"
echo
