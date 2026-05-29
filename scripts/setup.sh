#!/bin/bash
# Meta Ads MCP - Interactive Setup
# Run: bash scripts/setup.sh

set -e
set -o pipefail

# Meta Graph API version — bump here in one place when Meta deprecates it.
API_VERSION="v21.0"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Meta Ads MCP Setup ==="
echo ""

# Collect credentials.
# App ID is required: refresh_token.sh needs it to exchange long-lived tokens.
read -p "Paste your Meta Access Token: " META_TOKEN
read -p "Paste your App Secret: " META_SECRET
read -p "Paste your App ID: " META_APP_ID

if [ -z "$META_TOKEN" ] || [ -z "$META_SECRET" ] || [ -z "$META_APP_ID" ]; then
    echo "ERROR: Access Token, App Secret, and App ID are all required."
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
# --data-urlencode encodes the token correctly even if it contains special chars.
RESPONSE=$(curl -s -G \
    --data-urlencode "access_token=$META_TOKEN" \
    --data-urlencode "fields=name,account_id,account_status" \
    --data-urlencode "limit=5" \
    "https://graph.facebook.com/$API_VERSION/me/adaccounts")

# Match the JSON "error" key specifically, not the substring "error"
# (a valid account name could legitimately contain that word).
if echo "$RESPONSE" | grep -q '"error"'; then
    echo "ERROR: Could not connect. Check your token."
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
else
    echo "CONNECTION SUCCESSFUL! Ad accounts found:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
fi

echo ""
echo "Restart Claude Code for the MCP server to connect."
