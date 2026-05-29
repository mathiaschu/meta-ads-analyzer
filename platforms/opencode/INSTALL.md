# OpenCode — Install Guide

## Quick Install

```bash
# From the meta-ads-analyzer repo root
mkdir -p ~/.opencode/skills/meta-ads-analyzer
cp platforms/opencode/SKILL.md ~/.opencode/skills/meta-ads-analyzer/
cp -r references/ ~/.opencode/skills/meta-ads-analyzer/references/
```

Or use the universal installer:

```bash
bash scripts/install.sh opencode
```

## MCP Setup (Optional)

OpenCode supports MCP servers. Configure in OpenCode settings.

Run `bash scripts/setup.sh` first to configure credentials.

## Usage

Ask OpenCode:

- "Analyze my Meta Ads campaigns"
- "Why is CPA increasing?"
- "Generate a full diagnosis report"
