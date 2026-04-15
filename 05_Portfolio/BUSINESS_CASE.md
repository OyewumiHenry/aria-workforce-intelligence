# ARIA Business Case

What the data says, what it costs, and what the assumptions are.

---

## The Problem

Workers talk publicly about their jobs — on Glassdoor, on YouTube, on Reddit. Companies usually ignore this signal until it becomes a PR crisis or a hiring bottleneck. By then the damage is done.

ARIA reads 150 public reviews from one fulfillment employer, scores them for sentiment, organizes them into five themes, and ranks those themes by attrition pressure. The output is a specific set of recommendations with owners and timelines.

---

## What the Data Shows

| Theme | Reviews | Negative Rate | Risk Score | What It Looks Like |
|-------|---------|--------------|------------|-------------------|
| Compensation & Benefits | 71 | 15.5% | Highest volume | Pay doesn't match physical demands. Overtime rules unclear. |
| Workload & Burnout | 32 | 15.6% | Highest intensity | Relentless pace. Fatigue, physical strain, rate pressure. |
| Management & Communication | 27 | 14.8% | Third overall | Manager inconsistency. Write-ups without context. Opaque promotion decisions. |
| Career Growth | 13 | 15.4% | Moderate | No visible advancement path. Skills don't translate to promotion. |
| Work Culture | 7 | 28.6% | Small but severe | Dignity complaints. Bathroom-break policing. YouTube amplifies. |

Three themes (Compensation, Workload, Management) account for 72% of all negative reviews. That concentration means targeted interventions have disproportionate impact.

---

## Business Impact Model

ARIA scores each theme on two dimensions:

**Impact Potential** — how much operating damage the theme could cause across productivity, operations, cost, and reputation. These are executive judgment scores, not data-derived. They're transparent and adjustable.

**Evidence Pressure** — how strong the data signal is. This blends negative volume share, negative rate, severity (VADER intensity), public exposure (YouTube vs Glassdoor), and theme scale.

Final Business Impact = 50% Impact Potential + 50% Evidence Pressure. The blend gives equal weight to operating logic and observed data.

---

## Cost Framework

### What We Know

- Industry-standard replacement cost for frontline warehouse workers: $15K–$30K per departure
- Typical annual voluntary attrition in fulfillment: 60–150%
- ARIA uses $22,000 as a mid-range replacement cost assumption

### What We're Assuming

The What-If tab models cost avoidance using this formula:

```
Avoided Cost = (Avoided Negatives / Total Negatives) × Headcount × Turnover Cost × 0.15
```

The 0.15 (15%) is an assumed annual voluntary attrition rate — a mid-range for fulfillment/warehouse labor. This is not measured. It's an input you can change.

### The 94x ROI Claim — Where It Comes From and Why to Be Careful

The 94x figure was derived from:
- $4.73M estimated annual savings ($22K × 1,000 headcount × 20-30% turnover reduction assumption)
- $50K Phase 1 investment (data pipeline + dashboard development)
- $4.73M / $50K ≈ 94x

**The problem**: the 20-30% turnover reduction is an assumption, not a measurement. ARIA can identify what workers complain about. It can't prove that fixing those complaints reduces turnover by 20-30% without internal HR data to validate the link.

The correct way to read this: **if** targeted interventions reduce attrition by X%, **then** the cost avoidance is Y. The dashboard's What-If tab lets you model different assumptions. Use it to find the break-even point, not to confirm the 94x number.

---

## Recommendations

### 0–30 Days

| Action | Owner | Success Signal |
|--------|-------|---------------|
| Publish site-level pay bands, overtime premiums, flex-shift access rules | CHRO + COO | Lower pay complaints, stronger shift-fill |
| Ban dignity-based discipline triggers (bathroom-break policing) | CHRO + Legal + Site Ops | Fewer severe public-facing complaints |

### 30–60 Days

| Action | Owner | Success Signal |
|--------|-------|---------------|
| Install manager control metrics: write-up rates, promotion approvals, escalation closure time | COO + HRBP leaders | Lower manager-driven variance across shifts |

### 60–90 Days

| Action | Owner | Success Signal |
|--------|-------|---------------|
| Redesign peak workload controls: cap consecutive heavy-lift assignments, protect break windows | Ops + Safety + Workforce Planning | Lower fatigue risk, steadier throughput |
| Publish clear promotion pathways with calibrated criteria | Talent + Site Leadership | Higher internal mobility credibility |

---

## What Leadership Should Demand Next Week

| KPI | Required Cut | Why |
|-----|-------------|-----|
| Voluntary attrition rate | By site, shift, tenure band, manager | Tests whether the review signal aligns with real retention loss |
| Absenteeism and late-call-off rate | By shift and workload-heavy department | Validates whether burnout is showing up in daily labor reliability |
| Overtime acceptance and fill rate | By site and pay band | Shows whether compensation friction is weakening surge capacity |
| Safety incidents | By department and peak-period week | Tests the operating cost of workload pressure |
| Promotion approvals and write-up rates | By manager and demographic segment | Surfaces management inconsistency |

---

## Limitations of This Analysis

1. **No causal proof.** Review sentiment correlates with dissatisfaction, but we can't prove it causes turnover without internal turnover data.
2. **Small sample.** 150 reviews. Some theme-platform combinations have fewer than 5 data points.
3. **Impact scores are judgment calls.** The Productivity/Ops/Cost/Reputation weights are executive estimates, not data-derived metrics.
4. **One company, one industry.** Results apply to this specific fulfillment environment. Don't generalize without new data.
5. **VADER's ceiling.** 70% accuracy means roughly 1 in 3 sentiment labels may be wrong. Wilson intervals absorb some of this noise, but systematic error isn't fully captured.
6. **No financial forecast.** The ROI figures are sensitivity exercises. They show what happens *if* assumptions hold, not what *will* happen.