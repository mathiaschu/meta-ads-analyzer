# The Breakdown Effect

The "breakdown effect" is the misinterpretation that Meta's system shifts budget into underperforming segments. In reality, the system maximizes total results by optimizing for **marginal efficiency**, not average efficiency.

## Evaluation Rules

| Automation Type | Evaluation Level |
| :--- | :--- |
| Advantage+ Campaign Budget (CBO) | Campaign level |
| Automatic placements (without CBO) | Ad Set level |
| Multiple ads in 1 ad set | Ad Set level |

## How It Works

The system combines **pacing** (even budget distribution) with **automation** (ML-driven delivery optimization).

**Example:**

- Campaign: Engagement objective, $500 budget
- Placements: Facebook Stories + Instagram Stories

Day 1: Facebook Stories delivers at $0.35 CPA vs Instagram's $0.72. System identifies an **inflection point** where Facebook's CPA rises faster than Instagram's, then shifts budget accordingly.

**Final results:**

| Placement | Average CPA | Spend |
| :--- | :--- | :--- |
| Instagram Stories | $1.46 | $450 |
| Facebook Stories | $1.10 | $50 |

This looks counterintuitive — more budget went to higher average CPA. But the system optimized for **marginal efficiency over time**: getting the next conversion at lowest cost, not maintaining lowest average.

## Key Insight

> *The system optimizes for marginal efficiency dynamically, not average efficiency statically. A segment with higher average CPA may be protecting overall campaign efficiency by preventing even higher marginal costs elsewhere.*

**Never judge system decisions by average CPA in breakdown reports alone.**
