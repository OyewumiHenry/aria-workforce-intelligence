# ARIA: Attrition Risk Insight Analyzer

### Executive Workforce Intelligence from Public Employee Sentiment

I built ARIA to transform workforce risk into strategic action. By analyzing 150 public employee reviews across Glassdoor and YouTube, the system identifies which workforce issues are most likely to drive attrition, operational disruption, and leadership intervention.

**Live Dashboard:** [aria-workforce-intelligence.streamlit.app](https://aria-workforce-intelligence-7keiqrffmfx8et6wdn9fvg.streamlit.app/)

---

## What It Solves

Companies spend millions on internal engagement surveys but leave the real signal untapped: **what employees say publicly**. I created ARIA to bridge this gap with a single executive insight: **Which workforce issues will cost you the most, and what should you do about them right now?**

The system ingests 150 verified reviews, validates sentiment through VADER analysis (70% accuracy on this domain), and translates complaints into five actionable business themes:

1. **Compensation & Benefits** — Direct retention drag
2. **Workload & Burnout** — Throughput and safety risk
3. **Management & Communication** — Execution variance
4. **Career Growth** — Long-term retention pressure
5. **Work Culture** — Reputation and escalation risk

Every finding comes with an explicit confidence band and strategic recommendation.

---

## Key Insight

**Compensation issues** appear in 48% of negative reviews. **Workload** problems rank second at 32%, followed by **Management** at 28%. The concentration is real: the top three themes account for 73% of all attrition risk signal in this dataset.

---

## How to Use This

### Option 1: View the Live Dashboard

Visit [aria-workforce-intelligence.streamlit.app](https://aria-workforce-intelligence-7keiqrffmfx8et6wdn9fvg.streamlit.app/) to explore:

- **Executive Brief** — The 90-second story
- **Decision Agenda** — Actions, owners, and KPI requests
- **Risk Ranking** — Which theme poses the most attrition pressure
- **Impact Case** — Operating damage estimates
- **Evidence by Platform** — How Glassdoor and YouTube differ
- **Method Appendix** — How the analysis was built
- **Evidence Audit** — Drill into individual reviews

### Option 2: Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run deployment/aria_app.py
```

### Option 3: Deploy Your Own Version

1. Fork this repository
2. Connect your fork to Streamlit Community Cloud: [streamlit.io/cloud](https://streamlit.io/cloud)
3. Select your repo and branch
4. Deploy (Streamlit handles the rest)

---

## Project Structure

```
ARIA/
├── README.md                        (root level)
│
├── 01_Data/                         Raw data and governance artifacts
│   ├── final_aria_dataset.csv       Pipeline output (150 reviews, all validations passed)
│   ├── aria_executive_review_dataset.csv Reviewed and hand-tagged
│   ├── aria_executive_overrides.csv Manual adjustments (9 edge cases with reasons)
│   └── aria_dataset_manifest.json   SHA-256 hashes for integrity validation
│
├── 02_Notebooks/                    Data engineering and model training
│   ├── ARIA_pipeline_Note.ipynb     Main data processing and theme mapping
│   ├── governance_builder.py        Generates governance artifacts
│   ├── ml_baseline_training.py      ML model training scripts
│   ├── vader_validation_glassdoor.ipynb VADER sentiment model validation
│   ├── youtube_pipeline_ARIA.ipynb  YouTube transcript processing
│   └── requirements.txt             Python dependencies for notebooks
│
├── 05_Portfolio/                    Complete project documentation
│   ├── README.md                    Portfolio overview and methods
│   ├── ARCHITECTURE.md              System design and data flow
│   ├── BUSINESS_CASE.md             Financial justification and impact
│   ├── DEMO_WALKTHROUGH.md          Step-by-step demo guide
│   └── TECHNICAL_SPEC.md            Detailed technical specifications
│
└── deployment/                      Production application
    ├── aria_app.py                  Main 8-tab executive dashboard
    ├── aria_ml_attrition.py         ML model inference
    ├── aria_ml_theme.py             Theme classification utilities
    ├── validate_config.py           Pre-deployment validation script
    ├── requirements.txt             Python dependencies
    ├── packages.txt                 System-level dependencies
    ├── runtime.txt                  Python version (3.10+)
    └── .streamlit/
        └── config.toml              Streamlit dashboard configuration
```

---

## All 8 Dashboard Tabs

### 1. Executive Brief
Key findings, risk ranking, and strategic recommendations. The 90-second story.

### 2. Decision Agenda
Boardroom-ready opening script, 30/60/90-day actions, KPI requests, and challenge responses.

### 3. Risk Ranking
Attrition risk index for each theme with visual ranking and sentiment breakdown.

### 4. Impact Case
Business impact estimates across productivity, operations, cost, and reputation.

### 5. Evidence by Platform
Glassdoor vs YouTube side-by-side comparison with confidence intervals.

### 6. What-If Analysis
Intervention scenario sliders with live ROI projections and cost avoidance estimates.

### 7. Method Appendix
Complete transparency: governance validation, rank stability tests, formula reference, ML benchmarks.

### 8. Evidence Audit
Row-level review inspection with platform/theme/sentiment filters and CSV export.

---

## The Five Themes (Detailed Breakdown)

| Theme | Reviews | What It Tracks |
|-------|---------|---|
| **Compensation & Benefits** | 71 | Pay transparency, overtime rules, schedule predictability, benefits access |
| **Workload & Burnout** | 32 | Physical strain, pace pressure, fatigue, mental health impact |
| **Management & Communication** | 27 | Manager consistency, escalation handling, fairness, feedback quality |
| **Career Growth** | 13 | Advancement visibility, promotion credibility, skill development |
| **Work Culture** | 7 | Dignity, respect, workplace conditions, team dynamics |

Compensation dominates by volume (48% of negative reviews). Workload ranks second (32%), Management third (28%). Together, these three account for 73% of attrition risk signal.

---

## Data Quality & Governance

Every row in the dataset passed **18 comprehensive validation checks** before analysis:

| # | Validation Check | What It Validates |
|---|------------------|-------------------|
| 1 | Row count | Matches expected total (150) |
| 2 | Platform field | No nulls, only Glassdoor or YouTube |
| 3 | Cleaned text | No nulls across all reviews |
| 4 | VADER score | Numeric, within -1 to +1 range |
| 5 | VADER label | Only positive, negative, or neutral |
| 6 | Final sentiment | Only positive, negative, or neutral |
| 7 | Sentiment consistency | Final sentiment aligns with VADER score |
| 8 | Primary theme | Valid theme codes only (T1–T5) |
| 9 | Theme count | Non-negative integer |
| 10 | Confidence level | Only HIGH, MEDIUM, LOW, or NONE |
| 11 | Duplicate check | No duplicate source IDs within platform |
| 12 | Language detection | Flagged as LANG_NOT_SUPPORTED, not dropped |
| 13 | Glassdoor rating | Within 1–5 range where present |
| 14 | YouTube isolation | No Glassdoor-specific fields on YouTube rows |
| 15 | Human sentiment | Present for all YouTube rows |
| 16 | Return likelihood | Present for all YouTube rows |
| 17 | Theme keywords | At least one keyword match for HIGH confidence |
| 18 | Platform count | Glassdoor + YouTube = 150 |

**Zero errors. No imputation. No estimation.** All data files are SHA-256 hashed for integrity validation at startup.

---

## Model Selection: Why VADER

I tested three NLP models on 10 YouTube transcripts (the gold standard for spoken content):

| Model | Accuracy | Status |
|-------|----------|--------|
| TextBlob | 30% | Rejected — too sensitive to negation patterns |
| RoBERTa | 50% | Rejected — over-corrects polarity on long content |
| **VADER** | **70%** | Selected — Consistent on informal workplace language |

VADER was chosen because it handles the specific language patterns in warehouse and fulfillment worker reviews better than alternatives. Model selection is documented, not assumed.

---

## Technical Approach

I designed ARIA around three core principles:

**Governance First**: Every data transformation is auditable. SHA-256 hashes ensure data integrity. All theme assignments include confidence scores and provenance tracking. No silent fallbacks—if a review can't map to the five themes, the app halts.

**Executive Focus**: The dashboard answers business questions, not technical ones. Risk rankings drive action. Impact estimates are tied to observed evidence.

**Validation Heavy**: Model selection was evidence-based. Statistical methods use Wilson score intervals (better for small samples) and 6-scenario rank stability testing. Sample adequacy is labeled (Strong n≥30, Adequate n≥10, Caution n≥5, High Caution n<5).

---

## Statistical Methods

- **Wilson score intervals** — For all negative rates (handles small samples better than normal approximation)
- **6-scenario stability testing** — Ranks stress-tested under base, no-YouTube, direct-map-only, volume-only, rate-only, and intensity-only scenarios
- **Sample adequacy labels** — Strong (n≥30), Adequate (n≥10), Caution (n≥5), High Caution (n<5)

---

## ML Components (Advisory)

Both models are advisory. Neither overrides governance or changes business metrics.

**Theme Classifier**: TF-IDF (word + char n-grams) + logistic regression. 5-fold CV on n=150 with Wilson CIs per class and macro F1. Useful for benchmarking agreement between text content and governed labels.

**Attrition Proxy**: Logistic regression on review features. The target is synthetic — negative sentiment + low rating + high intensity. There are no real attrition labels. This quantifies risk concentration by theme, not actual churn probability.

---

## What This Does

* Transforms 150 public reviews into five actionable business themes  
* Ranks themes by attrition pressure with statistical confidence bands  
* Estimates operating damage by theme (productivity, cost, reputation, operations)  
* Provides a 30/60/90-day action recommendation  
* Breaks down evidence by platform (Glassdoor vs YouTube)  

---

## What This Doesn't Do

* Prove that review sentiment causes actual turnover, injury, or absenteeism  
* Replace internal HR data or engagement surveys  
* Predict individual employee exits  
* Benchmark against industry standards  
* Serve as a financial forecast (ROI figures are illustrative sensitivity exercises)  

---

## Requirements

- Python 3.10+
- Streamlit
- Pandas, NumPy
- VADER sentiment analysis
- Plotly for visualizations

---

## Running Locally

```bash
cd deployment
pip install -r requirements.txt
streamlit run aria_app.py
```

Opens at `http://localhost:8501`.

---

## Contributing

This is a portfolio project demonstrating workforce analytics capabilities. For questions or collaboration opportunities, reach out at **oyewumihenry6@gmail.com**.

---

*Built to help leaders see workforce risk before it becomes attrition.*