# Meta Ads Analyzer for Claude Code

A Claude Code skill + MCP server setup for expert-level Meta Ads campaign analysis. Includes the **Breakdown Effect** framework, Learning Phase diagnostics, and 9 reference documents from Meta's official documentation.

## What It Does

When installed, Claude Code can:

- Analyze campaign, ad set, and ad-level performance data
- Identify root causes of performance issues using Meta's system mechanics
- Explain the **Breakdown Effect** (why Meta allocates budget to seemingly "worse" segments)
- Diagnose Learning Phase, Auction Overlap, Pacing, and Creative Fatigue issues
- Generate structured analysis reports with actionable recommendations
- Connect directly to Meta's API to pull live campaign data (via MCP)

## Components

| Component | What it does |
|---|---|
| **Skill** (`skill/`) | Analysis framework with 9 reference docs that Claude loads as context |
| **MCP Server** (`mcp/`) | Connects Claude Code to Meta's Marketing API for live data |
| **Scripts** (`scripts/`) | Setup and token refresh helpers |

## Integration review and Codex compatibility

The MCP configuration launches the external npm package `meta-ads-mcp`; its server implementation is not bundled in this repository. That package includes campaign-management tools as well as reporting tools.

See [the integration audit and Codex compatibility notes](docs/compatibility-and-security-review.md) for reproduced reporting and OAuth defects, credential-handling improvements, validation limits, and a proposed Codex configuration. Review these findings before connecting a live account; this documentation does not patch the external server.

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [Node.js](https://nodejs.org/) v18+
- A Meta App with Marketing API access ([create one here](https://developers.facebook.com/apps/))

## Installation

### 1. Install the Skill

Copy the `skill/` folder into your Claude Code project:

```bash
# From your Claude Code project root
mkdir -p .claude/skills/meta-ads-analyzer
cp -r skill/* .claude/skills/meta-ads-analyzer/
```

The skill is now active. Claude will automatically use it when you ask about Meta Ads analysis.

### 2. Set Up the MCP Server (optional, for live data)

The MCP server lets Claude pull live campaign data from Meta's API. Skip this if you only want to analyze exported data (CSV, screenshots).

#### a) Create a Meta App

1. Go to [developers.facebook.com](https://developers.facebook.com/apps/)
2. Create a new app (type: **Business**)
3. Add the **Marketing API** product
4. Note your **App ID** and **App Secret**

#### b) Generate an Access Token

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app
3. Add permissions: `ads_read`, `ads_management`, `business_management`
4. Click **Generate Access Token** and authorize
5. Exchange for a long-lived token (60 days) using the setup script:

```bash
bash scripts/setup.sh
```

#### c) Configure Claude Code

Copy the MCP config template and add your credentials:

```bash
cp mcp/mcp.json.example .mcp.json
```

Edit `.mcp.json` and replace the placeholders with your actual token and app secret.

Then restart Claude Code for the MCP server to connect.

### 3. Verify

Ask Claude: **"Analyze my Meta Ads campaigns"** — it should connect to your ad account and start analyzing.

## Token Refresh

Meta long-lived tokens expire after ~60 days. To refresh:

```bash
bash scripts/refresh_token.sh
```

If the token already expired, generate a new one from the [Graph API Explorer](https://developers.facebook.com/tools/explorer/) and run `scripts/setup.sh` again.

## Usage Examples

Once installed, you can ask Claude things like:

- "Analyze my campaigns from the last 7 days"
- "Why is my CPA increasing on this campaign?"
- "Compare performance across placements"
- "Diagnose why this ad set is in Learning Limited"
- "Export a full analysis report for [campaign name]"

You can also paste CSV exports or screenshots from Meta Ads Manager — the skill works with any data format.

## What's in the Reference Docs

| Document | Covers |
|---|---|
| `breakdown_effect.md` | Why Meta allocates budget to "expensive" segments |
| `core_concepts.md` | Ad Auction, Pacing, Learning Phase overview |
| `learning_phase.md` | How learning works, when it resets |
| `ad_relevance_diagnostics.md` | Quality, Engagement, Conversion rankings |
| `auction_overlap.md` | When your ads compete against each other |
| `pacing.md` | Budget and bid pacing mechanics |
| `bid_strategies.md` | Spend-based, goal-based, manual bidding |
| `ad_auctions.md` | How auction winners are determined |
| `performance_fluctuations.md` | Normal vs. concerning performance changes |

## License

MIT
