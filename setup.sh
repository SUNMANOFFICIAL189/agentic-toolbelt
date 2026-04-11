#!/bin/bash
# CLAUDE HQ — JARVIS Setup Script
# Run this ONCE in your regular terminal (not inside Claude Code).
# It adds JARVIS/Commander awareness to your global Claude Code config.
#
# Usage: 
#   git clone https://github.com/SUNMANOFFICIAL189/CLAUDE-HQ.git ~/claude-hq
#   bash ~/claude-hq/setup.sh

set -e

CLAUDE_DIR="$HOME/.claude"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
HQ_MARKER="# === CLAUDE HQ — JARVIS ==="

echo "🏢 CLAUDE HQ — JARVIS Setup"
echo "============================"

mkdir -p "$CLAUDE_DIR"

# Remove old HQ block if present
if [ -f "$CLAUDE_MD" ] && grep -q "# === CLAUDE HQ ===" "$CLAUDE_MD" 2>/dev/null; then
    echo "🔄 Removing old CLAUDE HQ block..."
    sed -i '' '/# === CLAUDE HQ ===/,/# === END CLAUDE HQ ===/d' "$CLAUDE_MD" 2>/dev/null || true
fi

if [ -f "$CLAUDE_MD" ] && grep -q "$HQ_MARKER" "$CLAUDE_MD" 2>/dev/null; then
    echo "✅ JARVIS is already configured in $CLAUDE_MD"
    exit 0
fi

cat >> "$CLAUDE_MD" << 'HEREDOC'

# === CLAUDE HQ — JARVIS ===
# Central command center: ~/claude-hq/commander/COMMANDER.md
# Repository: https://github.com/SUNMANOFFICIAL189/CLAUDE-HQ

## When working inside ~/claude-hq:
AGENTS.md loads automatically. On session start:
1. Read commander/LESSONS.md (past mistakes)
2. Read registry.json (25 tools, 11 stacks)
3. Classify the user's task
4. For non-trivial tasks: load commander/COMMANDER.md and follow its protocol
5. Auto-activate the right tools by running install commands

## When working in ANY other directory:
If the user says "activate HQ", provides a PRD, or starts a major project:
1. cd ~/claude-hq && cat commander/COMMANDER.md (load the brain)
2. cat commander/LESSONS.md (check past mistakes)
3. cat registry.json (load tool inventory)
4. Classify task against registry
5. Clone/install matching tools
6. Return to project directory and begin work

## Auto-Trigger Rules
- PRD provided → Commander activation → PRD Full Build Stack
- "Build me X" → Commander activation → Full Project Build Stack
- "Design a website" → Commander → Web Design Stack
- "Create a video" → Commander → Video Production Stack
- "Creative brief" → Commander → Full Creative Brief Stack
- "Research X" → Commander → Research Stack
- "activate HQ" → Load full Commander + registry

## Core Principles (always active)
- Zero cost first — free alternatives before paid options
- Cheapest viable model — Haiku/Sonnet/Opus based on complexity
- Never store credentials in plain text or commit to git
- Plan before execute — mission board before agents spawn
- Learn from mistakes — update LESSONS.md after corrections
# === END CLAUDE HQ — JARVIS ===
HEREDOC

echo "✅ JARVIS block added to $CLAUDE_MD"
echo ""
echo "Now run:"
echo "  cd ~/claude-hq && claude"
echo ""
echo "Or from any project: say 'activate HQ' to load JARVIS."
