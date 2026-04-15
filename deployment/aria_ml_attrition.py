"""
Illustrative attrition-risk proxy: logistic regression on review-level features.

No real HR attrition labels — y is a transparent composite for portfolio demonstration.
Does not override governance, executive themes, or business-impact rankings.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

EXEC_THEMES = [
    "Workload & Burnout",
    "Management & Communication",
    "Compensation & Benefits",
    "Career Growth",
    "Work Culture",
]

# Business framing (aligned with BUSINESS_CASE.md illustrative range)
DEFAULT_TURNOVER_COST_USD = 22_000
BASELINE_FIRST_YEAR_ROI_MULTIPLE = 94


def _build_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    work = df.copy()
    if "rating_overall" not in work.columns:
        work["rating_overall"] = np.nan
    med = float(work["rating_overall"].median()) if work["rating_overall"].notna().any() else 3.0
    work["rating_filled"] = pd.to_numeric(work["rating_overall"], errors="coerce").fillna(med)
    work["vader_filled"] = pd.to_numeric(work.get("vader_score"), errors="coerce").fillna(0.0)
    if "negative_intensity_pct" not in work.columns:
        work["negative_intensity_pct"] = 0.0
    work["neg_intensity_filled"] = pd.to_numeric(work["negative_intensity_pct"], errors="coerce").fillna(0.0)
    work["pipe_conf"] = pd.to_numeric(work.get("pipeline_confidence_score"), errors="coerce").fillna(0.0)

    # Theme dummies
    theme_dummies = pd.get_dummies(work["executive_theme"], prefix="theme")
    for t in EXEC_THEMES:
        col = f"theme_{t}"
        if col not in theme_dummies.columns:
            theme_dummies[col] = 0

    # Platform and override indicators
    is_youtube = (work["platform"].astype(str) == "YouTube").astype(int)
    is_override = (work["assignment_method"].astype(str) == "Executive override").astype(int)

    # Interaction features for better signal capture on small samples
    vader_x_rating = work["vader_filled"] * work["rating_filled"]
    intensity_x_comp = work["neg_intensity_filled"] * theme_dummies.get(
        "theme_Compensation & Benefits", pd.Series(0, index=work.index)
    )
    override_x_conf = is_override * work["pipe_conf"]

    X = pd.concat([
        work[["rating_filled", "vader_filled", "neg_intensity_filled", "pipe_conf"]],
        theme_dummies[sorted(theme_dummies.columns)],
        pd.Series(is_youtube, name="platform_youtube", index=work.index),
        pd.Series(is_override, name="executive_override_row", index=work.index),
        pd.Series(vader_x_rating, name="vader_x_rating", index=work.index),
        pd.Series(intensity_x_comp, name="intensity_x_comp", index=work.index),
        pd.Series(override_x_conf, name="override_x_conf", index=work.index),
    ], axis=1)
    X = X.astype(float)
    feature_names = list(X.columns)
    return X, feature_names


def _build_proxy_target(df: pd.DataFrame, rating_col: pd.Series, intensity_col: pd.Series) -> Tuple[pd.Series, str]:
    """Binary proxy: negative sentiment + low rating + high intensity (3-signal trigger)."""
    neg = df["final_sentiment"].astype(str).str.lower() == "negative"
    low_rating = rating_col <= 3.0
    high_intensity = intensity_col >= intensity_col.median()

    # Strict 3-signal proxy first
    y = (neg & low_rating & high_intensity).astype(int)
    definition = (
        "Proxy = 1 when final_sentiment is negative AND rating_overall ≤ 3 AND "
        "negative_intensity ≥ sample median; missing values filled with sample median."
    )

    # Relax to 2-signal if too few positives for stable CV
    if int(y.sum()) < 10:
        y = (neg & low_rating).astype(int)
        definition = (
            "Proxy = 1 when final_sentiment is negative AND rating_overall ≤ 3; "
            "rating missing values are filled with the sample median before the threshold check. "
            "(3-signal trigger relaxed because strict class was too small for n=150.)"
        )

    # Last resort: sentiment only
    if int(y.sum()) < 8:
        y = neg.astype(int)
        definition = (
            "Proxy = 1 when final_sentiment is negative (relaxed threshold because "
            "the stricter proxy class was too small for n=150)."
        )
    return y, definition


def _bootstrap_theme_ci(
    df: pd.DataFrame,
    proba: np.ndarray,
    n_boot: int = 500,
    seed: int = 42,
) -> Dict[str, Dict[str, float]]:
    """Bootstrap 95% CI on mean predicted probability per theme."""
    rng = np.random.RandomState(seed)
    ci_map = {}
    for theme in EXEC_THEMES:
        mask = df["executive_theme"] == theme
        theme_proba = proba[mask.values]
        if len(theme_proba) < 2:
            ci_map[theme] = {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": len(theme_proba)}
            continue
        boot_means = []
        for _ in range(n_boot):
            sample = rng.choice(theme_proba, size=len(theme_proba), replace=True)
            boot_means.append(float(sample.mean()))
        ci_map[theme] = {
            "mean": round(float(theme_proba.mean()), 4),
            "ci_low": round(float(np.percentile(boot_means, 2.5)), 4),
            "ci_high": round(float(np.percentile(boot_means, 97.5)), 4),
            "n": int(mask.sum()),
        }
    return ci_map


def fit_attrition_proxy(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Fit logistic regression; return probabilities, coefficient importance, and CV metrics.
    """
    X, feature_names = _build_feature_matrix(df)
    rating_for_target = pd.to_numeric(df["rating_overall"], errors="coerce")
    med = float(rating_for_target.median()) if rating_for_target.notna().any() else 3.0
    rating_filled = rating_for_target.fillna(med)

    intensity_col = pd.to_numeric(df.get("negative_intensity_pct", pd.Series(0.0)), errors="coerce").fillna(0.0)
    y, proxy_definition = _build_proxy_target(df, rating_filled, intensity_col)

    if y.nunique() < 2:
        return None

    lr = LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        random_state=42,
        solver="lbfgs",
        C=0.5,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y_pred_cv = cross_val_predict(lr, X, y, cv=cv)
    cv_acc = float(accuracy_score(y, y_pred_cv))

    try:
        y_proba_cv = cross_val_predict(lr, X, y, cv=cv, method="predict_proba")[:, 1]
        cv_auc = float(roc_auc_score(y, y_proba_cv))
    except ValueError:
        cv_auc = float("nan")

    lr.fit(X, y)
    proba = lr.predict_proba(X)[:, 1]

    # Bootstrap confidence intervals per theme
    theme_ci = _bootstrap_theme_ci(df, proba)

    coef = lr.coef_[0]
    importance = (
        pd.DataFrame({"feature": feature_names, "coefficient": coef, "abs_coef": np.abs(coef)})
        .sort_values("abs_coef", ascending=False)
        .reset_index(drop=True)
    )

    return {
        "model": lr,
        "X": X,
        "y_proxy": y,
        "proxy_definition": proxy_definition,
        "predicted_proba": proba,
        "feature_importance": importance,
        "cv_accuracy": cv_acc,
        "cv_auc": cv_auc,
        "n_positive_proxy": int(y.sum()),
        "n_samples": int(len(df)),
        "default_turnover_cost_usd": DEFAULT_TURNOVER_COST_USD,
        "baseline_first_year_roi_multiple": BASELINE_FIRST_YEAR_ROI_MULTIPLE,
        "theme_confidence_intervals": theme_ci,
    }
