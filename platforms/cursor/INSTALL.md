# Cursor — Install Guide

## Quick Install

```bash
# From the meta-ads-analyzer repo root
mkdir -p .cursor/rules
cp platforms/cursor/meta-ads-analyzer.mdc .cursor/rules/
cp -r references/ .cursor/rules/references/
```

Or use the universal installer:

```bash
bash scripts/install.sh cursor
```

## MCP Setup (Optional)

Cursor supports MCP via VS Code settings. Add to `.vscode/settings.json`:

```json
{
  "mcpServers": {
    "meta-ads": {
      "command": "npx",
      "args": ["-y", "meta-ads-mcp"],
      "env": {
        "META_ACCESS_TOKEN": "${env:META_ACCESS_TOKEN}",
        "META_APP_SECRET": "${env:META_APP_SECRET}"
      }
    }
  }
}
```

Run `bash scripts/setup.sh` first to configure credentials.

## Usage

Ask Cursor in chat/composer:

- "Analyze my Meta Ads campaigns from the last 7 days"
- "Why is my CPA increasing?"
- "Generate a full analysis report"
