#!/bin/bash
# CLAUDE HQ — One-time setup script
# Run this ONCE in your regular terminal (not inside Claude Code).
# It adds CLAUDE HQ awareness to your global Claude Code config.
#
# Usage: 
#   git clone https://github.com/SUNMANOFFICIAL189/CLAUDE-HQ.git ~/claude-hq
#   bash ~/claude-hq/setup.sh

set -e

CLAUDE_DIR="$HOME/.claude"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
HQ_MARKER="# === CLAUDE HQ ==="

echo "🏢 CLAUDE HQ Setup"
echo "==================="

mkdir -p "$CLAUDE_DIR"

if [ -f "$CLAUDE_MD" ] && grep -q "$HQ_MARKER" "$CLAUDE_MD" 2>/dev/null; then
    echo "✅ CLAUDE HQ is already configured in $CLAUDE_MD"
    exit 0
fi

cat >> "$CLAUDE_MD" << 'HEREDOC'

# === CLAUDE HQ ===
# Central command center: ~/claude-hq/.claude/AGENTS.md
# Repository: https://github.com/SUNMANOFFICIAL189/CLAUDE-HQ

## When working inside ~/claude-hq:
AGENTS.md loads automatically. Read registry.json on session start. 
Classify the user's task and auto-activate the right tools by running 
git clone / npm install / plugin install commands. Take initiative — 
don't wait for the user to paste repo links.

## When working in ANY other directory:
If the user says "activate HQ", provides a PRD, or starts a major project:
1. cd ~/claude-hq && cat registry.json to load the tool inventory
2. Classify the task against the registry
3. Clone/install the matching tools
4. Return to the project directory and begin work

## Auto-Trigger Rules
- PRD provided → full stack activation (autonomous-agent + claude-mem + everything-claude-code + TECCP)
- "Build me X" → autonomous-agent-system + TECCP
- "activate HQ" → load full registry and present tools
# === END CLAUDE HQ ===
HEREDOC

echo "✅ CLAUDE HQ block added to $CLAUDE_MD"
echo ""
echo "Now run:"
echo "  cd ~/claude-hq && claude"
echo ""
echo "Or from any project: say 'activate HQ' to load the system."
