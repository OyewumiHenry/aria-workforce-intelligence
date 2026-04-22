"""
ARIA: Workforce Risk Insight Analyzer
Rebuild: 2026-04-13 21:40 UTC
Version: v3-governance-strict
Manifest version: 2026-04-13T20:40:06+00:00
"""
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from aria_config import (
    BUSINESS_IMPACT_MODEL,
    EXEC_THEMES,
    EXECUTIVE_CANONICAL_DATA_PATH,
    MANIFEST_CANONICAL_PATH,
    OVERRIDE_CANONICAL_DATA_PATH,
    PIPELINE_CONFIDENCE_SCORES,
    PLATFORM_COLORS,
    PLOTLY_CONFIG,
    PRIMARY_THEME_MAP,
    PROJECT_ROOT,
    RAW_CANONICAL_DATA_PATH,
    SENTIMENT_COLORS,
    THEME_COLORS,
    configure_app,
)

configure_app()

SOURCE_THEME_OVERRIDES: Dict[int, Dict[str, str]] = {}


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data
def load_manifest(path: str) -> Dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_governance_paths() -> Dict[str, Optional[Path]]:
    return {
        "raw": RAW_CANONICAL_DATA_PATH if RAW_CANONICAL_DATA_PATH.exists() else None,
        "executive": EXECUTIVE_CANONICAL_DATA_PATH if EXECUTIVE_CANONICAL_DATA_PATH.exists() else None,
        "override": OVERRIDE_CANONICAL_DATA_PATH if OVERRIDE_CANONICAL_DATA_PATH.exists() else None,
        "manifest": MANIFEST_CANONICAL_PATH if MANIFEST_CANONICAL_PATH.exists() else None,
    }


def safe_float(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().lower().split())


