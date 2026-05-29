# Hermes Agent — Install Guide

## Quick Install

```bash
# From the meta-ads-analyzer repo root
hermes skills install meta-ads-analyzer --from .
```

Or manually:

```bash
mkdir -p ~/.hermes/skills/meta-ads-analyzer
cp SKILL.md ~/.hermes/skills/meta-ads-analyzer/
cp -r references/ ~/.hermes/skills/meta-ads-analyzer/references/
```

## MCP Setup (Optional — Live API Data)

1. Run the setup script to configure Meta API credentials:

```bash
bash scripts/setup.sh
```

2. The script creates `.env.meta-ads` with your credentials. Add the MCP server to your Hermes `config.yaml`:

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  meta-ads:
    command: npx
    args: ["-y", "meta-ads-mcp"]
    env:
      META_ACCESS_TOKEN: "${META_ACCESS_TOKEN}"
      META_APP_SECRET: "${META_APP_SECRET}"
```

3. Restart Hermes.

## Usage

Once installed, ask Hermes:

- "Analizá mis campañas de Meta Ads de los últimos 7 días"
- "¿Por qué está subiendo el CPA en esta campaña?"
- "Compará performance entre placements"
- "Diagnosticá por qué este ad set está en Learning Limited"
- "Generá un reporte completo de análisis para [nombre de campaña]"

You can also paste CSV exports or screenshots from Meta Ads Manager — the skill works with any data format.
