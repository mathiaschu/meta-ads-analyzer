#!/bin/bash
# Meta Ads MCP - Interactive Setup
# Run: bash scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Meta Ads MCP Setup ==="
echo ""

# Collect credentials
read -p "Paste your Meta Access Token: " META_TOKEN
read -p "Paste your App Secret: " META_SECRET
read -p "Paste your App ID (optional, Enter to skip): " META_APP_ID

if [ -z "$META_TOKEN" ] || [ -z "$META_SECRET" ]; then
    echo "ERROR: Token and App Secret are required."
    exit 1
fi

# Save to local .env (not committed thanks to .gitignore)
ENV_FILE="$PROJECT_DIR/.env.meta-ads"

cat > "$ENV_FILE" << EOF
# Meta Ads MCP Credentials
# Generated: $(date '+%Y-%m-%d %H:%M')
# DO NOT COMMIT THIS FILE
export META_ACCESS_TOKEN="$META_TOKEN"
export META_APP_SECRET="$META_SECRET"
export META_APP_ID="$META_APP_ID"
EOF

echo ""
echo "Credentials saved to .env.meta-ads"

# Create .mcp.json in project root
MCP_FILE="$PROJECT_DIR/.mcp.json"

cat > "$MCP_FILE" << EOF
{
  "mcpServers": {
    "meta-ads": {
      "command": "npx",
      "args": ["-y", "meta-ads-mcp"],
      "env": {
        "META_ACCESS_TOKEN": "$META_TOKEN",
        "META_APP_SECRET": "$META_SECRET"
      }
    }
  }
}
EOF

echo ".mcp.json created"
echo ""

# Quick connection test
echo "Testing connection to Meta API..."
RESPONSE=$(curl -s -G -d "access_token=$META_TOKEN" "https://graph.facebook.com/v21.0/me/adaccounts?fields=name,account_id,account_status&limit=5")

if echo "$RESPONSE" | grep -q "error"; then
    echo "ERROR: Could not connect. Check your token."
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
else
    echo "CONNECTION SUCCESSFUL! Ad accounts found:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
fi

echo ""
echo "Restart Claude Code for the MCP server to connect."
