from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "01_Data" / "final_aria_dataset.csv"
EXECUTIVE_DATA_PATH = PROJECT_ROOT / "01_Data" / "aria_executive_review_dataset.csv"
OVERRIDE_TABLE_PATH = PROJECT_ROOT / "01_Data" / "aria_executive_overrides.csv"
MANIFEST_PATH = PROJECT_ROOT / "01_Data" / "aria_dataset_manifest.json"

PRIMARY_THEME_MAP: Dict[str, str] = {
    "T1_Physical_Degradation": "Workload & Burnout",
    "T2_Nepotism_Advancement": "Career Growth",
    "T3_Pay_Benefits": "Compensation & Benefits",
    "T4_Supervisor_Inconsistency": "Management & Communication",
    "T5_Bathroom_Dignity": "Work Culture",
}

OVERRIDE_SPECS: List[Dict[str, str]] = [
    {
        "source_id": 15,
        "platform": "Glassdoor",
        "primary_theme": "Untagged",
        "confidence": "NONE",
        "cleaned_text": "good reference previous work con knowledge",
        "executive_theme": "Career Growth",
        "override_reason": "Reference to prior knowledge is weak evidence, but it aligns more closely with advancement and employability than with pay, workload, management, or culture.",
    },
    {
        "source_id": 28,
        "platform": "Glassdoor",
        "primary_theme": "LANG_NOT_SUPPORTED",
        "confidence": "NONE",
        "cleaned_text": "seguridad compañerismo comodidad rotativos adaptabilidad trabajo cansado fine semana posibilidad cobrar más",
        "executive_theme": "Workload & Burnout",
        "override_reason": "The translated signal emphasizes rotating schedules, tiring work, and weekend load, so workload pressure is the dominant executive reading.",
    },
    {
        "source_id": 36,
        "platform": "Glassdoor",
        "primary_theme": "Untagged",
        "confidence": "NONE",
        "cleaned_text": "close home glove strong enough",
        "executive_theme": "Workload & Burnout",
        "override_reason": "The mention of inadequate gloves points to physical working conditions rather than pay, management, or advancement.",
    },
    {
        "source_id": 38,
        "platform": "Glassdoor",
        "primary_theme": "Untagged",
        "confidence": "NONE",
        "cleaned_text": "name name",
        "executive_theme": "Work Culture",
        "override_reason": "This row is non-informative placeholder text. It is assigned to the lowest-signal residual theme to preserve one-theme comparability and is disclosed as an override.",
    },
    {
        "source_id": 43,
        "platform": "Glassdoor",
        "primary_theme": "LANG_NOT_SUPPORTED",
        "confidence": "NONE",
        "cleaned_text": "muy buenos beneficios exelente ambiente trabajo ambiente trabajo muy seguro posibilidad hacer carrera dentro empresa salario esta mal pero podría mejorar mucho más para trabajo que hace allí horarios rotativos permite crear hábitos saludables que constantemente estás cambiando rutina diaria trabajo fine semana trabajo muy repetitivo tener coche propio que hay manera trasladarse transporte público",
        "executive_theme": "Compensation & Benefits",
        "override_reason": "The text mentions several issues, but salary and benefits are the clearest executive complaint in a one-theme decision model.",
    },
    {
        "source_id": 61,
        "platform": "Glassdoor",
        "primary_theme": "LANG_NOT_SUPPORTED",
        "confidence": "NONE",
        "cleaned_text": "très bonne école salaires généreux avantageux demande investissement personnel important",
        "executive_theme": "Compensation & Benefits",
        "override_reason": "Salary and advantages are the clearest dominant theme in the translated content.",
    },
    {
        "source_id": 62,
        "platform": "Glassdoor",
        "primary_theme": "LANG_NOT_SUPPORTED",
        "confidence": "NONE",
        "cleaned_text": "angemessen bezahlt und gibt kein dresscode bi auf stahlkappenschuhe verbot die security nervt ich weiß jemand von denen hat einen sender von dem magnet tor man rein und raus geht da tor hat sogar dann gepiepst al ich metal hatte ehrliche security mitarbeiter anstellen",
        "executive_theme": "Work Culture",
        "override_reason": "The complaint is primarily about intrusive security behavior and daily treatment, which fits culture and dignity more than pay.",
    },
    {
        "source_id": 63,
        "platform": "Glassdoor",
        "primary_theme": "Untagged",
        "confidence": "NONE",
        "cleaned_text": "name name",
        "executive_theme": "Work Culture",
        "override_reason": "This row is non-informative placeholder text. It is assigned to the lowest-signal residual theme to preserve one-theme comparability and is disclosed as an override.",
    },
    {
        "source_id": 83,
        "platform": "Glassdoor",
        "primary_theme": "LANG_NOT_SUPPORTED",
        "confidence": "NONE",
        "cleaned_text": "gute leitungen gute mitarbeitern gute arbeit gibt keine kontras für der arbeit",
        "executive_theme": "Management & Communication",
        "override_reason": "The emphasis on leadership quality makes management the closest executive theme even though the statement is positive.",
    },
]

OVERRIDE_REVIEWER = "ARIA governance layer"
OVERRIDE_APPROVAL_DATE = "2026-03-30"


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().lower().split())


