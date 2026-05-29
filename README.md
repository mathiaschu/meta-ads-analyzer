# Meta Ads Analyzer — Multi-Platform AI Skill

Expert-level Meta Ads campaign analysis skill for AI coding platforms. Includes the **Breakdown Effect** framework, Learning Phase diagnostics, and 9 reference documents from Meta's official documentation.

## Supported Platforms

| Platform | Install Command | Type |
|:---------|:---------------|:-----|
| **Hermes Agent** | `bash scripts/install.sh hermes` | Skill |
| **Claude Code** | `bash scripts/install.sh claude-code` | Skill |
| **Cursor** | `bash scripts/install.sh cursor` | Rules |
| **GitHub Copilot** | `bash scripts/install.sh copilot` | Instructions |
| **OpenCode** | `bash scripts/install.sh opencode` | Skill |
| **Windsurf** | `bash scripts/install.sh windsurf` | Rules |
| **Aider** | `bash scripts/install.sh aider` | Rules |

Install all at once: `bash scripts/install.sh all`

## What It Does

When installed on any supported platform, the AI can:

- Analyze campaign, ad set, and ad-level performance data
- Identify root causes of performance issues using Meta's system mechanics
- Explain the **Breakdown Effect** (why Meta allocates budget to seemingly "worse" segments)
- Diagnose Learning Phase, Auction Overlap, Pacing, and Creative Fatigue issues
- Generate structured analysis reports with actionable recommendations
- Connect directly to Meta's API to pull live campaign data (via MCP)

## Quick Start

### 1. Install for your platform

```bash
# Clone the repo
git clone https://github.com/jfiscman/meta-ads-analyzer.git
cd meta-ads-analyzer

# Install
bash scripts/install.sh hermes        # or: claude-code, cursor, copilot, etc.
```

> **Note on install location:** `hermes` and `opencode` install into your home
> directory (`~/.hermes`, `~/.opencode`) and work from anywhere. The
> project-scoped platforms (`claude-code`, `cursor`, `copilot`, `windsurf`,
> `aider`) install into the **current working directory** — run their install
> command from the root of the project you want the skill available in, not
> from inside this cloned repo.

### 2. Set up MCP (optional, for live API data)

```bash
bash scripts/setup.sh
```

Enter your Meta Access Token and App Secret when prompted. The script auto-configures the MCP server for your platform.

### 3. Start analyzing

Ask your AI assistant:

- "Analyze my Meta Ads campaigns from the last 7 days"
- "Why is my CPA increasing on this campaign?"
- "Compare performance across placements"
- "Diagnose why this ad set is in Learning Limited"
- "Export a full analysis report for [campaign name]"

You can also paste CSV exports or screenshots from Meta Ads Manager — the skill works with any data format.

## Repository Structure

```
meta-ads-analyzer/
├── SKILL.md                    ← Platform-agnostic skill definition
├── references/                 ← 9 domain knowledge docs (shared by all platforms)
│   ├── breakdown_effect.md     ← The Breakdown Effect (READ FIRST)
│   ├── core_concepts.md        ← Ad Auction, Pacing, Learning Phase
│   ├── learning_phase.md       ← Learning phase mechanics
│   ├── ad_relevance_diagnostics.md
│   ├── auction_overlap.md
│   ├── pacing.md
│   ├── bid_strategies.md
│   ├── ad_auctions.md
│   └── performance_fluctuations.md
├── platforms/                  ← Platform-specific adapters
│   ├── hermes/                 ← Hermes Agent skill
│   ├── claude-code/            ← Claude Code skill
│   ├── cursor/                 ← Cursor rules
│   ├── copilot/                ← GitHub Copilot instructions
│   ├── opencode/               ← OpenCode skill
│   ├── windsurf/               ← Windsurf rules
│   └── aider/                  ← Aider rules
├── mcp/                        ← MCP server config (multi-platform)
├── scripts/                    ← Setup & install scripts
│   ├── install.sh              ← Universal installer
│   ├── setup.sh                ← Meta API credential setup
│   └── refresh_token.sh        ← Token refresh (~60 days)
└── README.md
```

## Prerequisites

- Node.js v18+
- A Meta App with Marketing API access ([create one here](https://developers.facebook.com/apps/))

## Reference Documents

| # | Document | Covers |
|---|----------|--------|
| 1 | `breakdown_effect.md` | Why Meta allocates budget to "expensive" segments — **READ FIRST** |
| 2 | `core_concepts.md` | Ad Auction, Pacing, Learning Phase overview |
| 3 | `learning_phase.md` | How learning works, when it resets |
| 4 | `ad_relevance_diagnostics.md` | Quality, Engagement, Conversion rankings |
| 5 | `auction_overlap.md` | When your ads compete against each other |
| 6 | `pacing.md` | Budget and bid pacing mechanics |
| 7 | `bid_strategies.md` | Spend-based, goal-based, manual bidding |
| 8 | `ad_auctions.md` | How auction winners are determined |
| 9 | `performance_fluctuations.md` | Normal vs. concerning performance changes |

## The Breakdown Effect

The signature concept of this skill. Meta's delivery system optimizes for **marginal efficiency**, not average efficiency. A segment with higher average CPA may be protecting overall campaign efficiency by preventing even higher marginal costs elsewhere.

**Never judge system decisions by average CPA in breakdown reports alone.**

## Token Refresh

Meta long-lived tokens expire after ~60 days:

```bash
bash scripts/refresh_token.sh
```

## License

MIT — Copyright (c) 2026 Mathias Chu
