# GitHub Copilot — Install Guide

## Quick Install

Add the instructions to your project:

```bash
# From the meta-ads-analyzer repo root
cp platforms/copilot/copilot-instructions.md .github/copilot-instructions.md
```

Or use the universal installer:

```bash
bash scripts/install.sh copilot
```

## Optional: VS Code Settings

Add to `.vscode/settings.json`:

```json
{
  "github.copilot.chat.codeGeneration.instructions": [
    { "file": ".github/copilot-instructions.md" }
  ]
}
```

## Usage

Copilot will automatically follow the Meta Ads rules when analyzing campaign data in chat or inline.

Ask Copilot Chat:

- "Analyze this Meta Ads campaign data"
- "Why is my CPA increasing?"
- "Diagnose learning limited ad sets"