def text_fingerprint(value: object) -> str:
    return hashlib.sha256(normalize_text(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_override_table(raw_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for spec in OVERRIDE_SPECS:
        source_id = int(spec["source_id"])
        match = raw_df[raw_df["source_id"] == source_id]
        if len(match) != 1:
            raise ValueError(f"Expected exactly one row for override source_id={source_id}, found {len(match)}.")

        row = match.iloc[0]
        checks = {
            "platform": spec["platform"],
            "primary_theme": spec["primary_theme"],
            "confidence": spec["confidence"],
            "cleaned_text": spec["cleaned_text"],
        }
        for column, expected in checks.items():
            observed = normalize_text(row[column])
            if observed != normalize_text(expected):
                raise ValueError(
                    f"Override signature mismatch for source_id={source_id} on {column}: "
                    f"expected={expected!r}, observed={row[column]!r}"
                )

        rows.append(
            {
                "source_id": source_id,
                "platform": spec["platform"],
                "primary_theme": spec["primary_theme"],
                "confidence": spec["confidence"],
                "cleaned_text": spec["cleaned_text"],
                "text_fingerprint": text_fingerprint(spec["cleaned_text"]),
                "executive_theme": spec["executive_theme"],
                "executive_theme_method": "Executive override",
                "executive_theme_confidence": "OVERRIDE",
                "override_reason": spec["override_reason"],
                "reviewer": OVERRIDE_REVIEWER,
                "approval_date": OVERRIDE_APPROVAL_DATE,
            }
        )

    return pd.DataFrame(rows).sort_values("source_id").reset_index(drop=True)


def build_executive_dataset(raw_df: pd.DataFrame, override_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    df["text_fingerprint"] = df["cleaned_text"].apply(text_fingerprint)
    df["executive_theme"] = df["primary_theme"].map(PRIMARY_THEME_MAP)
    df["executive_theme_method"] = df["executive_theme"].apply(
        lambda value: "Direct pipeline map" if pd.notna(value) else ""
    )
    df["executive_theme_confidence"] = df["confidence"].where(df["executive_theme"].notna(), "")
    df["override_reason"] = ""

    override_lookup = override_df.set_index("source_id").to_dict(orient="index")
    override_mask = df["source_id"].isin(override_lookup.keys())
    for idx, row in df[override_mask].iterrows():
        override = override_lookup[int(row["source_id"])]
        checks = {
            "platform": override["platform"],
            "primary_theme": override["primary_theme"],
            "confidence": override["confidence"],
            "cleaned_text": override["cleaned_text"],
            "text_fingerprint": override["text_fingerprint"],
        }
        for column, expected in checks.items():
            if normalize_text(row[column]) != normalize_text(expected):
                raise ValueError(
                    f"Executive dataset override mismatch for source_id={int(row['source_id'])} on {column}."
                )

        df.at[idx, "executive_theme"] = override["executive_theme"]
        df.at[idx, "executive_theme_method"] = override["executive_theme_method"]
        df.at[idx, "executive_theme_confidence"] = override["executive_theme_confidence"]
        df.at[idx, "override_reason"] = override["override_reason"]

    unresolved = df[df["executive_theme"].isna()].copy()
    if not unresolved.empty:
        unresolved_ids = unresolved["source_id"].tolist()
        raise ValueError(f"Executive theme mapping unresolved for source_id values: {unresolved_ids}")

    return df


def main():
    raw_df = pd.read_csv(RAW_DATA_PATH)
    override_df = build_override_table(raw_df)
    executive_df = build_executive_dataset(raw_df, override_df)

    EXECUTIVE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    override_df.to_csv(OVERRIDE_TABLE_PATH, index=False, encoding="utf-8")
    executive_df.to_csv(EXECUTIVE_DATA_PATH, index=False, encoding="utf-8")

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "generator": "build_aria_governance_artifacts.py",
        "raw_dataset_name": RAW_DATA_PATH.name,
        "raw_dataset_path": RAW_DATA_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "raw_dataset_sha256": file_sha256(RAW_DATA_PATH),
        "executive_dataset_name": EXECUTIVE_DATA_PATH.name,
        "executive_dataset_path": EXECUTIVE_DATA_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "executive_dataset_sha256": file_sha256(EXECUTIVE_DATA_PATH),
        "override_table_name": OVERRIDE_TABLE_PATH.name,
        "override_table_path": OVERRIDE_TABLE_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "override_table_sha256": file_sha256(OVERRIDE_TABLE_PATH),
        "total_reviews": int(len(executive_df)),
        "platform_counts": {
            key: int(value) for key, value in executive_df["platform"].value_counts().to_dict().items()
        },
        "pipeline_theme_counts": {
            key: int(value) for key, value in executive_df["primary_theme"].value_counts().to_dict().items()
        },
        "executive_theme_counts": {
            key: int(value) for key, value in executive_df["executive_theme"].value_counts().to_dict().items()
        },
        "assignment_method_counts": {
            key: int(value)
            for key, value in executive_df["executive_theme_method"].value_counts().to_dict().items()
        },
        "none_confidence_reviews": int((executive_df["confidence"].fillna("").str.upper() == "NONE").sum()),
        "override_count": int(len(override_df)),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {EXECUTIVE_DATA_PATH}")
    print(f"Wrote {OVERRIDE_TABLE_PATH}")
    print(f"Wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
