---
name: meta-ads-analyzer
description: "Provides expert-level analysis and diagnosis for Meta Ads campaigns. Use this skill to interpret performance data, identify root causes of issues, and generate actionable recommendations, with a special focus on correctly handling the 'Breakdown Effect'. Use when the user mentions Meta Ads analysis, campaign diagnosis, ad performance, CPA analysis, ROAS analysis, or asks to analyze exported data from Meta Ads Manager."
---

# Meta Ads Analysis & Diagnosis Skill

## When to Use This Skill

Use this skill when you need to **analyze and diagnose Meta Ads campaign performance**, including:
- Interpreting campaign, ad set, or ad-level performance data
- Identifying root causes of performance issues
- Generating actionable optimization recommendations
- Understanding why Meta's system makes certain budget allocation decisions
- Analyzing CSV exports, screenshots, or raw data from Meta Ads Manager

## Result Recommendations (MANDATORY for Final Reports)

> **IMPORTANT:** The following rules are **MANDATORY** and **MUST be strictly followed** when writing the final analysis report. These are not optional guidelines — they define the required standards for all deliverables.

- **NEVER recommend pausing or reducing budget for any segment based solely on higher average CPA/CPM in breakdown reports.** Higher average cost does NOT mean poor performance — it often reflects the system capturing low *marginal* cost opportunities earlier. Removing segments may increase overall costs. Always frame changes as testable hypotheses, not directives.
- **ALWAYS justify recommendations with data evidence, Meta's system mechanics, and expected impact on *overall campaign performance*.**
- **EVERY insight must include data evidence and explanation.** Every recommendation must be actionable and verifiable.
- **ALIGN WITH OFFICIAL RECOMMENDATIONS.** Check `get_recommendations` API first. If diverging, explicitly acknowledge and explain why.
- **Disambiguate clicks.** Never use the term "clicks" alone. Use "Clicks (all)" for total interactions (likes, shares, page clicks, link clicks) or "Link Clicks" for clicks that lead offsite; these are distinct metrics with different meanings.
- **Audience size:** When reporting reach or audience size, use "Accounts Center accounts" or the number without unit — never "people" — per legal requirements.

## Metric Naming Guidelines

**IMPORTANT:** Always rename metric names to standardized, non-sensitive names exactly as specified below in all responses:

| Raw Metric Name | Standardized Display Name |
| :--- | :--- |
| `impressions` | Impressions |
| `video_thruplay_watched_actions` | ThruPlays |
| `clicks` | Clicks (all) |
| `purchase_roas` | Purchase ROAS (return on ad spend) |
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

## Core Principles

- **Holistic First:** Evaluate at aggregate level before drilling down. The system optimizes for the whole, not the parts.
- **Dynamic over Static:** Analyze performance over time, not single snapshots.
- **Marginal over Average:** The system prioritizes marginal CPA (cost of the *next* result), not average CPA. A higher average CPA segment might be preventing even higher marginal costs elsewhere.

## Meta Ads Domain Knowledge

### Legal Requirements & Terminology

- **Audience Size Metrics:** Due to legal requirements, when referring to audience size metrics (the total number of accounts that view the ad), you must use "Accounts Center accounts" (case insensitive) or report the metric without any unit instead of "people".
- **"People" Usage:** When "people" is used in contexts referring to audience size, replace with "Accounts Center accounts". When a **specific number** is used with "people" (e.g., "17,000 people"), use **"person"** after the number (e.g., "17,000 person").

### Campaign & Performance Definitions

- **Conversion Ads:** Ad entities with objectives like Lead, Sales, or App Promotions are categorized as conversion ads.
- **Conversion Rate:** Conversion rate = conversions / impressions.
- **Performance Indicators:** Lower Cost Per Result or CPM = higher performance. Higher ROAS = higher performance.

### Account & Asset Issues

- **Disabled or Restricted Account:** Occurs when assets (FB account, IG account, ad account, page, payout account) have been disabled or restricted by Meta, usually due to policy violations.

### Budget & Billing

- **Daily Spending Limit (DSL):** The current daily spending limit that advertisers can check, increase, or decrease.
- **Billing Threshold (Payment Threshold):** The amount of ad spend that triggers a payment method charge when reached.

## Analysis Workflow

**Reference Documents** (loaded automatically from `references/`):
- `breakdown_effect.md` - The Breakdown Effect with examples (READ THIS FIRST)
- `core_concepts.md` - Ad Auction, Pacing, Learning Phase overview
- `learning_phase.md` - Learning phase mechanics
- `ad_relevance_diagnostics.md` - Quality, Engagement, Conversion rankings
- `auction_overlap.md` - Diagnosing auction overlap
- `pacing.md` - Budget and bid pacing
- `bid_strategies.md` - Spend-based, goal-based, manual bidding
- `ad_auctions.md` - How auction winners are determined
- `performance_fluctuations.md` - Normal vs. concerning fluctuations

### Step 1: Identify the Correct Evaluation Level

This is the most critical step to avoid the Breakdown Effect.

| Campaign Setup | Correct Evaluation Level |
| :--- | :--- |
| Advantage+ Campaign Budget (CBO) | **Campaign Level** |
| Automatic Placements (without CBO) | **Ad Set Level** |
| Multiple Ads within a single Ad Set | **Ad Set Level** |

### Step 2: Check Learning Phase Status

Before any analysis:
- Is the ad set still in learning phase? (~50 optimization events needed)
- Were there recent significant edits that reset learning?
- If in learning: caveat all findings as preliminary

### Step 3: Analyze with Meta-Specific Lens

Focus on these analytical angles:

1. **Marginal Efficiency Analysis:** Infer marginal CPA trends from time-series data. A segment with low average CPA but rising marginal CPA explains why the system shifts budget away.
2. **Ad Relevance Diagnostics:** Check Quality, Engagement, and Conversion Rate Rankings to diagnose creative, targeting, or post-click issues.
3. **Auction Overlap Check:** Are ad sets competing against each other? Look for learning limited status and underdelivery.
4. **Pacing Analysis:** Is the system holding back budget for better opportunities? Evaluate over full campaign, not daily snapshots.
5. **Performance Fluctuation Assessment:** Is this normal variation (20-30% day-to-day) or a concerning trend (>50% sustained)?

### Step 4: Synthesize Findings Through Breakdown Effect Lens

Interpret ALL findings through the **Breakdown Effect** framework. Explain *why* the system makes certain decisions.

> **Example:** "While Placement A shows $10 average CPA vs Placement B's $15, time-series analysis reveals Placement A's CPA rising sharply — its marginal CPA likely exceeds Placement B's. The system correctly shifts budget to secure more conversions at lower marginal cost."

### Step 5: Generate Report

Structure every analysis report as:

1. **Executive Summary** - 2-3 key findings
2. **Evaluation Level** - Which level and why
3. **Learning Phase Status** - Current state per ad set
4. **Performance Analysis** - Metrics with proper naming
5. **Diagnosis** - Root causes with evidence
6. **Recommendations** - Actionable, with expected impact, framed as testable hypotheses
7. **Breakdown Effect Notes** - Explicit callouts where this applies
