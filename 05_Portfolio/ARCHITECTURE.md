# ARIA Technical Architecture

How the system works, from raw reviews to executive dashboard.

---

## System Layers

```
┌─────────────────────────────────────────────┐
│         Streamlit Dashboard (8 tabs)        │
│  aria_app.py — 2,600 lines                  │
│  aria_ml_theme.py — advisory classifier     │
│  aria_ml_attrition.py — illustrative proxy  │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Governance Data Layer               │
│  01_Data/                                   │
│  ├── aria_executive_review_dataset.csv      │
│  ├── aria_executive_overrides.csv           │
│  └── aria_dataset_manifest.json (SHA-256)   │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         ETL Pipeline (Jupyter)              │
│  02_Notebooks/                              │
│  ├── ARIA_pipeline_Note.ipynb               │
│  ├── youtube_pipeline_ARIA.ipynb            │
│  └── build_aria_governance_artifacts.py     │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Raw Sources                         │
│  Glassdoor: 140 text reviews                │
│  YouTube: 10 video transcripts              │
└─────────────────────────────────────────────┘
```

---

## Data Pipeline

### Step 1: Acquisition and Cleaning

**Glassdoor**: Pros, cons, and advice-to-management columns joined into `cleaned_text`. **YouTube**: Transcripts processed into pain points and key themes, then joined into `cleaned_text`.

Both normalized: strip whitespace, standardize column names, assign unique `source_id` per review.

Output: `final_aria_dataset.csv` (150 rows, unified schema).

### Step 2: VADER Sentiment Scoring

Each review gets a compound sentiment score (-1 to +1). Classification: positive (≥0.05), neutral (-0.05 to 0.05), negative (≤-0.05).

VADER was validated at 70% accuracy on this specific content type (warehouse/fulfillment worker language). That's adequate for the domain but shouldn't be treated as high-precision.

### Step 3: Theme Assignment

The notebook's `primary_theme` field (T1–T5) maps to five executive themes:

| Pipeline Code | Executive Theme |
|--------------|----------------|
| T1_Physical_Degradation | Workload & Burnout |
| T2_Nepotism_Advancement | Career Growth |
| T3_Pay_Benefits | Compensation & Benefits |
| T4_Supervisor_Inconsistency | Management & Communication |
| T5_Bathroom_Dignity | Work Culture |

141 reviews map directly. 9 require explicit override.

### Step 4: Executive Override

9 reviews couldn't map cleanly — reasons include untranslatable language, multi-language switching, and placeholder/non-informative content. Each override logs the `source_id`, original pipeline theme, assigned executive theme, reason, and date.

The override table is itself SHA-256 hashed and tracked in the manifest.

### Step 5: Governance Bundle

`build_aria_governance_artifacts.py` produces three files:
1. `aria_executive_review_dataset.csv` — the 150-row executive view
2. `aria_executive_overrides.csv` — the 9-row audit trail
3. `aria_dataset_manifest.json` — metadata + SHA-256 hashes for all three data files

---

## Dashboard Architecture

### Startup Sequence

1. Resolve data directory (tries four possible locations)
2. Load manifest JSON
3. Load all three CSVs
4. Compute SHA-256 hashes on the loaded files
5. Compare against manifest hashes — **halt on mismatch**
6. Verify every row has a valid `executive_theme` — **halt on failure**
7. Build summary tables, rank themes, train ML models (cached)
8. Render

### Caching

- `@st.cache_data`: Data loading, summary tables, statistical calculations
- `@st.cache_resource`: ML model training (theme classifier, attrition proxy)

Both use the manifest hash as a cache key — if data changes, models retrain automatically.

### Key Functions

| Function | Purpose |
|----------|---------|
| `wilson_interval(p, n)` | Wilson binomial CI for small samples |
| `build_theme_summary()` | Aggregate sentiment metrics by theme |
| `build_platform_summary()` | Cross-platform comparison |
| `build_stability_tables()` | 6-scenario robustness testing |
| `build_business_impact_table()` | Executive prioritization model |
| `validate_governance_bundle()` | SHA-256 hash verification |

### Business Impact Formula

```
Impact Potential = 0.35 × Productivity + 0.30 × Operations + 0.20 × Cost + 0.15 × Reputation
Evidence Pressure = 10 × (0.35 × Vol Share + 0.25 × Rate Share + 0.20 × Intensity Share + 0.10 × Public Exp + 0.10 × Theme Size)
Business Impact = 0.50 × Impact Potential + 0.50 × Evidence Pressure
```

Impact Potential scores are executive judgment (manually assigned per theme). Evidence Pressure is calculated from the data. The 50/50 blend gives equal weight to operating logic and observed signal.

### Risk Score Formula

```
Risk Score = Negative Reviews × Negative Rate % × (0.5 + Intensity / 200)
```

Combines volume, rate, and severity into a single comparable number.

---

## ML Modules

### Theme Classifier (`aria_ml_theme.py`)

Architecture: `FeatureUnion(word TF-IDF + char TF-IDF) → LogisticRegression`

- Word n-grams: (1,2), max 3,000 features
- Char n-grams: (3,5), max 2,000 features
- Balanced class weights, C=0.8
- Evaluation: 5-fold stratified CV, macro F1, Wilson CIs per class

This is advisory benchmarking. The governed `executive_theme` labels stay authoritative.

### Attrition Proxy (`aria_ml_attrition.py`)

Features: rating, VADER score, intensity, theme dummies, platform indicator, override flag, plus three interaction terms (VADER × rating, intensity × compensation, override × confidence).

Target: synthetic binary proxy — `1` when negative sentiment AND rating ≤ 3 AND intensity ≥ median. Falls back to 2-signal or 1-signal trigger if class count is too small for CV.

Output: per-review probability, coefficient importance, bootstrap 95% CIs per theme.

No real attrition labels exist. This is explicitly a portfolio demonstration, not a deployed prediction system.

---

## Deployment

The `deployment/` directory is self-contained. Push it to GitHub, connect to Streamlit Cloud, point at `aria_app.py`, set Python to 3.10.

```
Runtime: Python 3.10.15 (runtime.txt)
Config: .streamlit/config.toml (CSRF enabled, file watcher off, viewer toolbar)
System deps: packages.txt (build-essential, BLAS/LAPACK for scikit-learn)
```

Data must stay in `deployment/01_Data/`. If files are modified, SHA-256 hashes will fail and the app won't start — by design.

---

## Known Constraints

- **150 rows**: Too small for high-confidence ML. The classifier and proxy are directional, not definitive.
- **No streaming**: Batch processing only. Data updates require re-running the governance builder.
- **Single company**: Results reflect one fulfillment employer's review profile. Not generalizable without new data.
- **VADER ceiling**: 70% accuracy means ~30% of sentiment labels may be wrong. Wilson intervals partially account for this, but theme-level error isn't directly measured.