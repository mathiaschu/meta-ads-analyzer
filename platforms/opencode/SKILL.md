---
name: meta-ads-analyzer
description: "Expert Meta Ads campaign analysis and diagnosis. Analyzes performance data, identifies root causes, and generates actionable recommendations using the Breakdown Effect framework."
---

<!--
  OPENCODE SKILL
  Install: cp -r platforms/opencode/ ~/.opencode/skills/meta-ads-analyzer/
  Then copy references/ into ~/.opencode/skills/meta-ads-analyzer/references/
-->

# Meta Ads Analysis & Diagnosis Skill

## When to Use This Skill

Use this skill when you need to **analyze and diagnose Meta Ads campaign performance**, including:
- Interpreting campaign, ad set, or ad-level performance data
- Identifying root causes of performance issues
- Generating actionable optimization recommendations
- Understanding why Meta's system makes certain budget allocation decisions
- Analyzing CSV exports, screenshots, or raw data from Meta Ads Manager

## Reference Documents

Load these reference documents (in `references/`) before performing any analysis:

1. `references/breakdown_effect.md` — **READ FIRST**: The Breakdown Effect
2. `references/core_concepts.md` — Ad Auction, Pacing, Learning Phase
3. `references/learning_phase.md` — Learning phase mechanics
4. `references/ad_relevance_diagnostics.md` — Quality, Engagement, Conversion rankings
5. `references/auction_overlap.md` — Diagnosing auction overlap
6. `references/pacing.md` — Budget and bid pacing
7. `references/bid_strategies.md` — Spend-based, goal-based, manual bidding
8. `references/ad_auctions.md` — How auction winners are determined
9. `references/performance_fluctuations.md` — Normal vs. concerning fluctuations

## Result Recommendations (MANDATORY)

> **IMPORTANT:** These rules are **MANDATORY** and **MUST be strictly followed**.

- **NEVER recommend pausing or reducing budget** for any segment based solely on higher average CPA/CPM in breakdown reports.
- **ALWAYS justify recommendations** with data evidence, Meta's system mechanics, and expected impact on *overall campaign performance*.
- **EVERY insight** must include data evidence and explanation.
- **Disambiguate clicks:** Use "Clicks (all)" or "Link Clicks" — never just "clicks".
- **Audience size:** Use "Accounts Center accounts" — never "people".

## Metric Naming

| Raw | Display |
|:----|:--------|
| `impressions` | Impressions |
| `clicks` | Clicks (all) |
| `purchase_roas` | Purchase ROAS |
| `cpm` | CPM |
| `ctr` | CTR (all) |
| `cost_per_action_type:purchase` | Cost per Purchase |
| `actions:purchase` | Purchases |
| `reach` | Reach (Accounts Center accounts) |
| `spend` | Amount Spent |

## Core Principles

- **Holistic First:** Evaluate at aggregate level before drilling down.
- **Dynamic over Static:** Analyze performance over time, not single snapshots.
- **Marginal over Average:** The system prioritizes marginal CPA, not average CPA.

## Analysis Workflow

### Step 1: Identify the Correct Evaluation Level

| Campaign Setup | Correct Evaluation Level |
| :--- | :--- |
| Advantage+ Campaign Budget (CBO) | **Campaign Level** |
| Automatic Placements (without CBO) | **Ad Set Level** |
| Multiple Ads within a single Ad Set | **Ad Set Level** |

### Step 2: Check Learning Phase Status

- Is the ad set still in learning phase? (~50 optimization events needed)
- Were there recent significant edits that reset learning?
- If in learning: caveat all findings as preliminary

### Step 3: Analyze with Meta-Specific Lens

1. **Marginal Efficiency Analysis** — Infer marginal CPA trends from time-series data
2. **Ad Relevance Diagnostics** — Check Quality, Engagement, and Conversion Rate Rankings
3. **Auction Overlap Check** — Are ad sets competing against each other?
4. **Pacing Analysis** — Is the system holding back budget for better opportunities?
5. **Performance Fluctuation Assessment** — Normal (20-30%) vs. concerning (>50% sustained)

### Step 4: Synthesize Through Breakdown Effect Lens

Interpret ALL findings through the **Breakdown Effect** framework. Explain *why* the system makes certain decisions.

### Step 5: Generate Report

1. **Executive Summary** - 2-3 key findings
2. **Evaluation Level** - Which level and why
3. **Learning Phase Status** - Current state per ad set
4. **Performance Analysis** - Metrics with proper naming
5. **Diagnosis** - Root causes with evidence
6. **Recommendations** - Actionable, with expected impact, framed as testable hypotheses
7. **Breakdown Effect Notes** - Explicit callouts