def wilson_interval(successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    p = successes / total
    denominator = 1 + (z**2 / total)
    center = (p + (z**2 / (2 * total))) / denominator
    margin = (
        z
        * ((p * (1 - p) / total + z**2 / (4 * total**2)) ** 0.5)
        / denominator
    )
    return round(center - margin, 4), round(center + margin, 4)


def ci_label(lower: float, upper: float) -> str:
    return f"{lower * 100:.1f}% to {upper * 100:.1f}%"


def sample_read_label(total: int) -> str:
    if total < 5:
        return "Directional only"
    if total < 10:
        return "Use caution"
    return "Adequate"


def get_override_spec(row: pd.Series) -> Optional[Dict[str, str]]:
    source_id = safe_float(row.get("source_id"))
    if source_id is None:
        return None

    spec = SOURCE_THEME_OVERRIDES.get(int(source_id))
    if spec is None:
        return None

    checks = {
        "platform": "expected_platform",
        "primary_theme": "expected_primary_theme",
        "confidence": "expected_confidence",
        "cleaned_text": "expected_text",
    }
    for row_key, spec_key in checks.items():
        if normalize_text(row.get(row_key)) != normalize_text(spec[spec_key]):
            return None

    return spec


def assign_executive_theme(row: pd.Series) -> Optional[str]:
    primary_theme = str(row.get("primary_theme", "")).strip()
    if primary_theme in PRIMARY_THEME_MAP:
        return PRIMARY_THEME_MAP[primary_theme]

    override_spec = get_override_spec(row)
    if override_spec is not None:
        return override_spec["executive_theme"]

    return None


def compute_negative_intensity(row: pd.Series) -> float:
    if str(row.get("final_sentiment", "")).strip().lower() != "negative":
        return 0.0

    vader_score = safe_float(row.get("vader_score"))
    if vader_score is None:
        return 0.0
    return round(abs(vader_score), 3)


def assignment_method_for_row(row: pd.Series) -> str:
    primary_theme = str(row.get("primary_theme", "")).strip()
    if primary_theme in PRIMARY_THEME_MAP:
        return "Direct pipeline map"

    if get_override_spec(row) is not None:
        return "Executive override"

    return "Unresolved mapping"


def prepare_dataset(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()
    df["platform"] = df["platform"].fillna("Unknown")
    df["final_sentiment"] = df["final_sentiment"].fillna("neutral").str.lower()
    df["source_id"] = pd.to_numeric(df["source_id"], errors="coerce").fillna(-1).astype(int)
    df["pipeline_confidence"] = df["confidence"].fillna("NONE").astype(str).str.upper()
    df["pipeline_confidence_score"] = df["pipeline_confidence"].map(
        PIPELINE_CONFIDENCE_SCORES
    ).fillna(0.0)
    if "executive_theme" in df.columns:
        df["executive_theme"] = df["executive_theme"].fillna("")
        blank_theme_mask = df["executive_theme"].astype(str).str.strip() == ""
        if blank_theme_mask.any():
            df.loc[blank_theme_mask, "executive_theme"] = df.loc[blank_theme_mask].apply(
                assign_executive_theme, axis=1
            )
    else:
        df["executive_theme"] = df.apply(assign_executive_theme, axis=1)

    if "executive_theme_method" in df.columns:
        df["assignment_method"] = df["executive_theme_method"].fillna("")
        blank_method_mask = df["assignment_method"].astype(str).str.strip() == ""
        if blank_method_mask.any():
            df.loc[blank_method_mask, "assignment_method"] = df.loc[blank_method_mask].apply(
                assignment_method_for_row, axis=1
            )
    elif "assignment_method" not in df.columns:
        df["assignment_method"] = df.apply(assignment_method_for_row, axis=1)

    if "executive_theme_confidence" in df.columns:
        df["executive_theme_confidence"] = df["executive_theme_confidence"].fillna("")
    else:
        df["executive_theme_confidence"] = df["pipeline_confidence"]

    if "override_reason" in df.columns:
        df["override_reason"] = df["override_reason"].fillna("")
    else:
        df["override_reason"] = ""

    df["negative_intensity"] = df.apply(compute_negative_intensity, axis=1)
    df["negative_intensity_pct"] = (df["negative_intensity"] * 100).round(1)
    return df


def build_theme_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for theme in EXEC_THEMES:
        theme_df = df[df["executive_theme"] == theme].copy()
        negative_df = theme_df[theme_df["final_sentiment"] == "negative"]
        negative_rate = round((len(negative_df) / len(theme_df) * 100), 1) if len(theme_df) else 0.0
        avg_negative_intensity = round(negative_df["negative_intensity_pct"].mean(), 1) if len(negative_df) else 0.0
        ci_low, ci_high = wilson_interval(len(negative_df), len(theme_df))
        rows.append(
            {
                "Theme": theme,
                "Reviews": int(len(theme_df)),
                "Negative Reviews": int(len(negative_df)),
                "Negative Rate %": negative_rate,
                "Negative Rate CI Low %": round(ci_low * 100, 1),
                "Negative Rate CI High %": round(ci_high * 100, 1),
                "Negative Rate CI": ci_label(ci_low, ci_high),
                "Sample Read": sample_read_label(len(theme_df)),
                "Avg Negative Intensity": avg_negative_intensity,
            }
        )

    summary = pd.DataFrame(rows)
    summary["Driver Score"] = (summary["Negative Reviews"] * summary["Avg Negative Intensity"]).round(1)
    summary["Risk Score"] = (
        summary["Negative Reviews"]
        * summary["Negative Rate %"]
        * (0.5 + summary["Avg Negative Intensity"] / 200)
    ).round(1)
    return summary


def build_platform_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for theme in EXEC_THEMES:
        for platform in ["Glassdoor", "YouTube"]:
            platform_df = df[(df["executive_theme"] == theme) & (df["platform"] == platform)].copy()
            negative_df = platform_df[platform_df["final_sentiment"] == "negative"]
            negative_rate = round((len(negative_df) / len(platform_df) * 100), 1) if len(platform_df) else 0.0
            avg_negative_intensity = round(negative_df["negative_intensity_pct"].mean(), 1) if len(negative_df) else 0.0
            ci_low, ci_high = wilson_interval(len(negative_df), len(platform_df))
            rows.append(
                {
                    "Theme": theme,
                    "Platform": platform,
                    "Reviews": int(len(platform_df)),
                    "Negative Reviews": int(len(negative_df)),
                    "Negative Rate %": negative_rate,
                    "Negative Rate CI Low %": round(ci_low * 100, 1),
                    "Negative Rate CI High %": round(ci_high * 100, 1),
                    "Negative Rate CI": ci_label(ci_low, ci_high),
                    "Sample Read": sample_read_label(len(platform_df)),
                    "Avg Negative Intensity": avg_negative_intensity,
                }
            )
    return pd.DataFrame(rows)


def build_sentiment_theme_summary(df: pd.DataFrame) -> pd.DataFrame:
    sentiment_rows = []
    for theme in EXEC_THEMES:
        for sentiment in ["positive", "neutral", "negative"]:
            count = len(
                df[
                    (df["executive_theme"] == theme)
                    & (df["final_sentiment"] == sentiment)
                ]
            )
            sentiment_rows.append(
                {
                    "Theme": theme,
                    "Sentiment": sentiment.capitalize(),
                    "Count": int(count),
                }
            )
    return pd.DataFrame(sentiment_rows)


def validate_governance_bundle(
    manifest: Dict[str, object],
    raw_path: Path,
    executive_path: Path,
    override_path: Path,
) -> List[str]:
    errors: List[str] = []
    expected_hashes = {
        "raw_dataset_sha256": raw_path,
        "executive_dataset_sha256": executive_path,
        "override_table_sha256": override_path,
    }
    for manifest_key, actual_path in expected_hashes.items():
        expected_hash = str(manifest.get(manifest_key, "")).strip().lower()
        actual_hash = file_sha256(actual_path).lower()
        if expected_hash != actual_hash:
            errors.append(
                f"{manifest_key} does not match {actual_path.name}. Expected {expected_hash}, observed {actual_hash}."
            )

    if int(manifest.get("total_reviews", -1)) <= 0:
        errors.append("Manifest total_reviews is missing or invalid.")

    return errors


def top_three_themes(summary: pd.DataFrame, mode: str) -> List[str]:
    working = summary[summary["Reviews"] > 0].copy()
    if working.empty:
        return ["", "", ""]

    sort_map = {
        "risk": ["Risk Score", "Negative Reviews", "Negative Rate %", "Avg Negative Intensity"],
        "volume": ["Negative Reviews", "Reviews", "Avg Negative Intensity"],
        "rate": ["Negative Rate %", "Negative Reviews", "Reviews"],
        "severity": ["Avg Negative Intensity", "Negative Reviews", "Reviews"],
    }
    sorted_df = working.sort_values(by=sort_map[mode], ascending=False).head(3)
    names = sorted_df["Theme"].tolist()
    return names + [""] * (3 - len(names))


def build_stability_tables(df: pd.DataFrame, base_theme_summary: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    scenario_definitions = [
        ("Base workforce risk", base_theme_summary, "risk"),
        ("No YouTube", build_theme_summary(df[df["platform"] != "YouTube"]), "risk"),
        (
            "Direct pipeline map only",
            build_theme_summary(df[df["assignment_method"] == "Direct pipeline map"]),
            "risk",
        ),
        ("Negative volume only", base_theme_summary, "volume"),
        ("Negative rate only", base_theme_summary, "rate"),
        ("Negative intensity only", base_theme_summary, "severity"),
    ]

    scenario_rows = []
    for scenario_name, summary, mode in scenario_definitions:
        top_3 = top_three_themes(summary, mode)
        scenario_rows.append(
            {
                "Scenario": scenario_name,
                "Top 1": top_3[0],
                "Top 2": top_3[1],
                "Top 3": top_3[2],
            }
        )

    scenario_table = pd.DataFrame(scenario_rows)
    stability_rows = []
    for theme in EXEC_THEMES:
        top_3_count = int(
            sum(theme in [row["Top 1"], row["Top 2"], row["Top 3"]] for row in scenario_rows)
        )
        top_1_count = int(sum(theme == row["Top 1"] for row in scenario_rows))
        stability_rows.append(
            {
                "Theme": theme,
                "Top 3 Appearances": top_3_count,
                "Top 3 Stability %": round(top_3_count / len(scenario_rows) * 100, 1),
                "Top 1 Appearances": top_1_count,
            }
        )

    stability_table = pd.DataFrame(stability_rows).sort_values(
        by=["Top 3 Appearances", "Top 1 Appearances", "Theme"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    return scenario_table, stability_table


def build_business_impact_table(
    df: pd.DataFrame,
    theme_summary: pd.DataFrame,
    platform_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    max_negative_reviews = max(float(theme_summary["Negative Reviews"].max()), 1.0)
    max_negative_rate = max(float(theme_summary["Negative Rate %"].max()), 1.0)
    max_negative_intensity = max(float(theme_summary["Avg Negative Intensity"].max()), 1.0)
    max_reviews = max(float(theme_summary["Reviews"].max()), 1.0)

    for theme in EXEC_THEMES:
        theme_row = theme_summary[theme_summary["Theme"] == theme].iloc[0]
        theme_df = df[df["executive_theme"] == theme].copy()
        model = BUSINESS_IMPACT_MODEL[theme]
        public_exposure = max(
            platform_value(platform_summary, theme, "Glassdoor", "Negative Rate %"),
            platform_value(platform_summary, theme, "YouTube", "Negative Rate %"),
        )
        platform_theme_rows = platform_summary[platform_summary["Theme"] == theme].copy()
        platforms_present = int((platform_theme_rows["Reviews"] > 0).sum())
        low_sample_flag = bool(
            ((platform_theme_rows["Reviews"] > 0) & (platform_theme_rows["Reviews"] < 5)).any()
        )
        direct_map_share = round(
            (
                len(theme_df[theme_df["assignment_method"] == "Direct pipeline map"])
                / max(float(theme_row["Reviews"]), 1.0)
            ) * 100,
            1,
        )
        avg_pipeline_confidence = round(
            float(theme_df["pipeline_confidence_score"].mean()) * 10,
            1,
        )
        high_pipeline_confidence_share = round(
            (theme_df["pipeline_confidence"] == "HIGH").mean() * 100,
            1,
        ) if len(theme_df) else 0.0

        impact_potential = round(
            0.35 * float(model["Productivity"])
            + 0.30 * float(model["Operations"])
            + 0.20 * float(model["Cost"])
            + 0.15 * float(model["Reputation"]),
            1,
        )
        evidence_pressure = round(
            10
            * (
                0.35 * (float(theme_row["Negative Reviews"]) / max_negative_reviews)
                + 0.25 * (float(theme_row["Negative Rate %"]) / max_negative_rate)
                + 0.20 * (float(theme_row["Avg Negative Intensity"]) / max_negative_intensity)
                + 0.10 * (public_exposure / 100)
                + 0.10 * (float(theme_row["Reviews"]) / max_reviews)
            ),
            1,
        )
        evidence_confidence = round(
            10
            * (
                0.45 * min(float(theme_row["Reviews"]) / 25, 1.0)
                + 0.25 * (avg_pipeline_confidence / 10)
                + 0.15 * (platforms_present / 2)
                + 0.10 * (direct_map_share / 100)
                + 0.05 * (0 if low_sample_flag else 1)
            ),
            1,
        )
        business_impact_rating = round(
            0.50 * impact_potential
            + 0.50 * evidence_pressure,
            1,
        )
        rows.append(
            {
                "Theme": theme,
                "Productivity Impact": float(model["Productivity"]),
                "Operational Impact": float(model["Operations"]),
                "Cost Impact": float(model["Cost"]),
                "Reputation Impact": float(model["Reputation"]),
                "Impact Potential": impact_potential,
                "Business Impact Rating": business_impact_rating,
                "Evidence Pressure": evidence_pressure,
                "Evidence Confidence": evidence_confidence,
                "Avg Pipeline Confidence": avg_pipeline_confidence,
                "High Pipeline Confidence %": high_pipeline_confidence_share,
                "Direct Map Share %": direct_map_share,
                "Platform Coverage": platforms_present,
                "Public Exposure %": public_exposure,
                "Low Sample Risk": "Yes" if low_sample_flag else "No",
                "Current Negative Reviews": int(theme_row["Negative Reviews"]),
                "Current Negative Rate %": float(theme_row["Negative Rate %"]),
                "Current Negative Intensity": float(theme_row["Avg Negative Intensity"]),
                "Impact Summary": str(model["Impact Summary"]),
            }
        )

    impact_df = pd.DataFrame(rows).sort_values(
        by=[
            "Business Impact Rating",
            "Evidence Confidence",
            "Evidence Pressure",
            "Current Negative Reviews",
        ],
        ascending=False,
    ).reset_index(drop=True)
    impact_df["Impact Rank"] = range(1, len(impact_df) + 1)
    impact_df["Impact Tier"] = impact_df["Business Impact Rating"].apply(
        lambda value: "Very High"
        if value >= 9.0
        else ("High" if value >= 8.0 else ("Elevated" if value >= 7.0 else "Moderate"))
    )
    impact_df["Confidence Band"] = impact_df["Evidence Confidence"].apply(
        lambda value: "High"
        if value >= 7.5
        else ("Moderate" if value >= 5.5 else "Caution")
    )
    return impact_df


def platform_value(platform_summary: pd.DataFrame, theme: str, platform: str, column: str) -> float:
    row = platform_summary[
        (platform_summary["Theme"] == theme) & (platform_summary["Platform"] == platform)
    ]
    if row.empty:
        return 0.0
    return float(row.iloc[0][column])


def pct(value: float) -> str:
    return f"{value:.1f}%"


def mono_number(value: float) -> str:
    return f"{int(round(value)):,}"


def short_hash(value: object, width: int = 12) -> str:
    text = str(value).strip()
    return text[:width] if text else "n/a"


def section_subtitle(text: str):
    st.markdown(f"<p class='section-sub'>{text}</p>", unsafe_allow_html=True)


def render_bullet_list(items: List[str]):
    st.markdown("\n".join([f"- {item}" for item in items]))


def render_numbered_list(items: List[str]):
    st.markdown("\n".join([f"{i + 1}. {item}" for i, item in enumerate(items)]))


def format_theme_list(items: List[str]) -> str:
    cleaned = [item for item in items if item]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


# Run the main app logic
governance_paths = resolve_governance_paths()
missing_governance_files = [
    name
    for name, path in governance_paths.items()
    if path is None
]
if missing_governance_files:
    st.markdown(
        """
        <div class='panel' style='border-left:6px solid #13315c; margin-top: 36px;'>
            <h3 style='margin:0 0 8px 0;'>Governance Bundle Required</h3>
            <p style='margin:0; color:#475569;'>
                ARIA requires the governed review bundle in <code>01_Data</code>:
                <code>final_aria_dataset.csv</code>, <code>aria_executive_review_dataset.csv</code>,
                <code>aria_executive_overrides.csv</code>, and <code>aria_dataset_manifest.json</code>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

raw_dataset_path = governance_paths["raw"]
executive_dataset_path = governance_paths["executive"]
override_table_path = governance_paths["override"]
manifest_path = governance_paths["manifest"]
governance_manifest = load_manifest(str(manifest_path))
governance_errors = validate_governance_bundle(
    governance_manifest,
    raw_dataset_path,
    executive_dataset_path,
    override_table_path,
)
if governance_errors:
    st.markdown(
        """
        <div class='panel' style='border-left:6px solid #b42318; margin-top: 36px;'>
            <h3 style='margin:0 0 8px 0;'>Governance Validation Failed</h3>
            <p style='margin:0; color:#475569;'>
                The manifest does not match the governed dataset bundle. Rebuild the artifacts before presenting.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_bullet_list(governance_errors)
    st.stop()

try:
    dataset_source_display = str(executive_dataset_path.relative_to(PROJECT_ROOT))
    raw_dataset_source_display = str(raw_dataset_path.relative_to(PROJECT_ROOT))
    override_source_display = str(override_table_path.relative_to(PROJECT_ROOT))
    manifest_source_display = str(manifest_path.relative_to(PROJECT_ROOT))
except ValueError:
    dataset_source_display = str(executive_dataset_path)
    raw_dataset_source_display = str(raw_dataset_path)
    override_source_display = str(override_table_path)
    manifest_source_display = str(manifest_path)

override_reference_table = load_data(str(override_table_path))
df = prepare_dataset(load_data(str(executive_dataset_path)))
unresolved_rows = df[df["executive_theme"].isna()].copy()
if not unresolved_rows.empty:
    st.markdown(
        """
        <div class='panel' style='border-left:6px solid #b42318; margin-top: 36px;'>
                <h3 style='margin:0 0 8px 0;'>Executive Translation Incomplete</h3>
                <p style='margin:0; color:#475569;'>
                    ARIA found pipeline rows that do not map cleanly into the five executive themes
                    and do not have a validated executive override. Review these rows before presenting.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
    )
    st.dataframe(
        unresolved_rows[
            ["source_id", "platform", "primary_theme", "pipeline_confidence", "cleaned_text"]
        ].rename(
            columns={
                "source_id": "Source ID",
                "platform": "Platform",
                "primary_theme": "Pipeline Theme",
                "pipeline_confidence": "Pipeline Confidence",
                "cleaned_text": "Review Text",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.stop()

theme_summary = build_theme_summary(df)
platform_summary = build_platform_summary(df)
sentiment_theme_summary = build_sentiment_theme_summary(df)
business_impact_table = build_business_impact_table(df, theme_summary, platform_summary)
scenario_table, stability_table = build_stability_tables(df, theme_summary)

top_drivers = theme_summary.sort_values(
    by=["Driver Score", "Negative Reviews", "Avg Negative Intensity"],
    ascending=False,
).head(3)
top_driver_names = top_drivers["Theme"].tolist()
top_driver_theme_list = format_theme_list(top_driver_names)
negative_theme_summary = theme_summary[theme_summary["Negative Reviews"] > 0].copy()
volume_leader = negative_theme_summary.sort_values(
    by=["Negative Reviews", "Reviews", "Avg Negative Intensity"],
    ascending=False,
).iloc[0]
severity_leader = negative_theme_summary.sort_values(
    by=["Avg Negative Intensity", "Negative Reviews", "Reviews"],
    ascending=False,
).iloc[0]

risk_ranking = theme_summary.sort_values(
    by=["Risk Score", "Negative Reviews", "Negative Rate %", "Avg Negative Intensity"],
    ascending=False,
).reset_index(drop=True)
risk_ranking["Rank"] = range(1, len(risk_ranking) + 1)
risk_ranking["Workforce Risk Rating"] = (
    risk_ranking["Risk Score"] / max(float(risk_ranking["Risk Score"].max()), 1.0) * 10
).round(1)
risk_leader = risk_ranking.iloc[0]

total_reviews = len(df)
negative_reviews = int((df["final_sentiment"] == "negative").sum())
overall_negative_rate = round((negative_reviews / total_reviews) * 100, 1)
overall_ci_low, overall_ci_high = wilson_interval(negative_reviews, total_reviews)
glassdoor_negative_reviews = int(
    ((df["platform"] == "Glassdoor") & (df["final_sentiment"] == "negative")).sum()
)
youtube_negative_reviews = int(
    ((df["platform"] == "YouTube") & (df["final_sentiment"] == "negative")).sum()
)
glassdoor_negative_rate = round(
    (glassdoor_negative_reviews / max((df["platform"] == "Glassdoor").sum(), 1)) * 100,
    1,
)
youtube_negative_rate = round(
    (youtube_negative_reviews / max((df["platform"] == "YouTube").sum(), 1)) * 100,
    1,
)
top_driver_negative_share = round(
    (top_drivers["Negative Reviews"].sum() / negative_reviews) * 100,
    1,
) if negative_reviews else 0.0

assignment_summary = (
    df["assignment_method"]
    .value_counts()
    .reindex(["Direct pipeline map", "Executive override", "Unresolved mapping"], fill_value=0)
    .rename_axis("Assignment Method")
    .reset_index(name="Reviews")
)
assignment_summary["Share %"] = (
    assignment_summary["Reviews"] / max(total_reviews, 1) * 100
).round(1)
assignment_count_lookup = assignment_summary.set_index("Assignment Method")["Reviews"].to_dict()
assignment_share_lookup = assignment_summary.set_index("Assignment Method")["Share %"].to_dict()
direct_theme_share = float(assignment_share_lookup["Direct pipeline map"])
override_share = float(assignment_share_lookup["Executive override"])
high_pipeline_confidence_reviews = int((df["pipeline_confidence"] == "HIGH").sum())
high_pipeline_confidence_share = round(
    (high_pipeline_confidence_reviews / max(total_reviews, 1)) * 100,
    1,
)
none_pipeline_confidence_reviews = int((df["pipeline_confidence"] == "NONE").sum())

platform_counts = df["platform"].value_counts().to_dict()
glassdoor_reviews = int(platform_counts.get("Glassdoor", 0))
youtube_reviews = int(platform_counts.get("YouTube", 0))
glassdoor_ci_low, glassdoor_ci_high = wilson_interval(glassdoor_negative_reviews, glassdoor_reviews)
youtube_ci_low, youtube_ci_high = wilson_interval(youtube_negative_reviews, youtube_reviews)
stability_leader = stability_table.iloc[0]
scenario_count = len(scenario_table)
manifest_generated_at = str(governance_manifest.get("generated_at_utc", "Unknown"))
raw_dataset_hash = str(governance_manifest.get("raw_dataset_sha256", ""))
executive_dataset_hash = str(governance_manifest.get("executive_dataset_sha256", ""))
override_table_hash = str(governance_manifest.get("override_table_sha256", ""))
governance_status_table = pd.DataFrame(
    [
        {
            "Artifact": "Raw pipeline dataset",
            "Path": raw_dataset_source_display,
            "SHA256": short_hash(raw_dataset_hash, 16),
        },
        {
            "Artifact": "Executive review dataset",
            "Path": dataset_source_display,
            "SHA256": short_hash(executive_dataset_hash, 16),
        },
        {
            "Artifact": "Override table",
            "Path": override_source_display,
            "SHA256": short_hash(override_table_hash, 16),
        },
        {
            "Artifact": "Governance manifest",
            "Path": manifest_source_display,
            "SHA256": short_hash(file_sha256(manifest_path), 16),
        },
    ]
)

low_sample_watchlist = platform_summary[
    (platform_summary["Reviews"] > 0) & (platform_summary["Reviews"] < 5)
].copy()
low_sample_watchlist["Caution Level"] = low_sample_watchlist["Reviews"].apply(
    lambda value: "High caution" if value < 3 else "Caution"
)
low_sample_watchlist = low_sample_watchlist.sort_values(
    by=["Reviews", "Negative Rate %", "Avg Negative Intensity"],
    ascending=[True, False, False],
).reset_index(drop=True)

override_audit = df[df["assignment_method"] == "Executive override"][
    [
        "source_id",
        "platform",
        "primary_theme",
        "pipeline_confidence",
        "executive_theme",
        "executive_theme_confidence",
        "override_reason",
        "final_sentiment",
        "cleaned_text",
    ]
].rename(
    columns={
        "source_id": "Source ID",
        "platform": "Platform",
        "primary_theme": "Pipeline Theme",
        "pipeline_confidence": "Pipeline Confidence",
        "executive_theme": "Executive Theme",
        "executive_theme_confidence": "Executive Theme Confidence",
        "override_reason": "Override Reason",
        "final_sentiment": "Sentiment",
        "cleaned_text": "Review Text",
    }
)

formula_table = pd.DataFrame(
    [
        {
            "Component": "Theme assignment",
            "Type": "Observed transformation",
            "Logic": "Use the notebook primary_theme when it matches one of the five ARIA themes; otherwise apply only explicit source-level overrides for the 9 unsupported pipeline rows, validated against source_id, platform, pipeline theme, pipeline confidence, and cleaned_text. Unresolved rows stop the app.",
        },
        {
            "Component": "Negative intensity",
            "Type": "Observed severity index",
            "Logic": "For negative reviews only, use the absolute VADER magnitude as a cross-platform severity reference, while final_sentiment still follows the pipeline rules by platform.",
        },
        {
            "Component": "Workforce risk index",
            "Type": "Relative dataset index",
            "Logic": "Negative Reviews x Negative Rate % x (0.5 + Avg Negative Intensity / 200). Ranked only within this dataset.",
        },
        {
            "Component": "Evidence pressure",
            "Type": "Observed support signal",
            "Logic": "10 x (0.35 negative-review share + 0.25 negative-rate share + 0.20 intensity share + 0.10 public-exposure share + 0.10 theme-size share).",
        },
        {
            "Component": "Evidence confidence",
            "Type": "Support-quality cue",
            "Logic": "10 x (0.45 review-base sufficiency + 0.25 average pipeline confidence + 0.15 platform coverage + 0.10 direct-map share + 0.05 no-low-sample bonus).",
        },
        {
            "Component": "Business impact estimate",
            "Type": "Executive judgment model",
            "Logic": "0.50 impact potential + 0.50 evidence pressure, where impact potential = 0.35 Productivity + 0.30 Operations + 0.20 Cost + 0.15 Reputation.",
        },
        {
            "Component": "Governance validation",
            "Type": "Integrity control",
            "Logic": "ARIA verifies the raw dataset, executive review dataset, and override table against aria_dataset_manifest.json before rendering the dashboard.",
        },
        {
            "Component": "Rank stability check",
            "Type": "Robustness test",
            "Logic": "Top themes are re-ranked across six scenario views: base risk, no YouTube, direct-map only, negative volume only, negative rate only, and negative intensity only.",
        },
    ]
)

comp_row = theme_summary[theme_summary["Theme"] == "Compensation & Benefits"].iloc[0]

top_business_impact = business_impact_table.iloc[0]
second_business_impact = business_impact_table.iloc[1]
third_business_impact = business_impact_table.iloc[2]
confidence_leader = business_impact_table.sort_values(
    by=["Evidence Confidence", "Current Negative Reviews"],
    ascending=False,
).iloc[0]
public_exposure_leader = business_impact_table.sort_values(
    by=["Public Exposure %", "Evidence Confidence", "Current Negative Reviews"],
    ascending=False,
).iloc[0]
glassdoor_theme_leader = platform_summary[
    (platform_summary["Platform"] == "Glassdoor") & (platform_summary["Reviews"] > 0)
].sort_values(
    by=["Negative Reviews", "Negative Rate %", "Reviews"],
    ascending=False,
).iloc[0]
youtube_theme_leader = platform_summary[
    (platform_summary["Platform"] == "YouTube") & (platform_summary["Reviews"] > 0)
].sort_values(
    by=["Negative Rate %", "Negative Reviews", "Avg Negative Intensity"],
    ascending=False,
).iloc[0]
small_sample_leader = low_sample_watchlist.iloc[0] if not low_sample_watchlist.empty else None
stability_lookup = stability_table.set_index("Theme")
risk_leader_stability = stability_lookup.loc[risk_leader["Theme"]]
top_business_impact_stability = stability_lookup.loc[top_business_impact["Theme"]]

decision_validation_map = {
    "Compensation & Benefits": {
        "Leadership Read": "Compensation and schedule design are the clearest external friction signal in this review set and should be reviewed before treating the issue as a pure recruiting shortage.",
        "Next KPI": "Overtime acceptance and fill rate by site and pay band",
        "Decision Use": "Comp review, scheduling review, and shift-fill pressure check",
    },
    "Workload & Burnout": {
        "Leadership Read": "Workload design appears to be creating sustained fatigue pressure and should be treated as an operations and safety review priority, not just a morale complaint cluster.",
        "Next KPI": "Absenteeism and late-call-off rate by workload-heavy department",
        "Decision Use": "Peak-workload redesign and labor-reliability review",
    },
    "Management & Communication": {
        "Leadership Read": "Manager variance and escalation handling appear to be a real control-system risk, not just isolated tone issues.",
        "Next KPI": "Write-up rates, department moves, and escalation closure time by manager",
        "Decision Use": "Frontline-control review and manager-variance audit",
    },
    "Career Growth": {
        "Leadership Read": "Advancement credibility looks like a secondary but persistent trust issue that can weaken retention credibility over time.",
        "Next KPI": "Promotion approvals by manager, tenure band, and segment",
        "Decision Use": "Promotion-criteria review and internal-mobility check",
    },
    "Work Culture": {
        "Leadership Read": "Low-volume dignity complaints carry outsized employee-relations and employer-brand exposure and should be handled as a policy-risk issue.",
        "Next KPI": "Employee-relations cases and policy exceptions tied to dignity complaints",
        "Decision Use": "Policy review and reputational-risk containment",
    },
}


def classify_conclusion_strength(
    evidence_confidence: float,
    stability_pct: float,
    negative_reviews_count: int,
    low_sample_risk: str,
) -> str:
    if (
        evidence_confidence >= 7.5
        and stability_pct >= 80
        and negative_reviews_count >= 10
        and low_sample_risk == "No"
    ):
        return "High for external-signal use"
    if evidence_confidence >= 6.0 and stability_pct >= 60:
        return "Moderate"
    return "Directional"

observed_findings = [
    f"{mono_number(top_drivers['Negative Reviews'].sum())} of {mono_number(negative_reviews)} negative reviews ({pct(top_driver_negative_share)}) sit in {top_driver_theme_list}. The negative signal is concentrated rather than spread evenly across all five themes.",
    f"{volume_leader['Theme']} carries the largest negative review volume in this sample: {mono_number(volume_leader['Negative Reviews'])} negative reviews across {mono_number(volume_leader['Reviews'])} reviews ({pct(volume_leader['Negative Rate %'])} negative, intensity {volume_leader['Avg Negative Intensity']:.1f}/100).",
    f"{risk_leader['Theme']} ranks first on the workforce risk index with score {risk_leader['Risk Score']:.1f} and remains in the top three in {mono_number(risk_leader_stability['Top 3 Appearances'])} of {mono_number(scenario_count)} scenario views, so the rank is not dependent on a single weighting choice.",
    f"YouTube is more negative in this sample but materially smaller in scale: n={mono_number(youtube_reviews)} with {pct(youtube_negative_rate)} negative (95% CI {ci_label(youtube_ci_low, youtube_ci_high)}) versus Glassdoor n={mono_number(glassdoor_reviews)} with {pct(glassdoor_negative_rate)} negative (95% CI {ci_label(glassdoor_ci_low, glassdoor_ci_high)}). Platform differences are therefore treated as pressure indicators, not equal-weight evidence.",
]

executive_judgment = [
    f"{top_business_impact['Theme']} should be treated as the strongest current executive priority, not because ARIA proves financial loss, but because its operating exposure and observed evidence align at {top_business_impact['Business Impact Rating']:.1f}/10 with evidence confidence {top_business_impact['Evidence Confidence']:.1f}/10 ({top_business_impact['Confidence Band']}).",
    f"{volume_leader['Theme']} should be treated as the first internal validation target because it carries the largest negative volume and is the most plausible place to test whether public friction is already showing up in shift fill, overtime acceptance, or retention loss.",
    f"{public_exposure_leader['Theme']} requires disproportionate policy attention when public-exposure pressure outruns review volume because small, severe complaint clusters can create outsized reputational or employee-relations escalation before the volume looks large in aggregate.",
    "Leadership can safely conclude that pay design, workload design, and frontline management controls are the three most defensible places to investigate next. Leadership should not claim causal turnover effects or ROI outcomes until internal KPIs are added.",
]

ranking_rationales = {}
for _, row in risk_ranking.iterrows():
    reasons = []
    if row["Theme"] == volume_leader["Theme"]:
        reasons.append("largest negative volume in the current dataset")
    if row["Theme"] == severity_leader["Theme"]:
        reasons.append("highest average negative intensity")
    if float(row["Negative Rate %"]) >= 50:
        reasons.append("more than half of its theme reviews are negative")
    if row["Theme"] == public_exposure_leader["Theme"]:
        reasons.append("strong public-exposure pressure")
    if not reasons:
        reasons.append("a smaller combined negative signal than the higher-ranked themes")

    if len(reasons) == 1:
        ranking_rationales[row["Theme"]] = reasons[0].capitalize() + "."
    else:
        ranking_rationales[row["Theme"]] = reasons[0].capitalize() + " and " + reasons[1] + "."

business_impact = [
    f"Productivity and cost: {top_business_impact['Theme']} carries the highest current business-impact estimate because its impact potential ({top_business_impact['Impact Potential']:.1f}/10) is reinforced by a strong observed signal ({top_business_impact['Evidence Pressure']:.1f}/10) and stable rank behavior.",
    "Operations: Management & Communication and Workload & Burnout remain the clearest execution-risk themes because they weaken frontline consistency, sustainable pace, and peak-period stability.",
    f"Decision use: {volume_leader['Theme']} is the largest negative-volume driver, while {public_exposure_leader['Theme']} carries the highest public-exposure pressure. That means the best current business conclusion is where to investigate first, not what outcome has already been proven.",
]

impact_evidence = [
    "The business-impact estimate now blends two visible components: impact potential from the operating model and observed evidence pressure from review volume, negative rate, severity, public exposure, and theme scale.",
    f"The strongest evidence confidence currently sits with {confidence_leader['Theme']} at {confidence_leader['Evidence Confidence']:.1f}/10, driven by sample depth, notebook pipeline confidence, direct-map share, and platform coverage.",
    f"YouTube remains more negative in this sample at {pct(youtube_negative_rate)} overall versus {pct(glassdoor_negative_rate)} on Glassdoor, but the smaller YouTube sample and wider interval mean that signal is treated as a multiplier on urgency, not as equal-weight proof.",
    "The business-impact estimate remains an executive prioritization layer. It is more data-informed than a fixed score, but it is still not a direct HR or finance KPI.",
]

defensibility_facts = [
    f"ARIA is reading the governed executive review dataset from {dataset_source_display}, generated from the raw pipeline output at {raw_dataset_source_display}.",
    f"The review base is {mono_number(total_reviews)} total reviews: Glassdoor n={mono_number(glassdoor_reviews)} and YouTube n={mono_number(youtube_reviews)}.",
    f"The governance manifest was generated at {manifest_generated_at} and the bundle hashes validate on load: raw {short_hash(raw_dataset_hash)}, executive {short_hash(executive_dataset_hash)}, override {short_hash(override_table_hash)}.",
    f"Executive theme provenance is explicit: {mono_number(assignment_count_lookup['Direct pipeline map'])} direct pipeline maps ({pct(direct_theme_share)}) and {mono_number(assignment_count_lookup['Executive override'])} explicit overrides ({pct(override_share)}). Override rows are validated against the original pipeline row signature, and ARIA no longer uses silent keyword fallback.",
    f"Notebook tagging confidence remains visible in the data: {mono_number(high_pipeline_confidence_reviews)} reviews are HIGH confidence ({pct(high_pipeline_confidence_share)}), while {mono_number(none_pipeline_confidence_reviews)} reviews carry NONE and are the rows most likely to require executive translation.",
    f"{mono_number(len(low_sample_watchlist))} platform-theme combinations are low-sample and should be read cautiously when the percentage is high but the denominator is below 5.",
    f"{stability_leader['Theme']} is the most stable theme under sensitivity testing, appearing in the top three in {mono_number(stability_leader['Top 3 Appearances'])} of {mono_number(scenario_count)} scenario views.",
    "Every presented review is assigned to one dominant theme so the model remains comparable across charts, but assignment confidence varies by method, and unresolved rows halt the app rather than being classified silently.",
]

what_this_does_not_claim = [
    "ARIA does not prove causality between review sentiment and actual turnover, injury, or absenteeism without internal HR and operations data.",
    "The workforce risk index is a relative ranking inside this dataset. It is not an industry benchmark and should not be read as a certified probability of exit.",
    "Negative intensity is a comparative severity index built from VADER magnitude. It should be used to compare themes, not as a literal measure of financial damage or worker harm.",
    "The business impact estimate is an executive prioritization model. It reflects operating judgment layered on top of observed evidence, not a machine-learned forecast.",
]

strategic_recommendations = [
    f"Reset pay transparency within 30 days. Publish site-level pay bands, overtime premiums, and flex-shift access rules so workers can see how heavy work converts into earnings. This directly targets Compensation & Benefits, which currently records {mono_number(comp_row['Negative Reviews'])} negative reviews.",
    "Protect schedule predictability. Require weekly earnings previews by shift, freeze last-minute schedule changes unless site leadership signs off, and standardize access to overtime windows. This addresses the schedule volatility showing up inside negative pay and burnout reviews.",
    "Standardize frontline manager behavior and promotion decisions. Track involuntary department moves, write-up rates, escalation closure time, and promotion approvals by manager; then tie those metrics to manager reviews. This directly addresses Management & Communication and the opaque advancement issues inside Career Growth.",
    "Redesign peak-week workload controls. Cap consecutive heavy-lift assignments, adjust productivity targets in bulky or high-strain zones, and protect break windows in scanner or time-off-task rules. This addresses Workload & Burnout, where complaints center on fatigue, rate pressure, and physical strain.",
    "Remove dignity-based triggers from performance management immediately. Bathroom breaks should not be timed, logged, or used as a disciplinary shortcut. This action directly targets Work Culture and its reputationally exposed dignity complaints.",
]

boardroom_opening = [
    f"The strongest conclusion today is concentration, not causality: {mono_number(top_drivers['Negative Reviews'].sum())} of {mono_number(negative_reviews)} negative reviews ({pct(top_driver_negative_share)}) sit in {top_driver_theme_list}.",
    f"{volume_leader['Theme']} is the largest negative-volume driver with {mono_number(volume_leader['Negative Reviews'])} negative reviews, while {risk_leader['Theme']} ranks first overall on workforce risk and stays in the top three in {mono_number(risk_leader_stability['Top 3 Appearances'])} of {mono_number(scenario_count)} scenario views.",
    f"{risk_leader['Theme']} ranks first on workforce risk, while {top_business_impact['Theme']} ranks first on business impact after blending operating exposure with observed evidence. That is a prioritization result, not proof of downstream losses.",
    f"Public testimony is smaller but harsher: YouTube is n={mono_number(youtube_reviews)} at {pct(youtube_negative_rate)} negative versus Glassdoor n={mono_number(glassdoor_reviews)} at {pct(glassdoor_negative_rate)} negative. Reputation risk is real, but the samples are not equal in weight.",
]

leadership_safe_claims = [
    f"It is safe to say that the external negative signal is concentrated in {top_driver_theme_list}, rather than spread evenly across all five themes.",
    f"It is safe to say that {volume_leader['Theme']}, {risk_leader['Theme']}, and {top_business_impact['Theme']} are the strongest current candidates for executive review because volume, risk rank, and impact estimate all point toward them.",
    "It is safe to say that ARIA supports targeted investigation and action prioritization. It is not safe to say that ARIA has proven turnover, injury, or ROI outcomes.",
    "It is safe to ask leadership for the next validating KPI immediately, because the current evidence is strong enough to justify follow-up but not strong enough to close the case on causality.",
]

conclusion_strength_rows = []
for _, row in risk_ranking.iterrows():
    theme = row["Theme"]
    impact_row = business_impact_table[business_impact_table["Theme"] == theme].iloc[0]
    stability_row = stability_lookup.loc[theme]
    guidance = decision_validation_map[theme]
    conclusion_strength_rows.append(
        {
            "Theme": theme,
            "Signal Strength": classify_conclusion_strength(
                float(impact_row["Evidence Confidence"]),
                float(stability_row["Top 3 Stability %"]),
                int(impact_row["Current Negative Reviews"]),
                str(impact_row["Low Sample Risk"]),
            ),
            "Evidence Confidence": f"{impact_row['Evidence Confidence']:.1f}/10",
            "Stability": f"{int(stability_row['Top 3 Appearances'])}/{scenario_count} scenarios",
            "What leadership can say now": guidance["Leadership Read"],
            "Next KPI to validate": guidance["Next KPI"],
            "Best decision use": guidance["Decision Use"],
        }
    )
conclusion_strength_table = pd.DataFrame(conclusion_strength_rows)

decision_agenda = pd.DataFrame(
    [
        {
            "Horizon": "0-30 days",
            "Executive move": "Reset pay transparency, overtime rules, and schedule predictability.",
            "Target theme": "Compensation & Benefits",
            "Primary owner": "CHRO + COO",
            "Success signal": "Lower pay-related complaints, stronger shift-fill reliability, fewer last-minute escalations.",
        },
        {
            "Horizon": "0-30 days",
            "Executive move": "Ban dignity-based discipline triggers such as bathroom-break policing.",
            "Target theme": "Work Culture",
            "Primary owner": "CHRO + Legal + Site Operations",
            "Success signal": "Reduced employee-relations risk and fewer severe public-facing complaints.",
        },
        {
            "Horizon": "30-60 days",
            "Executive move": "Install manager control metrics for write-ups, department moves, promotion approvals, and escalation closure times.",
            "Target theme": "Management & Communication",
            "Primary owner": "COO + HRBP leaders",
            "Success signal": "Lower manager-driven variance across shifts and sites.",
        },
        {
            "Horizon": "60-90 days",
            "Executive move": "Redesign peak workload controls, break protections, and heavy-lift rotations.",
            "Target theme": "Workload & Burnout",
            "Primary owner": "Operations + Safety + Workforce Planning",
            "Success signal": "Lower fatigue risk, steadier throughput, fewer absenteeism spikes during peak demand.",
        },
        {
            "Horizon": "60-90 days",
            "Executive move": "Publish clear promotion pathways and manager-calibrated advancement criteria.",
            "Target theme": "Career Growth",
            "Primary owner": "Talent + Site Leadership",
            "Success signal": "Higher internal mobility credibility and lower frustration among promotable workers.",
        },
    ]
)

kpi_request_table = pd.DataFrame(
    [
        {
            "KPI to request": "Voluntary exit rate",
            "Required cut": "By site, shift, tenure band, and manager",
            "Why it matters": "Tests whether the external review signal aligns with real retention loss.",
        },
        {
            "KPI to request": "Absenteeism and late-call-off rate",
            "Required cut": "By shift and workload-heavy department",
            "Why it matters": "Validates whether burnout is already reducing daily labor reliability.",
        },
        {
            "KPI to request": "Overtime acceptance and fill rate",
            "Required cut": "By site and pay band",
            "Why it matters": "Shows whether compensation friction is weakening surge capacity.",
        },
        {
            "KPI to request": "Safety incidents and restricted-duty cases",
            "Required cut": "By department and peak-period week",
            "Why it matters": "Tests the operating cost of workload pressure and physical strain.",
        },
        {
            "KPI to request": "Promotion approvals and write-up rates",
            "Required cut": "By manager and demographic segment",
            "Why it matters": "Surfaces management inconsistency and advancement credibility gaps.",
        },
    ]
)

challenge_response_table = pd.DataFrame(
    [
        {
            "Likely challenge": "Why are you forcing everything into five themes?",
            "Answer anchor": "The five-theme structure is deliberate. It prevents taxonomy sprawl and keeps every recommendation tied to an executive decision bucket.",
        },
        {
            "Likely challenge": "Are these findings causal?",
            "Answer anchor": "No. ARIA shows external worker-sentiment evidence and ranks pressure points; it does not claim causal proof without internal HR and operations data.",
        },
        {
            "Likely challenge": "How reliable is the theme assignment?",
            "Answer anchor": f"{pct(direct_theme_share)} of reviews map directly from the notebook primary_theme. The remaining {pct(override_share)} are explicit executive overrides of unsupported pipeline rows, validated against the original row signature and disclosed in the audit.",
        },
        {
            "Likely challenge": "Why is YouTube more negative than Glassdoor?",
            "Answer anchor": f"We treat that as descriptive rather than causal. YouTube is harsher, but it is only n={mono_number(youtube_reviews)} with a wider 95% interval ({ci_label(youtube_ci_low, youtube_ci_high)}) versus Glassdoor n={mono_number(glassdoor_reviews)} ({ci_label(glassdoor_ci_low, glassdoor_ci_high)}), so it is an urgency signal rather than equal-weight proof.",
        },
        {
            "Likely challenge": "Does the ranking collapse if the weighting changes?",
            "Answer anchor": f"ARIA stress-tests the rank across {mono_number(scenario_count)} scenario views. {stability_leader['Theme']} is the most stable theme, appearing in the top three in {mono_number(stability_leader['Top 3 Appearances'])} of those views.",
        },
        {
            "Likely challenge": f"Why does {top_business_impact['Theme']} rank first in business impact?",
            "Answer anchor": f"{volume_leader['Theme']} is the largest negative-volume driver, but {top_business_impact['Theme']} ranks first in business impact because its operating impact potential and observed evidence combine more strongly in the current model.",
        },
    ]
)

page_guide_table = pd.DataFrame(
    [
        {
            "Page": "Executive Brief",
            "Purpose": "Condensed readout of findings, risk, impact, and actions.",
        },
        {
            "Page": "Decision Agenda",
            "Purpose": "Opening narrative, actions, KPI requests, and challenge responses.",
        },
        {
            "Page": "Risk Ranking",
            "Purpose": "Current order of workforce pressure across the five themes.",
        },
        {
            "Page": "Impact Case",
            "Purpose": "Operating, cost, and reputation exposure by theme.",
        },
        {
            "Page": "Evidence by Platform",
            "Purpose": "Cross-platform readout with sample-size context.",
        },
        {
            "Page": "Method Appendix",
            "Purpose": "Data provenance, controls, formulas, and limits.",
        },
        {
            "Page": "Evidence Audit",
            "Purpose": "Row-level traceability for the governed review set.",
        },
    ]
)

executive_brief_text = "\n".join(
    [
        "# ARIA Executive Brief",
        "",
        "## Key Findings",
        *[f"- {item}" for item in observed_findings],
        "",
        "## Executive Judgment",
        *[f"- {item}" for item in executive_judgment],
        "",
        "## What Leadership Can Say Today",
        *[f"- {item}" for item in leadership_safe_claims],
        "",
        "## Risk Ranking",
        *[
            f"{int(row['Rank'])}. {row['Theme']} | risk {row['Risk Score']:.1f} | {mono_number(row['Negative Reviews'])} negative reviews | {pct(row['Negative Rate %'])} negative | intensity {row['Avg Negative Intensity']:.1f}/100"
            for _, row in risk_ranking.iterrows()
        ],
        "",
        "## Impact Case",
        *[f"- {item}" for item in business_impact],
        "",
        "## Strategic Recommendations",
        *[f"{i + 1}. {item}" for i, item in enumerate(strategic_recommendations)],
    ]
)

method_appendix_text = "\n".join(
    [
        "# ARIA Method Appendix",
        "",
        "## Method Facts",
        *[f"- {item}" for item in defensibility_facts],
        "",
        "## Governance Bundle",
        *[
            f"- {row['Artifact']}: {row['Path']} | hash {row['SHA256']}"
            for _, row in governance_status_table.iterrows()
        ],
        "",
        "## Rank Stability",
        *[
            f"- {row['Scenario']}: {row['Top 1']}, {row['Top 2']}, {row['Top 3']}"
            for _, row in scenario_table.iterrows()
        ],
        "",
        "## What This Does Not Claim",
        *[f"- {item}" for item in what_this_does_not_claim],
        "",
        "## Formula Reference",
        *[
            f"- {row['Component']} ({row['Type']}): {row['Logic']}"
            for _, row in formula_table.iterrows()
        ],
    ]
)

st.markdown(
    """
    <div class='hero'>
        <div class='hero-kicker'>ARIA project</div>
        <h1>ARIA</h1>
        <p>
            Executive workforce risk review built from external worker sentiment on Glassdoor and YouTube.
            ARIA turns the final pipeline output into leadership priorities for workforce risk, operating disruption,
            and immediate action inside a fulfillment-style labor environment.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class='panel' style='margin-bottom:18px;'>
        <h3 style='margin:0 0 10px 0;'>Project Framing</h3>
        <p style='margin:0 0 10px 0; color:#475569; line-height:1.7;'>
            ARIA answers one executive question: which workforce issues are most likely to drive workforce risk,
            operating damage, and leadership intervention right now?
        </p>
        <p style='margin:0; color:#475569; line-height:1.7;'>
            Evidence comes from a governed review bundle: the raw final pipeline dataset, a reviewed executive translation layer,
            a signed override table, and a validated manifest. ARIA translates that evidence into five decision themes only:
            Workload &amp; Burnout, Management &amp; Communication, Compensation &amp; Benefits, Career Growth,
            and Work Culture.
        </p>
        <p style='margin:10px 0 0 0; color:#475569; line-height:1.7;'>
            The governance layer, executive scoring logic, dashboard narrative, and deployment configuration are delivered here as one integrated project.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Page Summary", expanded=False):
    st.dataframe(page_guide_table, use_container_width=True, hide_index=True)

metric_cols = st.columns(6)
metric_cols[0].metric("Total Reviews", mono_number(total_reviews))
metric_cols[1].metric(
    "Negative Reviews",
    mono_number(negative_reviews),
    f"{pct(overall_negative_rate)} overall | 95% CI {ci_label(overall_ci_low, overall_ci_high)}",
)
metric_cols[2].metric(
    "Glassdoor Negative",
    pct(glassdoor_negative_rate),
    f"n={mono_number(glassdoor_reviews)} | 95% CI {ci_label(glassdoor_ci_low, glassdoor_ci_high)}",
)
metric_cols[3].metric(
    "YouTube Negative",
    pct(youtube_negative_rate),
    f"n={mono_number(youtube_reviews)} | 95% CI {ci_label(youtube_ci_low, youtube_ci_high)}",
)
metric_cols[4].metric(
    "Pipeline HIGH Confidence",
    pct(high_pipeline_confidence_share),
    f"{mono_number(high_pipeline_confidence_reviews)} reviews",
)
metric_cols[5].metric("Top 3 Driver Share", pct(top_driver_negative_share))

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "Executive Brief",
        "Decision Agenda",
        "Risk Ranking",
        "Impact Case",
        "Evidence by Platform",
        "Method Appendix",
        "Evidence Audit",
    ]
)

with tab1:
    st.markdown("## Key Findings")
    section_subtitle(
        "Condensed readout of findings, risk, impact, and actions."
    )

    driver_cols = st.columns(3)
    for idx, (_, row) in enumerate(top_drivers.iterrows()):
        gd_rate = platform_value(platform_summary, row["Theme"], "Glassdoor", "Negative Rate %")
        yt_rate = platform_value(platform_summary, row["Theme"], "YouTube", "Negative Rate %")
        gd_reviews = platform_value(platform_summary, row["Theme"], "Glassdoor", "Reviews")
        yt_reviews = platform_value(platform_summary, row["Theme"], "YouTube", "Reviews")
        impact_row = business_impact_table[business_impact_table["Theme"] == row["Theme"]].iloc[0]
        stability_row = stability_lookup.loc[row["Theme"]]
        theme_color = THEME_COLORS[row["Theme"]]
        driver_cols[idx].markdown(
            f"""
            <div class='driver-card' style='border-top-color:{theme_color};'>
                <div class='driver-rank'>Observed driver {idx + 1}</div>
                <div class='driver-theme'>{row["Theme"]}</div>
                <div class='driver-meta'>
                    Negative reviews: {mono_number(row["Negative Reviews"])} of {mono_number(row["Reviews"])}<br>
                    Negative intensity: {row["Avg Negative Intensity"]:.1f}/100<br>
                    Glassdoor negative: {pct(gd_rate)} on n={mono_number(gd_reviews)}<br>
                    YouTube negative: {pct(yt_rate)} on n={mono_number(yt_reviews)}<br>
                    Evidence confidence: {impact_row["Evidence Confidence"]:.1f}/10<br>
                    Top-3 stability: {int(stability_row["Top 3 Appearances"])}/{scenario_count} scenarios
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Observed In Data")
    render_bullet_list(observed_findings)

    st.markdown("### Executive Judgment Based On Operating Logic")
    render_bullet_list(executive_judgment)

    st.markdown("### Conclusion Strength By Theme")
    section_subtitle(
        "This is the safest business-reading layer: what leadership can say now, how strong the signal is, and which KPI should validate it next."
    )
    st.dataframe(
        conclusion_strength_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Theme": st.column_config.TextColumn("Theme", width="small"),
            "Signal Strength": st.column_config.TextColumn("Signal Strength", width="small"),
            "Evidence Confidence": st.column_config.TextColumn("Evidence Confidence", width="small"),
            "Stability": st.column_config.TextColumn("Stability", width="small"),
            "What leadership can say now": st.column_config.TextColumn("What leadership can say now", width="large"),
            "Next KPI to validate": st.column_config.TextColumn("Next KPI to validate", width="medium"),
            "Best decision use": st.column_config.TextColumn("Best decision use", width="medium"),
        },
    )

    st.markdown("---")
    st.markdown("## Risk Ranking")
    section_subtitle("Current order of workforce pressure across the five themes.")
    for _, row in risk_ranking.iterrows():
        st.markdown(
            f"""
            <div class='ranking-item'>
                <strong>{int(row["Rank"])}. {row["Theme"]}</strong><br>
                Risk score {row["Risk Score"]:.1f} | {mono_number(row["Negative Reviews"])} negative reviews |
                {pct(row["Negative Rate %"])} negative | intensity {row["Avg Negative Intensity"]:.1f}/100<br>
                <span style='color:#475569'>{ranking_rationales[row["Theme"]]}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("## Impact Case Summary")
    render_bullet_list(business_impact)

    st.markdown("## Strategic Recommendations")
    render_numbered_list(strategic_recommendations)

with tab2:
    st.markdown("## Decision Agenda")
    section_subtitle(
        "Opening narrative, actions, KPI requests, and challenge responses."
    )

    st.markdown(
        f"""
        <div class='callout'>
            Three points to land first: pressure is concentrated in {top_driver_theme_list}, {volume_leader['Theme']} is the largest negative-volume driver, and {top_business_impact['Theme']} is the strongest operating-impact estimate.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 90-Second Opening")
    render_bullet_list(boardroom_opening)

    st.markdown("### What Leadership Can Say Today")
    render_bullet_list(leadership_safe_claims)

    download_cols = st.columns(4)
    download_cols[0].download_button(
        "Download ARIA Brief",
        data=executive_brief_text,
        file_name="aria_executive_brief.md",
        mime="text/markdown",
        use_container_width=True,
    )
    download_cols[1].download_button(
        "Download Method Appendix",
        data=method_appendix_text,
        file_name="aria_method_appendix.md",
        mime="text/markdown",
        use_container_width=True,
    )
    download_cols[2].download_button(
        "Export Risk Ranking (CSV)",
        data=risk_ranking.to_csv(index=False),
        file_name="aria_risk_ranking.csv",
        mime="text/csv",
        use_container_width=True,
    )
    download_cols[3].download_button(
        "Export Impact Case (CSV)",
        data=business_impact_table.to_csv(index=False),
        file_name="aria_impact_case.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("### 30 / 60 / 90 Day Decision Agenda")
    st.dataframe(
        decision_agenda,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Horizon": st.column_config.TextColumn("Horizon", width="small"),
            "Executive move": st.column_config.TextColumn("Executive move", width="large"),
            "Target theme": st.column_config.TextColumn("Target theme", width="medium"),
            "Primary owner": st.column_config.TextColumn("Primary owner", width="medium"),
            "Success signal": st.column_config.TextColumn("Success signal", width="large"),
        },
    )

    st.markdown("### Metrics Leadership Should Demand Next Week")
    st.dataframe(
        kpi_request_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "KPI to request": st.column_config.TextColumn("KPI to request", width="medium"),
            "Required cut": st.column_config.TextColumn("Required cut", width="medium"),
            "Why it matters": st.column_config.TextColumn("Why it matters", width="large"),
        },
    )

    st.markdown("### Challenge Response Grid")
    st.caption("Anticipated pushback and anchored responses. Click each to read the full answer.")
    for _, row in challenge_response_table.iterrows():
        with st.expander(f"**{row['Likely challenge']}**"):
            st.markdown(row["Answer anchor"])

with tab3:
    st.markdown("## Risk Ranking")
    section_subtitle(
        "Current ranking of workforce pressure across the five themes."
    )

    risk_chart = risk_ranking.copy().sort_values("Risk Score", ascending=True)
    fig_risk = go.Figure(
        go.Bar(
            x=risk_chart["Risk Score"],
            y=risk_chart["Theme"],
            orientation="h",
            marker_color=[THEME_COLORS[t] for t in risk_chart["Theme"]],
            text=[
                f"{pct(rate)} | {mono_number(neg)} neg"
                for rate, neg in zip(risk_chart["Negative Rate %"], risk_chart["Negative Reviews"])
            ],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Risk score: %{x:.1f}<extra></extra>",
        )
    )
    fig_risk.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="IBM Plex Sans", size=13, color="#0f172a"),
        margin=dict(t=26, b=28, l=180, r=140),
        height=380,
        xaxis=dict(
            title="Workforce risk score",
            gridcolor="#e2e8f0",
            tickfont=dict(color="#334155"),
            title_font=dict(color="#475569"),
            automargin=True,
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            tickfont=dict(color="#334155", size=14),
            automargin=True,
        ),
        showlegend=False,
    )
    fig_risk.update_traces(textfont_color="#0f172a", cliponaxis=False)
    st.plotly_chart(fig_risk, use_container_width=True, config=PLOTLY_CONFIG)

    st.markdown("### Risk Table")
    risk_table = risk_ranking[
        [
            "Rank",
            "Theme",
            "Reviews",
            "Negative Reviews",
            "Negative Rate %",
            "Negative Rate CI",
            "Sample Read",
            "Avg Negative Intensity",
            "Risk Score",
        ]
    ].copy()
    st.dataframe(risk_table, use_container_width=True, hide_index=True)

    st.markdown("### Sentiment Distribution by Theme")
    sentiment_chart_df = sentiment_theme_summary.copy()
    sentiment_chart_df["Theme"] = pd.Categorical(
        sentiment_chart_df["Theme"],
        categories=risk_ranking["Theme"].tolist(),
        ordered=True,
    )
    fig_sentiment = px.bar(
        sentiment_chart_df.sort_values("Theme"),
        x="Theme",
        y="Count",
        color="Sentiment",
        barmode="stack",
        color_discrete_map={
            "Positive": SENTIMENT_COLORS["positive"],
            "Neutral": SENTIMENT_COLORS["neutral"],
            "Negative": SENTIMENT_COLORS["negative"],
        },
    )
    fig_sentiment.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="IBM Plex Sans", size=13, color="#0f172a"),
        margin=dict(t=26, b=28, l=12, r=12),
        height=420,
        xaxis_title="Theme",
        yaxis_title="Reviews",
        legend_title="Sentiment",
    )
    fig_sentiment.update_xaxes(
        tickfont=dict(color="#334155"),
        title_font=dict(color="#475569"),
        automargin=True,
    )
    fig_sentiment.update_yaxes(
        tickfont=dict(color="#334155"),
        title_font=dict(color="#475569"),
        automargin=True,
    )
    st.plotly_chart(fig_sentiment, use_container_width=True, config=PLOTLY_CONFIG)

with tab4:
    st.markdown("## Impact Case")
    section_subtitle(
        "Operating, cost, and reputation exposure by theme."
    )

    st.markdown("### Observed Evidence Feeding The Estimate")
    render_bullet_list(impact_evidence)

    impact_cols = st.columns(3)
    for idx, row in enumerate([top_business_impact, second_business_impact, third_business_impact]):
        theme_color = THEME_COLORS[row["Theme"]]
        impact_cols[idx].markdown(
            f"""
            <div class='driver-card' style='border-top-color:{theme_color};'>
                <div class='driver-rank'>Executive estimate {int(row["Impact Rank"])}</div>
                <div class='driver-theme'>{row["Theme"]}</div>
                <div class='driver-meta'>
                    Business impact estimate: {row["Business Impact Rating"]:.1f}/10<br>
                    Impact potential: {row["Impact Potential"]:.1f}/10<br>
                    Observed evidence pressure: {row["Evidence Pressure"]:.1f}/10<br>
                    Evidence confidence: {row["Evidence Confidence"]:.1f}/10 ({row["Confidence Band"]})<br>
                    Current negatives: {mono_number(row["Current Negative Reviews"])}<br>
                    {row["Impact Summary"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    impact_compare = risk_ranking[["Theme", "Workforce Risk Rating"]].merge(
        business_impact_table[["Theme", "Business Impact Rating"]],
        on="Theme",
        how="left",
    )
    impact_compare["Theme"] = pd.Categorical(
        impact_compare["Theme"],
        categories=business_impact_table["Theme"].tolist(),
        ordered=True,
    )
    impact_compare_long = impact_compare.melt(
        id_vars="Theme",
        value_vars=["Business Impact Rating", "Workforce Risk Rating"],
        var_name="Score Type",
        value_name="Rating",
    )
    impact_compare_long["Score Type"] = impact_compare_long["Score Type"].map(
        {
            "Business Impact Rating": "Business impact estimate",
            "Workforce Risk Rating": "Workforce risk index",
        }
    )
    fig_compare = px.bar(
        impact_compare_long.sort_values("Theme"),
        x="Theme",
        y="Rating",
        color="Score Type",
        barmode="group",
        text="Rating",
        color_discrete_map={
            "Business impact estimate": "#13315c",
            "Workforce risk index": "#b42318",
        },
    )
    fig_compare.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="IBM Plex Sans", size=13, color="#0f172a"),
        margin=dict(t=26, b=40, l=40, r=12),
        height=420,
        xaxis_title="Theme",
        yaxis_title="Relative rating / 10",
        legend_title="Score type",
    )
    fig_compare.update_xaxes(
        tickfont=dict(color="#334155"),
        title_font=dict(color="#475569"),
        automargin=True,
    )
    fig_compare.update_yaxes(
        tickfont=dict(color="#334155"),
        title_font=dict(color="#475569"),
        automargin=True,
    )
    fig_compare.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside",
        textfont_color="#0f172a",
        cliponaxis=False,
    )
    st.plotly_chart(fig_compare, use_container_width=True, config=PLOTLY_CONFIG)

    ordered_impact = business_impact_table.sort_values("Business Impact Rating", ascending=False)
    heatmap_x = ["Productivity Impact", "Operational Impact", "Cost Impact", "Reputation Impact"]
    heatmap_y = ordered_impact["Theme"].tolist()
    heatmap_z = ordered_impact[heatmap_x].values.tolist()
    fig_heatmap = go.Figure(
        data=go.Heatmap(
            z=heatmap_z,
            x=["Productivity", "Operations", "Cost", "Reputation"],
            y=heatmap_y,
            colorscale=[
                [0.0, "#e7eef9"],
                [0.5, "#7fa2d6"],
                [1.0, "#13315c"],
            ],
            zmin=5,
            zmax=10,
            colorbar=dict(
                tickfont=dict(color="#334155"),
                title=dict(font=dict(color="#475569")),
            ),
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}/10<extra></extra>",
        )
    )
    fig_heatmap.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="IBM Plex Sans", size=13, color="#0f172a"),
        margin=dict(t=26, b=48, l=180, r=28),
        height=360,
        xaxis=dict(
            tickfont=dict(color="#334155"),
            title_font=dict(color="#475569"),
            automargin=True,
        ),
        yaxis=dict(
            tickfont=dict(color="#334155"),
            title_font=dict(color="#475569"),
            automargin=True,
        ),
    )
    st.plotly_chart(fig_heatmap, use_container_width=True, config=PLOTLY_CONFIG)

    st.markdown("### Impact Case Table")
    impact_table = ordered_impact[
        [
            "Impact Rank",
            "Theme",
            "Business Impact Rating",
            "Impact Tier",
            "Impact Potential",
            "Evidence Pressure",
            "Evidence Confidence",
            "Confidence Band",
            "Current Negative Reviews",
            "Current Negative Rate %",
            "Current Negative Intensity",
            "Public Exposure %",
            "Avg Pipeline Confidence",
            "High Pipeline Confidence %",
            "Direct Map Share %",
        ]
    ].copy()
    impact_table = impact_table.rename(
        columns={
            "Business Impact Rating": "Impact Case Rating",
            "Impact Potential": "Impact Potential",
            "Evidence Pressure": "Observed Evidence Pressure",
            "Evidence Confidence": "Evidence Confidence",
            "Public Exposure %": "Public Exposure %",
            "Avg Pipeline Confidence": "Avg Pipeline Confidence / 10",
            "High Pipeline Confidence %": "Pipeline HIGH Confidence %",
            "Direct Map Share %": "Direct Pipeline Map %",
        }
    )
    st.dataframe(impact_table, use_container_width=True, hide_index=True)

with tab5:
    st.markdown("## Evidence by Platform")
    section_subtitle(
        "Cross-platform signal comparison with sample-size context."
    )

    c1, c2, c3 = st.columns(3)
    c1.markdown(
        f"""
        <div class='panel'>
            <h3 style='margin:0 0 6px 0;'>Glassdoor</h3>
            <p style='font-family:IBM Plex Mono, monospace; font-size:34px; margin:0; color:#13315c;'>{pct(glassdoor_negative_rate)}</p>
            <p class='small-note'>95% CI {ci_label(glassdoor_ci_low, glassdoor_ci_high)}. Written reviews are materially less negative than video testimony.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c2.markdown(
        f"""
        <div class='panel'>
            <h3 style='margin:0 0 6px 0;'>YouTube</h3>
            <p style='font-family:IBM Plex Mono, monospace; font-size:34px; margin:0; color:#b42318;'>{pct(youtube_negative_rate)}</p>
            <p class='small-note'>95% CI {ci_label(youtube_ci_low, youtube_ci_high)}. Public worker testimony is sharper, but this platform is only n={mono_number(youtube_reviews)} in the current dataset.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c3.markdown(
        f"""
        <div class='panel'>
            <h3 style='margin:0 0 6px 0;'>Gap</h3>
            <p style='font-family:IBM Plex Mono, monospace; font-size:34px; margin:0; color:#0f172a;'>{youtube_negative_rate - glassdoor_negative_rate:.1f} pts</p>
            <p class='small-note'>Leadership should assume the written review picture understates the public severity of workforce-risk drivers.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    platform_chart = platform_summary.copy()
    platform_chart["Theme"] = pd.Categorical(
        platform_chart["Theme"],
        categories=risk_ranking["Theme"].tolist(),
        ordered=True,
    )
    fig_platform = px.bar(
        platform_chart.sort_values("Theme"),
        x="Theme",
        y="Negative Rate %",
        color="Platform",
        barmode="group",
        text="Negative Reviews",
        color_discrete_map=PLATFORM_COLORS,
    )
    fig_platform.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="IBM Plex Sans", size=13, color="#0f172a"),
        margin=dict(t=26, b=48, l=40, r=12),
        height=440,
        xaxis_title="Theme",
        yaxis_title="Negative rate %",
        legend_title="Platform",
    )
    fig_platform.update_xaxes(
        tickfont=dict(color="#334155"),
        title_font=dict(color="#475569"),
        automargin=True,
    )
    fig_platform.update_yaxes(
        tickfont=dict(color="#334155"),
        title_font=dict(color="#475569"),
        automargin=True,
    )
    fig_platform.update_traces(
        texttemplate="%{text} neg",
        textposition="outside",
        textfont_color="#0f172a",
        cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:.1f}% negative<extra></extra>",
    )
    st.plotly_chart(fig_platform, use_container_width=True, config=PLOTLY_CONFIG)

    platform_findings = [
        f"Glassdoor is the base-rate view. Its strongest negative theme is {glassdoor_theme_leader['Theme']} at {pct(glassdoor_theme_leader['Negative Rate %'])} negative on n={mono_number(glassdoor_theme_leader['Reviews'])} with 95% CI {glassdoor_theme_leader['Negative Rate CI']}.",
        f"YouTube is the escalation-tone view. Its sharpest signal is {youtube_theme_leader['Theme']} at {pct(youtube_theme_leader['Negative Rate %'])} negative on n={mono_number(youtube_theme_leader['Reviews'])} with 95% CI {youtube_theme_leader['Negative Rate CI']}.",
        (
            f"{small_sample_leader['Theme']} on {small_sample_leader['Platform']} is a low-sample caution case at {pct(small_sample_leader['Negative Rate %'])} negative on n={mono_number(small_sample_leader['Reviews'])} with 95% CI {small_sample_leader['Negative Rate CI']}."
            if small_sample_leader is not None
            else "No platform-theme pair is currently flagged as low-sample."
        ),
    ]
    st.markdown("### Cross-Platform Readout")
    render_bullet_list(platform_findings)

with tab6:
    st.markdown("## Method Appendix")
    section_subtitle(
        "Data provenance, controls, formulas, and limits."
    )

    provenance_cols = st.columns(4)
    provenance_cols[0].metric(
        "Direct Pipeline Map",
        mono_number(assignment_count_lookup["Direct pipeline map"]),
        f"{pct(assignment_share_lookup['Direct pipeline map'])} of reviews",
    )
    provenance_cols[1].metric(
        "Executive Override",
        mono_number(assignment_count_lookup["Executive override"]),
        f"{pct(assignment_share_lookup['Executive override'])} of reviews",
    )
    provenance_cols[2].metric(
        "Pipeline HIGH Confidence",
        mono_number(high_pipeline_confidence_reviews),
        f"{pct(high_pipeline_confidence_share)} of reviews",
    )
    provenance_cols[3].metric(
        "Low-Sample Theme Pairs",
        mono_number(len(low_sample_watchlist)),
        "Platform-theme pairs with n < 5",
    )

    with st.expander("NLP Model Selection", expanded=False):
        st.markdown(
            """
            Three sentiment models were tested against human-coded labels on 10 YouTube transcripts
            (the gold standard for spoken worker content). VADER was selected based on measured accuracy,
            not assumption.
            """
        )
        model_selection_table = pd.DataFrame(
            [
                {
                    "Model": "TextBlob",
                    "Accuracy": "30%",
                    "Decision": "Rejected",
                    "Reason": "Too sensitive to negation patterns in informal speech",
                },
                {
                    "Model": "RoBERTa",
                    "Accuracy": "50%",
                    "Decision": "Rejected",
                    "Reason": "Over-corrects polarity on long spoken content",
                },
                {
                    "Model": "VADER",
                    "Accuracy": "70%",
                    "Decision": "Selected",
                    "Reason": "Consistent performance on informal workplace language",
                },
            ]
        )
        st.dataframe(model_selection_table, use_container_width=True, hide_index=True)
        st.caption(
            "Validation method: human-coded sentiment labels on YouTube transcripts compared against each model's output. "
            "VADER's 70% accuracy is adequate for this domain but means ~30% of labels may be misclassified."
        )

    with st.expander("Data Quality Validation (18 Checks)", expanded=False):
        st.markdown(
            """
            Every row in `final_aria_dataset.csv` passed all 18 checks before any analysis was run.
            **Result: zero errors, no imputation, no estimation.**
            """
        )
        validation_checks = pd.DataFrame(
            [
                {"#": 1, "Check": "Row count", "Validates": "Matches expected total (150)"},
                {"#": 2, "Check": "Platform field", "Validates": "No nulls, only Glassdoor or YouTube"},
                {"#": 3, "Check": "Cleaned text", "Validates": "No nulls across all reviews"},
                {"#": 4, "Check": "VADER score", "Validates": "Numeric, within -1 to +1 range"},
                {"#": 5, "Check": "VADER label", "Validates": "Only positive, negative, or neutral"},
                {"#": 6, "Check": "Final sentiment", "Validates": "Only positive, negative, or neutral"},
                {"#": 7, "Check": "Sentiment consistency", "Validates": "Final sentiment aligns with VADER score direction"},
                {"#": 8, "Check": "Primary theme", "Validates": "Valid theme codes only (T1-T5)"},
                {"#": 9, "Check": "Theme count", "Validates": "Non-negative integer"},
                {"#": 10, "Check": "Confidence", "Validates": "Only HIGH, MEDIUM, LOW, or NONE"},
                {"#": 11, "Check": "Duplicate check", "Validates": "No duplicate source IDs within platform"},
                {"#": 12, "Check": "Foreign language", "Validates": "Flagged as LANG_NOT_SUPPORTED, not silently dropped"},
                {"#": 13, "Check": "Glassdoor rating", "Validates": "Within 1-5 range where present"},
                {"#": 14, "Check": "YouTube isolation", "Validates": "No Glassdoor-specific fields on YouTube rows"},
                {"#": 15, "Check": "Human sentiment", "Validates": "Present for all 10 YouTube rows"},
                {"#": 16, "Check": "Would-they-return", "Validates": "Present for all 10 YouTube rows"},
                {"#": 17, "Check": "Theme keywords", "Validates": "At least one keyword match for HIGH confidence rows"},
                {"#": 18, "Check": "Platform count", "Validates": "Glassdoor + YouTube = 150"},
            ]
        )
        st.dataframe(validation_checks, use_container_width=True, hide_index=True)

    method_col1, method_col2 = st.columns(2)
    with method_col1:
        st.markdown("### Method Facts")
        render_bullet_list(defensibility_facts)
    with method_col2:
        st.markdown("### What This Does Not Claim")
        render_bullet_list(what_this_does_not_claim)

    st.markdown("### Low-Sample Watchlist")
    if low_sample_watchlist.empty:
        st.info("No platform-theme combinations fall below n=5 in the current dataset.")
    else:
        st.dataframe(
            low_sample_watchlist[
                [
                    "Theme",
                    "Platform",
                    "Reviews",
                    "Negative Reviews",
                    "Negative Rate %",
                    "Negative Rate CI",
                    "Sample Read",
                    "Avg Negative Intensity",
                    "Caution Level",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Governance Bundle Status", expanded=False):
        st.dataframe(governance_status_table, use_container_width=True, hide_index=True)

    with st.expander("Rank Stability", expanded=False):
        st.dataframe(scenario_table, use_container_width=True, hide_index=True)
        st.dataframe(stability_table, use_container_width=True, hide_index=True)

    with st.expander("Formula Reference", expanded=False):
        st.dataframe(formula_table, use_container_width=True, hide_index=True)

    with st.expander("Manual Override Audit", expanded=False):
        st.markdown(
            "These rows were translated through explicit source-level overrides because the notebook output was unsupported for five-theme executive reporting."
        )
        st.dataframe(override_audit, use_container_width=True, hide_index=True)

with tab7:
    st.markdown("## Evidence Audit")
    section_subtitle(
        "Row-level traceability for the governed review set."
    )

    audit_cols = st.columns(3)
    selected_platforms = audit_cols[0].multiselect(
        "Platform",
        options=sorted(df["platform"].unique().tolist()),
        default=sorted(df["platform"].unique().tolist()),
    )
    selected_themes = audit_cols[1].multiselect(
        "Theme",
        options=EXEC_THEMES,
        default=EXEC_THEMES,
    )
    selected_sentiments = audit_cols[2].multiselect(
        "Sentiment",
        options=["positive", "neutral", "negative"],
        default=["positive", "neutral", "negative"],
    )

    audit_df = df[
        df["platform"].isin(selected_platforms)
        & df["executive_theme"].isin(selected_themes)
        & df["final_sentiment"].isin(selected_sentiments)
    ][
        [
            "source_id",
            "platform",
            "primary_theme",
            "pipeline_confidence",
            "executive_theme",
            "executive_theme_confidence",
            "override_reason",
            "assignment_method",
            "final_sentiment",
            "negative_intensity_pct",
            "cleaned_text",
        ]
    ].rename(
        columns={
            "source_id": "Source ID",
            "platform": "Platform",
            "primary_theme": "Pipeline Theme",
            "pipeline_confidence": "Pipeline Confidence",
            "executive_theme": "Executive Theme",
            "executive_theme_confidence": "Executive Theme Confidence",
            "override_reason": "Override Reason",
            "assignment_method": "Translation Method",
            "final_sentiment": "Sentiment",
            "negative_intensity_pct": "VADER Intensity Reference",
            "cleaned_text": "Review Text",
        }
    )

    st.dataframe(audit_df, use_container_width=True, hide_index=True)

    st.download_button(
        "Export Audit Data (CSV)",
        data=audit_df.to_csv(index=False),
        file_name="aria_evidence_audit.csv",
        mime="text/csv",
        use_container_width=True,
    )

# Governance footer
st.markdown(
    f"""
    <div class='gov-footer'>
        ARIA Governance &middot; Manifest {manifest_generated_at} &middot;
        Executive dataset {short_hash(executive_dataset_hash)} &middot;
        Override table {short_hash(override_table_hash)} &middot;
        n={mono_number(total_reviews)} reviews &middot; {mono_number(len(EXEC_THEMES))} themes
    </div>
    """,
    unsafe_allow_html=True,
)
