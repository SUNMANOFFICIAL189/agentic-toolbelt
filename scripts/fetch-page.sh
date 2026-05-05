#!/usr/bin/env bash
# Unified web-page fetcher for HQ.
# Doctrine: Jina Reader for routine fetches (free, fast, hosted), Crawl4AI
# for JS-heavy / anti-bot escalations (local, no Docker).
#
# Usage:
#   fetch-page.sh <url>                    # quick mode (Jina only)
#   fetch-page.sh <url> --mode auto        # Jina, escalate to Crawl4AI on degraded
#   fetch-page.sh <url> --mode deep        # Crawl4AI directly
#
# Output: JSON envelope. See scripts/lib/fetch-page.py for the schema.

set -euo pipefail

HQ_ROOT="${HQ_ROOT:-$HOME/claude-hq}"
VENV_PY="$HQ_ROOT/.venv-crawl4ai/bin/python"
SCRIPT="$HQ_ROOT/scripts/lib/fetch-page.py"

if [ ! -x "$VENV_PY" ]; then
  echo "ERROR: Crawl4AI venv not found at $HQ_ROOT/.venv-crawl4ai" >&2
  echo "Run: python3 -m venv \"$HQ_ROOT/.venv-crawl4ai\" && \"$HQ_ROOT/.venv-crawl4ai/bin/pip\" install crawl4ai && \"$HQ_ROOT/.venv-crawl4ai/bin/crawl4ai-setup\"" >&2
  exit 2
fi

exec "$VENV_PY" "$SCRIPT" "$@"
