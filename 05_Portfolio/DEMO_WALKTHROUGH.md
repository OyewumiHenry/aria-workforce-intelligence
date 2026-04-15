# ARIA Dashboard Walkthrough

What each tab does, what to look at, and what the numbers mean.

---

## Before You Start

Open the dashboard: `http://localhost:8501` (local) or the [live demo](https://aria-workforce-intelligence-jiyrdp7nbtkwpukuz3atiy.streamlit.app/).

On first load, ARIA validates data integrity (SHA-256 hashes), builds summary tables, and trains two advisory ML models. This takes about 5 seconds. After that, everything is cached.

---

## Landing Page

The top of the page shows six KPI cards:

| Metric | What It Means |
|--------|--------------|
| Total Reviews | 150 (140 Glassdoor + 10 YouTube) |
| Negative Reviews | Count and overall negative rate with 95% CI |
| Glassdoor Negative | Platform-specific rate with sample size and CI |
| YouTube Negative | Same — typically higher due to harsher public testimony |
| Pipeline HIGH Confidence | Share of reviews where the notebook's theme assignment was high-confidence |
| Top 3 Driver Share | How concentrated the negative signal is in the top three themes |

Below the KPIs: "What Each Page Means" expander gives a one-line description of each tab.

---

## Tab 1: Executive Brief

**When to use**: First. This is the shortest credible version of the story.

Shows three driver cards (top themes by negative volume), each with negative count, intensity, and platform split. Below that:

- **Observed In Data** — factual findings from the review analysis
- **Executive Judgment** — interpretive statements about which theme matters most and why
- **Risk Ranking** — all five themes ranked by attrition risk score with rationale
- **Impact Case Summary** — what each theme means for operations
- **Strategic Recommendations** — five specific actions with targets and owners

---

## Tab 2: Decision Agenda

**When to use**: When you're presenting to leadership.

Contains:
- **Callout box** with the three points to land first
- **90-second opening** — four bullet points for starting a boardroom discussion
- **Download buttons** — Executive Brief (Markdown), Method Appendix (Markdown), Risk Ranking (CSV), Impact Case (CSV)
- **30/60/90-day decision agenda** — actions, target themes, owners, success signals
- **KPI request table** — what leadership should demand from HR/Ops next week
- **Challenge response grid** — anticipated pushback with anchored answers

---

## Tab 3: Risk Ranking

**When to use**: When someone asks why one theme ranks above another.

Horizontal bar chart of risk scores by theme, plus a data table with:
- Rank, Theme, Total Reviews, Negative Reviews, Negative Rate %, Negative Rate CI, Sample Read, Avg Negative Intensity, Risk Score

Below: stacked bar chart showing sentiment distribution (positive/neutral/negative) across all five themes.

Risk score formula: `Negative Reviews × Negative Rate % × (0.5 + Intensity/200)`. Combines volume, rate, and severity.

---

## Tab 4: Impact Case

**When to use**: When someone asks what each theme does to operations, cost, or reputation.

Starts with evidence bullets about the impact model. Then three impact cards (top themes) showing:
- Business Impact Rating (/10)
- Impact Potential (operating judgment)
- Evidence Pressure (data signal)
- Evidence Confidence
- Current negative count
- Impact summary

Grouped bar chart: Business Impact vs Attrition Risk side by side per theme. These can diverge — a theme with lower attrition risk might have higher operating impact.

**Predictive attrition proxy section**: If scikit-learn is installed, shows the illustrative attrition model — CV accuracy, AUC, positive proxy class count, and an ROI linkage callout. Includes a probability distribution histogram, box plot by theme, and feature importance bar chart.

The proxy is a synthetic target (negative + low rating + high intensity). It's for concentration analysis and portfolio demonstration, not churn prediction.

Below the proxy: heatmap of operating domain scores (Productivity, Operations, Cost, Reputation) by theme, and the full impact table.

---

## Tab 5: Evidence by Platform

**When to use**: When someone asks how Glassdoor and YouTube differ.

Three cards at top: Glassdoor negative rate, YouTube negative rate, and the gap in percentage points. YouTube is consistently harsher but has a much smaller sample (n=10 vs n=140), so the CI is wider.

Grouped bar chart: negative rate by theme × platform. Text annotations show negative count per bar.

Cross-platform readout: which theme leads on each platform, and any low-sample caution cases.

---

## Tab 6: What-If Analysis

**When to use**: When you want to model "what if we improved X theme by Y%?"

Two input controls at top:
- **Turnover cost per departure** — default $22,000
- **Workforce headcount** — default 1,000

Then five sliders (0–50%), one per theme. Each represents a hypothetical reduction in negative reviews for that theme.

The model recalculates in real time:
- Total avoided negatives
- Estimated annual savings
- Projected ROI (against $50K Phase 1 investment)
- Payback signal (Strong/Moderate/Weak)

Scenario summary callout shows the combined impact across selected themes.

Data table and horizontal bar chart break out cost avoidance per theme. CSV export button at bottom.

**Key assumption**: The cost formula uses a 15% annual voluntary attrition rate. This is an assumption, not a measurement. The caption at the bottom makes this explicit.

---

## Tab 7: Method Appendix

**When to use**: When someone asks how the data, controls, and calculations work.

Top metrics: Direct Pipeline Map count (141), Executive Override count (9), Pipeline HIGH Confidence share (69.3%), Low-Sample Theme Pairs count.

Two-column layout:
- **Method Facts** — nine bullets covering data source, review count, governance, theme provenance, confidence, stability testing, and the ML advisory layer
- **What This Does Not Claim** — six disclaimers covering causality, benchmarking, attrition interpretation, and ML limitations

**Advisory ML section**: If scikit-learn is available, shows the theme classifier's 5-fold CV accuracy, macro F1, and pipeline direct-map accuracy. Includes a full comparison table (governed theme vs ML prediction vs probability) and a confusion matrix heatmap.

Expandable sections:
- Governance Bundle Status — file paths, hashes, validation status
- Rank Stability — 6-scenario table + top-3 appearance counts
- Formula Reference — every formula with type and logic
- Manual Override Audit — the 9 override rows with source IDs and reasons

---

## Tab 8: Evidence Audit

**When to use**: When someone wants to see the actual reviews.

Three filter dropdowns: Platform, Theme, Sentiment. All default to "show everything."

Data table shows each review with: Source ID, Platform, Pipeline Theme, Pipeline Confidence, Executive Theme, Executive Theme Confidence, Override Reason, Translation Method, Sentiment, VADER Intensity Reference, Review Text.

CSV export button at bottom.

This is the traceability layer. Any claim in Tabs 1–7 can be traced back to specific reviews here.

---

## Governance Footer

Appears at the bottom of every page. Shows:
- Manifest generation timestamp
- Executive dataset hash (first 12 characters)
- Override table hash (first 12 characters)
- Total review count
- Theme count

If this footer is present and the hashes match, the data is intact.