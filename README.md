# ARIA: Workforce Risk Insight Analyzer

### Executive Workforce Risk Review From Public Employee Sentiment

ARIA turns 150 public employee reviews from Glassdoor and YouTube into a structured executive view of workforce risk. It focuses on five decision themes, clear scoring logic, and review-level traceability.

**Live Dashboard:** [aria-workforce-intelligence.streamlit.app](https://aria-workforce-intelligence-7keiqrffmfx8et6wdn9fvg.streamlit.app/)

---

## Quick Links

- [Architecture](05_Portfolio/ARCHITECTURE.md)
- [Technical Spec](05_Portfolio/TECHNICAL_SPEC.md)
- [Business Case](05_Portfolio/BUSINESS_CASE.md)
- [Demo Walkthrough](05_Portfolio/DEMO_WALKTHROUGH.md)
- [Main App](deployment/aria_app.py)

---

## At A Glance

- **Input:** 150 governed public employee reviews from Glassdoor and YouTube
- **Output:** five executive workforce-risk themes, ranked and tied to concrete actions
- **Decision value:** an evidence-first readout of where leadership should investigate, validate, and act next

```text
Public reviews -> governed dataset -> executive theme translation
               -> workforce-risk ranking -> impact review -> action agenda
```

---

## What ARIA Does

- Translates public employee reviews into five executive themes
- Ranks those themes by relative workforce risk inside this dataset
- Estimates business impact using transparent operating weights plus observed evidence
- Compares Glassdoor and YouTube without pretending they carry equal weight
- Lets leaders trace every claim back to governed review rows

The deployed app is an evidence review tool, not a predictive HR system.

---

## Key Findings

- Compensation & Benefits carries the largest negative review volume in this sample and is the clearest first compensation and scheduling review priority.
- Workload & Burnout carries the sharpest operational-strain signal and remains a top-tier execution concern under sensitivity testing.
- Management & Communication remains a major control-system risk because complaints cluster around inconsistency, escalation, and advancement credibility.
- The top three themes hold most of the negative signal, so the strongest conclusion is concentration of pressure, not diffuse dissatisfaction across every theme.

---

## Research Work

The deployed app is narrower than the notebook work, but the technical comparison work is still in the repository:

- `02_Notebooks/youtube_pipeline_ARIA.ipynb` contains the `TextBlob` vs `VADER` vs `RoBERTa` comparison and the YouTube transcript validation results.
- `02_Notebooks/vader_validation_glassdoor.ipynb` contains the Glassdoor-side sentiment validation and comparison work.
- `02_Notebooks/ARIA_pipeline_Note.ipynb` shows how the validated sentiment approach feeds the unified executive dataset.
- `02_Notebooks/ml_baseline_training.py` and `02_Notebooks/aria_ml_theme.py` keep the optional research-side advisory theme benchmarking.

So the repository keeps both layers:

- a deployable executive product in `deployment/`
- the supporting research work in `02_Notebooks/`

---

## Run Locally

```bash
pip install -r deployment/requirements.txt
streamlit run deployment/aria_app.py
```

For Streamlit Community Cloud, set the main file path to `deployment/aria_app.py`.

---

## Project Structure

```text
ARIA/
|-- README.md
|-- .streamlit/
|   `-- config.toml
|-- packages.txt
|-- 01_Data/
|   |-- final_aria_dataset.csv
|   |-- aria_executive_review_dataset.csv
|   |-- aria_executive_overrides.csv
|   `-- aria_dataset_manifest.json
|-- 02_Notebooks/
|   |-- ARIA_pipeline_Note.ipynb
|   |-- aria_ml_theme.py
|   |-- youtube_pipeline_ARIA.ipynb
|   |-- vader_validation_glassdoor.ipynb
|   |-- governance_builder.py
|   |-- ml_baseline_training.py
|   `-- requirements.txt
|-- 05_Portfolio/
|   |-- ARCHITECTURE.md
|   |-- BUSINESS_CASE.md
|   |-- DEMO_WALKTHROUGH.md
|   `-- TECHNICAL_SPEC.md
`-- deployment/
    |-- aria_app.py
    |-- aria_config.py
    |-- validate_config.py
    |-- requirements.txt
    `-- ...
```

---

## Dashboard Tabs

1. **Executive Brief** - condensed readout of findings, risk, impact, and actions
2. **Decision Agenda** - opening narrative, actions, KPI asks, and challenge responses
3. **Risk Ranking** - current workforce-risk ranking across the five themes
4. **Impact Case** - operating impact estimate grounded in explicit assumptions
5. **Evidence by Platform** - Glassdoor versus YouTube readout with sample-size context
6. **Method Appendix** - governance, formulas, validation, and limits
7. **Evidence Audit** - row-level traceability and CSV export

---

## Data And Governance

Every review row passes the governed preparation flow before analysis:

- unified cleaned text
- sentiment labels and VADER reference scores
- one executive theme per row
- explicit overrides for unsupported pipeline rows
- SHA-256 manifest checks for the governed bundle

If the governed files do not match the manifest, the deployed app stops instead of rendering silently.

---

## Methods

- **Theme model:** five executive themes only
- **Sentiment reference:** VADER, validated on this domain and used as a comparative severity aid
- **Workforce risk index:** negative review count x negative rate x severity adjustment
- **Intervals:** Wilson score intervals for negative-rate uncertainty
- **Stability testing:** six scenario views to stress-test rank order
- **Impact case:** 50/50 blend of operating impact potential and observed evidence pressure

---

## Research Notebooks

The notebooks under `02_Notebooks/` document the preparation, validation, and comparison work behind the project. The deployed dashboard does **not** depend on synthetic turnover proxies, live ROI sliders, or deployment-time ML classifiers.

---

## What ARIA Does Not Claim

- It does not prove that public sentiment causes real turnover, absenteeism, or safety events.
- It does not predict individual employee exits.
- It does not replace internal HR, labor, or finance data.
- It does not provide an industry benchmark.
- It does not present ROI forecasts as measured business outcomes.

ARIA is most useful as an external-signal layer that helps leadership decide what to inspect, validate, and act on next.
