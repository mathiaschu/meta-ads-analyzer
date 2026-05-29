# Claude Code — Install Guide

## Quick Install

```bash
# From the meta-ads-analyzer repo root
mkdir -p .claude/skills/meta-ads-analyzer
cp platforms/claude-code/SKILL.md .claude/skills/meta-ads-analyzer/
cp -r references/ .claude/skills/meta-ads-analyzer/references/
```

Or use the universal installer:

```bash
bash scripts/install.sh claude-code
```

## MCP Setup (Optional — Live API Data)

1. Run setup:

```bash
bash scripts/setup.sh
```

2. This creates `.mcp.json` automatically. Restart Claude Code.

## Usage

Ask Claude:

- "Analyze my Meta Ads campaigns from the last 7 days"
- "Why is my CPA increasing on this campaign?"
- "Compare performance across placements"
- "Diagnose why this ad set is in Learning Limited"
- "Export a full analysis report for [campaign name]"
