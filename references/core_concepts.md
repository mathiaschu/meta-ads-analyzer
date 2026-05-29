# Meta Ads Core Concepts

## Ad Auction

Every ad opportunity triggers an auction. Winner is determined by **Total Value**:

> *Total Value = (Advertiser Bid) x (Estimated Action Rate) + (Ad Quality)*

- **Advertiser Bid:** Controlled by bid strategy
- **Estimated Action Rate (pAction):** Predicted probability of desired action
- **Ad Quality:** User feedback, low-quality attribute assessments

**Key:** Lower bids can win if estimated action rates and quality are higher. Relevance drives cost efficiency.

## Pacing

Controls how budget is spent over campaign lifetime:

- **Budget Pacing:** Distributes budget evenly across schedule
- **Bid Pacing:** Adjusts bids based on remaining budget and opportunities

**Key:** Prevents exhausting budget early on expensive results; reserves budget for cheaper opportunities later.

## The Breakdown Effect

See `breakdown_effect.md` for detailed explanation.

**Core concept:** System optimizes for **marginal CPA** (cost of next result), not average CPA. A segment with lower average CPA may have saturated, making its marginal CPA higher than other segments.

## Learning Phase

New or significantly edited ad sets enter learning phase:

- Exits after ~**50 optimization events** within 7 days
- Performance is volatile with higher CPA during this phase
- Significant edits (budget, bid, targeting, creative, optimization goal) reset learning

**Best practices:** Avoid edits during learning; ensure budget supports ~50 weekly events; avoid fragmenting learning across too many ad sets.

## Ad Relevance Diagnostics

Diagnostic tools (not auction inputs) comparing your ad to competitors:

| Diagnostic | Measures |
| :--- | :--- |
| Quality Ranking | Perceived ad quality |
| Engagement Rate Ranking | Expected engagement rate |
| Conversion Rate Ranking | Expected conversion rate |

**Rankings:** Above Average (good), Below Average Bottom 35%/20%/10% (needs improvement).

Use to diagnose whether underperformance stems from quality, engagement, or post-click conversion issues.
