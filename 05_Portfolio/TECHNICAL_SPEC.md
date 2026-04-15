# ARIA Technical Specification

What's in the code, what the formulas do, and what the data looks like.

---

## Runtime

- **Python**: 3.10.15 (locked in `runtime.txt`)
- **Dependencies**: 12 packages in `requirements.txt` — Streamlit 1.32, pandas ≥2.0, Plotly ≥5.17, scikit-learn ≥1.3, vaderSentiment ≥3.3
- **System deps**: `packages.txt` — build-essential, python3-dev, BLAS/LAPACK for scikit-learn

---

## Data Schemas

### Raw Dataset (`final_aria_dataset.csv`) — 150 rows

| Column | Type | Description |
|--------|------|-------------|
| `source_id` | string | Unique ID (e.g., `GLASS_001`, `YT_003`) |
| `platform` | string | `Glassdoor` or `YouTube` |
| `review_pros_cleaned` | string | Glassdoor positive aspects |
| `review_cons_cleaned` | string | Glassdoor negative aspects |
| `advice_to_management_cleaned` | string | Glassdoor management advice |
| `transcript_cleaned` | string | YouTube full transcript |
| `primary_theme` | string | Pipeline theme code (T1–T5) |
| `confidence` | string | Pipeline assignment confidence (HIGH/MEDIUM/LOW/NONE) |
| `vader_score` | float | Compound sentiment (-1 to +1) |
| `vader_label` | string | Sentiment class (positive/neutral/negative) |

### Executive Dataset (`aria_executive_review_dataset.csv`) — 150 rows

Adds these columns to the raw schema:

| Column | Type | Description |
|--------|------|-------------|
| `executive_theme` | string | One of 5 themes (e.g., `Compensation & Benefits`) |
| `executive_theme_confidence` | float | Mapping confidence score |
| `assignment_method` | string | `Direct pipeline map` or `Executive override` |
| `override_reason` | string | Why the override was needed (null for pipeline maps) |
| `final_sentiment` | string | Final sentiment label |
| `negative_intensity_pct` | float | VADER negative magnitude scaled 0–100 |
| `cleaned_text` | string | Unified review text (all fields joined) |
| `rating_overall` | float | Glassdoor star rating (null for YouTube) |

### Override Audit (`aria_executive_overrides.csv`) — 9 rows

| Column | Type | Description |
|--------|------|-------------|
| `source_id` | string | Review being overridden |
| `primary_theme` | string | Original pipeline assignment |
| `executive_theme` | string | Override assignment |
| `override_reason` | string | Justification |
| `pipeline_confidence` | string | Original confidence level |

### Manifest (`aria_dataset_manifest.json`)

```json
{
  "generated_at": "UTC timestamp",
  "datasets": {
    "raw": { "filename": "...", "sha256": "...", "rows": 150 },
    "executive": { "filename": "...", "sha256": "...", "rows": 150 },
    "overrides": { "filename": "...", "sha256": "...", "rows": 9 }
  },
  "platforms": { "Glassdoor": 140, "YouTube": 10 },
  "assignment_methods": { "Direct pipeline map": 141, "Executive override": 9 }
}
```

---

## Formulas

### Sentiment Classification

VADER compound score thresholds:
- Positive: compound ≥ 0.05
- Neutral: -0.05 < compound < 0.05
- Negative: compound ≤ -0.05

### Negative Intensity

```
negative_intensity_pct = abs(vader_negative_component) × 100
```

Only calculated for reviews classified as negative. Used as a severity measure — how *strongly* negative, not just whether negative.

### Wilson Confidence Interval

```
center = (p + z²/2n) / (1 + z²/n)
margin = z × sqrt((p(1-p)/n + z²/4n²) / (1 + z²/n)²)
CI = [center - margin, center + margin]
```

Where p = observed negative rate, n = sample size, z = 1.96 (95% confidence). Wilson intervals are preferred over normal approximation because they behave correctly when p is near 0 or 1, and when n is small.

### Attrition Risk Score

```
Risk Score = Negative Reviews × Negative Rate % × (0.5 + Avg Negative Intensity / 200)
```

Combines volume (how many), rate (what proportion), and severity (how intense). The intensity term adds 0–50% to the base score depending on average negative VADER magnitude.

### Business Impact Rating

```
Impact Potential = 0.35 × Productivity + 0.30 × Operations + 0.20 × Cost + 0.15 × Reputation
```

Each dimension is scored 1–10 by executive judgment per theme. These are transparent input assumptions, not data-derived outputs.

```
Evidence Pressure = 10 × (0.35 × Vol Share + 0.25 × Rate Share + 0.20 × Intensity Share + 0.10 × Public Exposure + 0.10 × Theme Size)
```

All components are normalized to [0, 1] from the data.

```
Business Impact = 0.50 × Impact Potential + 0.50 × Evidence Pressure
```

### Evidence Confidence

```
Confidence = 10 × (0.30 × Sample Depth + 0.25 × Pipeline Confidence + 0.25 × Direct Map Share + 0.20 × Platform Coverage)
```

Higher when the theme has more reviews, higher pipeline confidence, more direct maps (vs overrides), and presence on both platforms.

### What-If Cost Avoidance

```
Avoided Cost = (Avoided Negatives / Total Negatives) × Headcount × Turnover Cost × 0.15
```

The 0.15 assumes 15% annual voluntary attrition. This is a user-adjustable assumption, not a measured value. The formula assumes linear relationship between negative review reduction and attrition reduction.

---

## ML Specifications

### Theme Classifier

| Parameter | Value |
|-----------|-------|
| Vectorizer | FeatureUnion: word (1,2)-grams + char_wb (3,5)-grams |
| Word features | max 3,000, min_df=1, max_df=0.95, sublinear TF |
| Char features | max 2,000, min_df=1, max_df=0.95, sublinear TF |
| Classifier | LogisticRegression, C=0.8, balanced weights, LBFGS |
| Evaluation | 5-fold stratified CV |
| Metrics | Accuracy, macro F1, per-class Wilson CIs |

### Attrition Proxy

| Parameter | Value |
|-----------|-------|
| Features | rating, VADER score, intensity, pipeline confidence, 5 theme dummies, YouTube indicator, override indicator, 3 interaction terms |
| Target | Binary: negative AND rating ≤ 3 AND intensity ≥ median |
| Fallback targets | 2-signal (neg + low rating) if class < 10; sentiment-only if class < 8 |
| Classifier | LogisticRegression, C=0.5, balanced weights, LBFGS |
| Evaluation | 5-fold stratified CV (accuracy + AUC) |
| Uncertainty | Bootstrap 95% CIs on mean probability per theme (500 iterations) |

---

## Streamlit Configuration

From `.streamlit/config.toml`:

| Setting | Value | Why |
|---------|-------|-----|
| `fileWatcherType` | `none` | No file watching in production |
| `toolbarMode` | `viewer` | Read-only toolbar for end users |
| `enableXsrfProtection` | `true` | CSRF protection |
| `showErrorDetails` | `false` | Don't expose stack traces to users |
| `logger.level` | `warning` | Suppress debug noise |
| `theme.base` | `light` | Light theme with navy (#13315c) primary |

---

## Performance

With 150 rows, nothing is slow. For reference:

- Data load + hash validation: < 1 second
- Summary table construction: < 0.5 seconds
- ML model training (both): < 3 seconds (first load only; cached after)
- Chart rendering: < 1 second per chart
- Total cold-start time: ~5 seconds