#!/bin/bash
# Refresh Meta Ads long-lived token
# Run when token is about to expire (~every 55 days)
# Usage: bash scripts/refresh_token.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env.meta-ads"
MCP_FILE="$PROJECT_DIR/.mcp.json"

# Load current credentials
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env.meta-ads not found. Run setup.sh first."
    exit 1
fi

source "$ENV_FILE"

if [ -z "$META_ACCESS_TOKEN" ] || [ -z "$META_APP_ID" ] || [ -z "$META_APP_SECRET" ]; then
    echo "ERROR: Missing credentials in .env.meta-ads"
    echo "Make sure META_ACCESS_TOKEN, META_APP_ID, and META_APP_SECRET are set."
    exit 1
fi

echo "Refreshing Meta Ads token..."

# Exchange for new long-lived token
RESPONSE=$(curl -s "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=$META_APP_ID&client_secret=$META_APP_SECRET&fb_exchange_token=$META_ACCESS_TOKEN")

NEW_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
EXPIRES=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('expires_in',''))" 2>/dev/null)

if [ -z "$NEW_TOKEN" ]; then
    echo "ERROR: Could not refresh token."
    echo "Response: $RESPONSE"
    echo ""
    echo "You may need to generate a new token from:"
    echo "  https://developers.facebook.com/tools/explorer/"
    echo "Then run: bash scripts/setup.sh"
    exit 1
fi

DAYS=$((EXPIRES / 86400))

# Update .env.meta-ads
cat > "$ENV_FILE" << EOF
# Meta Ads MCP Credentials
# Refreshed: $(date '+%Y-%m-%d %H:%M')
# Long-lived token expires in ~$DAYS days
# To refresh: bash scripts/refresh_token.sh
# DO NOT COMMIT THIS FILE
export META_ACCESS_TOKEN="$NEW_TOKEN"
export META_APP_ID="$META_APP_ID"
export META_APP_SECRET="$META_APP_SECRET"
EOF

# Update .mcp.json
cat > "$MCP_FILE" << EOF
{
  "mcpServers": {
    "meta-ads": {
      "command": "npx",
      "args": ["-y", "meta-ads-mcp"],
      "env": {
        "META_ACCESS_TOKEN": "$NEW_TOKEN",
        "META_APP_SECRET": "$META_APP_SECRET"
      }
    }
  }
}
EOF

echo "Token refreshed successfully!"
echo "  Expires in ~$DAYS days"
echo ""
echo "Restart Claude Code for the new token to take effect."
