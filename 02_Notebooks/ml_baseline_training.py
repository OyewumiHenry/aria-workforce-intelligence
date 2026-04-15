"""
Offline trainer for ARIA advisory theme classifier (optional — same logic as dashboard runtime).

The Streamlit app fits the model at runtime (cached by executive dataset SHA-256) so no binary
artifacts are required in git. Run this script to reproduce metrics or for CI checks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "deployment"))

from aria_ml_theme import train_and_eval_theme_classifier

import pandas as pd


def main() -> int:
    data_path = PROJECT_ROOT / "01_Data" / "aria_executive_review_dataset.csv"
    if not data_path.exists():
        print(f"Missing governed dataset: {data_path}", file=sys.stderr)
        return 1

    df = pd.read_csv(data_path)
    _, metrics = train_and_eval_theme_classifier(df)
    out_dir = PROJECT_ROOT / "01_Data" / "aria_ml_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ml_eval_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))
    print(f"\nWrote metrics snapshot to {out_dir / 'ml_eval_metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
