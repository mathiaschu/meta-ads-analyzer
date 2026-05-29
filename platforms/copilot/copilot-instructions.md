# Meta Ads Analyzer — GitHub Copilot Instructions

<!--
  GITHUB COPILOT INTEGRATION
  Copy this file to: .github/copilot-instructions.md
  For VS Code: Add to .vscode/settings.json under "github.copilot.chat.codeGeneration.instructions"
-->

## Meta Ads Campaign Analysis

When analyzing Meta Ads campaign data, follow these rules:

### Core Principles
- Evaluate at aggregate level before drilling down (holistic first)
- Analyze performance over time, not single snapshots
- The system optimizes for marginal CPA, not average CPA (Breakdown Effect)

### The Breakdown Effect
Meta's system optimizes for **marginal efficiency**, not average efficiency. A segment with higher average CPA may be protecting overall campaign efficiency. **Never judge by average CPA in breakdown reports alone.**

### Evaluation Levels
| Campaign Setup | Correct Level |
|:---|:---|
| Advantage+ CBO | Campaign Level |
| Automatic Placements | Ad Set Level |
| Multiple Ads in 1 Ad Set | Ad Set Level |

### Mandatory Rules
1. Never recommend pausing/reducing budget based solely on higher average CPA/CPM in breakdowns
2. Always justify recommendations with data evidence and system mechanics
3. Every insight must include data evidence and explanation
4. Align with official recommendations (check API first)
5. Use "Clicks (all)" or "Link Clicks" — never just "clicks"
6. Use "Accounts Center accounts" — never "people"

### Metric Naming
| Raw Metric | Display Name |
|:-----------|:-------------|
| `impressions` | Impressions |
| `clicks` | Clicks (all) |
| `purchase_roas` | Purchase ROAS |
| `cpm` | CPM |
| `ctr` | CTR (all) |
| `cost_per_action_type:purchase` | Cost per Purchase |
| `actions:purchase` | Purchases |
| `reach` | Reach (Accounts Center accounts) |
| `spend` | Amount Spent |

### Report Structure
1. Executive Summary
2. Evaluation Level
3. Learning Phase Status
4. Performance Analysis
5. Diagnosis (root causes with evidence)
6. Recommendations (actionable, testable hypotheses)
7. Breakdown Effect Notes
