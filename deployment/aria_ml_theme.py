"""
Advisory theme classifier for ARIA: TF-IDF + LogisticRegression.

Trained on governed executive_theme labels from aria_executive_review_dataset.csv.
Does not replace governance, overrides, or manifest-validated artifacts.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline

EXEC_THEMES = [
    "Workload & Burnout",
    "Management & Communication",
    "Compensation & Benefits",
    "Career Growth",
    "Work Culture",
]

PRIMARY_THEME_MAP: Dict[str, str] = {
    "T1_Physical_Degradation": "Workload & Burnout",
    "T2_Nepotism_Advancement": "Career Growth",
    "T3_Pay_Benefits": "Compensation & Benefits",
    "T4_Supervisor_Inconsistency": "Management & Communication",
    "T5_Bathroom_Dignity": "Work Culture",
}


def pipeline_mapped_theme(primary: object) -> str | None:
    if primary is None or (isinstance(primary, float) and pd.isna(primary)):
        return None
    return PRIMARY_THEME_MAP.get(str(primary).strip())


def _build_tfidf_union() -> FeatureUnion:
    """Word n-grams plus character n-grams for better short-text and multilingual handling."""
    word_tfidf = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        max_features=3000,
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )
    char_tfidf = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        max_features=2000,
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )
    return FeatureUnion([("word", word_tfidf), ("char", char_tfidf)])


def _per_class_ci(y_true: pd.Series, y_pred: np.ndarray, classes: List[str]) -> Dict[str, Dict[str, float]]:
    """Wilson confidence intervals on per-class accuracy from CV predictions."""
    ci_map = {}
    z = 1.96
    for cls in classes:
        mask = y_true == cls
        n = int(mask.sum())
        if n == 0:
            ci_map[cls] = {"accuracy": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}
            continue
        correct = int((y_pred[mask.values] == cls).sum())
        p = correct / n
        denom = 1 + (z ** 2 / n)
        center = (p + z ** 2 / (2 * n)) / denom
        margin = z * ((p * (1 - p) / n + z ** 2 / (4 * n ** 2)) ** 0.5) / denom
        ci_map[cls] = {
            "accuracy": round(p, 4),
            "ci_low": round(max(center - margin, 0.0), 4),
            "ci_high": round(min(center + margin, 1.0), 4),
            "n": n,
        }
    return ci_map


def train_and_eval_theme_classifier(df: pd.DataFrame) -> Tuple[Pipeline, Dict[str, Any]]:
    """Fit pipeline on df; return (fitted pipeline, CV metrics dict)."""
    work = df[df["executive_theme"].isin(EXEC_THEMES)].copy()
    if work.empty:
        raise ValueError("No rows with valid executive_theme for ML.")

    X = work["cleaned_text"].fillna("").astype(str)
    y = work["executive_theme"]

    pipeline = Pipeline([
        ("features", _build_tfidf_union()),
        ("clf", LogisticRegression(
            max_iter=4000,
            class_weight="balanced",
            random_state=42,
            solver="lbfgs",
            C=0.8,
        )),
    ])

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y_pred_cv = cross_val_predict(pipeline, X, y, cv=cv)
    cv_accuracy = float(accuracy_score(y, y_pred_cv))
    cv_macro_f1 = float(f1_score(y, y_pred_cv, average="macro", zero_division=0))

    # Per-class confidence intervals from CV predictions
    class_ci = _per_class_ci(y, y_pred_cv, EXEC_THEMES)

    mapped = work["primary_theme"].map(lambda v: pipeline_mapped_theme(v))
    mappable = mapped.notna()
    pipeline_map_acc = (
        float((mapped[mappable] == y[mappable]).mean()) if mappable.any() else 0.0
    )

    report_dict = classification_report(
        y, y_pred_cv, labels=EXEC_THEMES, output_dict=True, zero_division=0
    )

    pipeline.fit(X, y)

    metrics: Dict[str, Any] = {
        "artifact_version": 2,
        "model": "TfidfVectorizer (word+char) + LogisticRegression",
        "label": "executive_theme (governed)",
        "n_samples": int(len(work)),
        "cv_folds": 5,
        "cv_accuracy": cv_accuracy,
        "cv_macro_f1": cv_macro_f1,
        "pipeline_direct_map_accuracy": pipeline_map_acc,
        "pipeline_mappable_n": int(mappable.sum()),
        "classes": EXEC_THEMES,
        "class_confidence_intervals": class_ci,
        "classification_report_cv": report_dict,
        "notes": (
            "5-fold CV on n=150; high variance expected. Word+char n-gram union improves "
            "handling of short-text and multilingual reviews. VADER remains the packaged "
            "sentiment signal. Executive themes and overrides stay authoritative."
        ),
    }
    return pipeline, metrics
