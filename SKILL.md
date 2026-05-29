---
name: meta-ads-analyzer
description: "Expert-level analysis and diagnosis for Meta Ads campaigns. Analyzes performance data, identifies root causes, and generates actionable recommendations using the Breakdown Effect framework. Use when analyzing Meta Ads campaigns, diagnosing CPA/ROAS issues, or interpreting exported data from Meta Ads Manager."
version: 2.0.0
author: Mathias Chu
license: MIT
platforms:
  - hermes
  - claude-code
  - cursor
  - copilot
  - opencode
  - windsurf
  - aider
tags:
  - meta-ads
  - facebook-ads
  - campaign-analysis
  - marketing
  - performance-diagnosis
  - breakdown-effect
  - cpa-analysis
  - roas-analysis
  - mcp
prerequisites:
  commands:
    - node (v18+)
    - npx
metadata:
  hermes:
    skill_type: analysis
    mcp_required: false
    mcp_optional: true
---

# Meta Ads Analysis & Diagnosis Skill

Multi-platform skill for analyzing Meta Ads campaign performance. Works across Hermes, Claude Code, Cursor, GitHub Copilot, OpenCode, Windsurf, and Aider.

## When to Use

Use this skill when you need to **analyze and diagnose Meta Ads campaign performance**, including:
- Interpreting campaign, ad set, or ad-level performance data
- Identifying root causes of performance issues
- Generating actionable optimization recommendations
- Understanding why Meta's system makes certain budget allocation decisions
- Analyzing CSV exports, screenshots, or raw data from Meta Ads Manager

## Domain Knowledge (Mandatory Reading)

Load these reference documents in order for complete domain understanding:

| # | Document | Covers |
|---|----------|--------|
| 1 | `references/breakdown_effect.md` | Why Meta allocates budget to "expensive" segments — **READ FIRST** |
| 2 | `references/core_concepts.md` | Ad Auction, Pacing, Learning Phase overview |
| 3 | `references/learning_phase.md` | How learning works, when it resets |
| 4 | `references/ad_relevance_diagnostics.md` | Quality, Engagement, Conversion rankings |
| 5 | `references/auction_overlap.md` | When your ads compete against each other |
| 6 | `references/pacing.md` | Budget and bid pacing mechanics |
| 7 | `references/bid_strategies.md` | Spend-based, goal-based, manual bidding |
| 8 | `references/ad_auctions.md` | How auction winners are determined |
| 9 | `references/performance_fluctuations.md` | Normal vs. concerning performance changes |

## Core Principles

- **Holistic First:** Evaluate at aggregate level before drilling down. The system optimizes for the whole, not the parts.
- **Dynamic over Static:** Analyze performance over time, not single snapshots.
- **Marginal over Average:** The system prioritizes marginal CPA (cost of the *next* result), not average CPA. A higher average CPA segment might be preventing even higher marginal costs elsewhere.

## Result Recommendations (MANDATORY for Final Reports)

> **IMPORTANT:** These rules are **MANDATORY** and **MUST be strictly followed** when writing the final analysis report.

- **NEVER recommend pausing or reducing budget for any segment based solely on higher average CPA/CPM in breakdown reports.** Higher average cost does NOT mean poor performance — it often reflects the system capturing low *marginal* cost opportunities earlier. Removing segments may increase overall costs. Always frame changes as testable hypotheses, not directives.
- **ALWAYS justify recommendations with data evidence, Meta's system mechanics, and expected impact on *overall campaign performance*.**
- **EVERY insight must include data evidence and explanation.** Every recommendation must be actionable and verifiable.
- **ALIGN WITH OFFICIAL RECOMMENDATIONS.** Check `get_recommendations` API first. If diverging, explicitly acknowledge and explain why.
- **Disambiguate clicks.** Never use the term "clicks" alone. Use "Clicks (all)" for total interactions or "Link Clicks" for clicks that lead offsite.
- **Audience size:** Use "Accounts Center accounts" or the number without unit — never "people" — per legal requirements.

## Metric Naming Guidelines

**IMPORTANT:** Always rename metrics to standardized names:

| Raw Metric | Standardized Name |
|:-----------|:------------------|
| `impressions` | Impressions |
| `video_thruplay_watched_actions` | ThruPlays |
| `clicks` | Clicks (all) |
| `purchase_roas` | Purchase ROAS |
| `cpm` | CPM |
| `cpc` | CPC (all) |
| `ctr` | CTR (all) |
| `cost_per_action_type:link_click` | CPC (Link Click) |
| `outbound_clicks_ctr` | Outbound CTR |
| `cost_per_action_type:purchase` | Cost per Purchase |
| `actions:purchase` | Purchases |
| `action_values:purchase` | Purchase Value |
| `frequency` | Frequency |
| `reach` | Reach (Accounts Center accounts) |
| `spend` | Amount Spent |

## Legal Requirements

- **Audience Size Metrics:** Use "Accounts Center accounts" or report the metric without any unit instead of "people".
- **"People" Usage:** When a specific number is used with "people" (e.g., "17,000 people"), use "person" after the number (e.g., "17,000 person").

## Campaign & Performance Definitions

- **Conversion Ads:** Ad entities with objectives like Lead, Sales, or App Promotions.
- **Conversion Rate:** conversions / impressions.
- **Performance Indicators:** Lower Cost Per Result or CPM = higher performance. Higher ROAS = higher performance.

## Analysis Workflow

### Step 1: Identify the Correct Evaluation Level

This is the most critical step to avoid the Breakdown Effect.

| Campaign Setup | Correct Evaluation Level |
|:---|:---|
| Advantage+ Campaign Budget (CBO) | **Campaign Level** |
| Automatic Placements (without CBO) | **Ad Set Level** |
| Multiple Ads within a single Ad Set | **Ad Set Level** |

### Step 2: Check Learning Phase Status

Before any analysis:
- Is the ad set still in learning phase? (~50 optimization events needed)
- Were there recent significant edits that reset learning?
- If in learning: caveat all findings as preliminary

### Step 3: Analyze with Meta-Specific Lens

1. **Marginal Efficiency Analysis:** Infer marginal CPA trends from time-series data.
2. **Ad Relevance Diagnostics:** Check Quality, Engagement, and Conversion Rate Rankings.
3. **Auction Overlap Check:** Are ad sets competing against each other?
4. **Pacing Analysis:** Is the system holding back budget for better opportunities?
5. **Performance Fluctuation Assessment:** Normal variation (20-30%) vs. concerning trend (>50% sustained)?

### Step 4: Synthesize Through Breakdown Effect Lens

Interpret ALL findings through the **Breakdown Effect** framework. Explain *why* the system makes certain decisions.

> **Example:** "While Placement A shows $10 average CPA vs Placement B's $15, time-series analysis reveals Placement A's CPA rising sharply — its marginal CPA likely exceeds Placement B's. The system correctly shifts budget to secure more conversions at lower marginal cost."

### Step 5: Generate Report

Structure every analysis report as:

1. **Executive Summary** — 2-3 key findings
2. **Evaluation Level** — Which level and why
3. **Learning Phase Status** — Current state per ad set
4. **Performance Analysis** — Metrics with proper naming
5. **Diagnosis** — Root causes with evidence
6. **Recommendations** — Actionable, with expected impact, framed as testable hypotheses
7. **Breakdown Effect Notes** — Explicit callouts where this applies

## MCP Server (Optional — Live API Data)

An MCP server (`meta-ads-mcp` on npm) connects directly to Meta's Marketing API v21.0 for live campaign data. See `mcp/` for configuration templates.

**Required permissions:** `ads_read`, `ads_management`, `business_management`
