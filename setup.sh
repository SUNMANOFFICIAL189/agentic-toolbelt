#!/bin/bash
# CLAUDE HQ — One-time setup script
# Adds CLAUDE HQ awareness to your global Claude Code config
# so it's available from ANY project directory.
#
# Usage: 
#   git clone https://github.com/SUNMANOFFICIAL189/CLAUDE-HQ.git ~/claude-hq && bash ~/claude-hq/setup.sh

set -e

CLAUDE_DIR="$HOME/.claude"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
HQ_MARKER="# === CLAUDE HQ ==="

echo "🏢 CLAUDE HQ Setup"
echo "==================="

# Create ~/.claude if it doesn't exist
mkdir -p "$CLAUDE_DIR"

# Check if CLAUDE HQ block already exists
if [ -f "$CLAUDE_MD" ] && grep -q "$HQ_MARKER" "$CLAUDE_MD" 2>/dev/null; then
    echo "✅ CLAUDE HQ is already configured in $CLAUDE_MD"
    echo "   To update, remove the CLAUDE HQ block and re-run this script."
    exit 0
fi

# Append CLAUDE HQ block to CLAUDE.md
cat >> "$CLAUDE_MD" << 'HEREDOC'

# === CLAUDE HQ ===
# Central command center for all major projects.
# Repository: https://github.com/SUNMANOFFICIAL189/CLAUDE-HQ

## CLAUDE HQ Activation Protocol

For ANY major project (especially when a PRD is provided), fetch and activate CLAUDE HQ:

1. Fetch the master protocol: https://raw.githubusercontent.com/SUNMANOFFICIAL189/CLAUDE-HQ/main/.claude/AGENTS.md
2. Fetch the tool registry: https://raw.githubusercontent.com/SUNMANOFFICIAL189/CLAUDE-HQ/main/registry.json
3. Follow the Tool Selection Algorithm in AGENTS.md
4. Present activation plan to user

## Auto-Trigger Rules
- PRD provided → immediately activate full prd-full-build stack
- "Build me X" → activate autonomous-agent-system + claude-mem
- Multi-session project → activate token-efficiency at minimum
- User says "activate HQ" or "claude hq" → fetch and load full system

## Quick Reference
- 6 registered tools (2 owned, 4 external)
- 5 predefined tool combinations
- System evolves — push improvements via [HQ-EVOLVE] commits

## Evolution
If you identify improvements to CLAUDE HQ during any session:
1. Propose the improvement to the user
2. Push to github.com/SUNMANOFFICIAL189/CLAUDE-HQ with [HQ-EVOLVE] commit
# === END CLAUDE HQ ===
HEREDOC

echo "✅ CLAUDE HQ block added to $CLAUDE_MD"
echo ""
echo "How it works:"
echo "  • Every Claude Code session now knows about CLAUDE HQ"
echo "  • For major projects, Claude will auto-fetch the full system"
echo "  • Say 'activate HQ' or provide a PRD to trigger it"
echo ""
echo "🚀 Ready. Start Claude Code in any project directory."
