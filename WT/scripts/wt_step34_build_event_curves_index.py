from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
INPUT_FILE = BASE / "outputs" / "WT_Triathlon_Sprint_Standard_Canonical_1989_2025.xlsx"
OUTPUT_FILE = BASE / "outputs" / "WT_Event_Curves_Index_1989_2025.json.gz"

SEGMENT_COLUMNS = {
    "Total": "total_seconds",
    "Swim": "swim_seconds",
    "T1": "t1_seconds",
    "Bike": "bike_seconds",
    "T2": "t2_seconds",
    "Run": "run_seconds",
}


def _key(*parts: Any) -> str:
    return "|".join(str(part) for part in parts)


def _event_name(source_files: pd.Series) -> str:
    names = sorted({str(value).strip() for value in source_files.dropna() if str(value).strip()})
    if not names:
        return ""
    name = names[0]
    return re.sub(r"\.xlsx$", "", name, flags=re.IGNORECASE).strip()


def _sex_label(value: Any) -> str:
    return "F" if str(value).strip().upper() == "F" else "O"


def build_index() -> dict[str, Any]:
    columns = ["modality", "sex", "age_group", "year", "source_file", *SEGMENT_COLUMNS.values()]
    df = pd.read_excel(INPUT_FILE, sheet_name="Canonical_Results", usecols=columns)
    df = df[pd.to_numeric(df["total_seconds"], errors="coerce").gt(0)].copy()

    curves: dict[str, list[int]] = {}
    events: dict[str, dict[str, Any]] = {}

    group_cols = ["modality", "sex", "age_group", "year"]
    for group_key, group in df.groupby(group_cols, dropna=False):
        modality, sex, age_group, year = group_key
        sex = _sex_label(sex)
        event_key = _key(modality, sex, age_group, int(year))
        event_name = _event_name(group["source_file"])
        events[event_key] = {
            "modality": str(modality),
            "sex_label": sex,
            "age_group": str(age_group),
            "year": int(year),
            "event_name": event_name,
            "source_files": sorted(group["source_file"].dropna().astype(str).unique().tolist()),
        }

        for segment, column in SEGMENT_COLUMNS.items():
            values = pd.to_numeric(group[column], errors="coerce").dropna()
            values = values[values.gt(0)]
            if values.empty:
                continue
            seconds = sorted(int(round(value)) for value in values.tolist())
            curve_key = _key(modality, sex, age_group, int(year), segment)
            curves[curve_key] = seconds
            events[event_key][f"n_{segment.lower()}"] = len(seconds)

    return {
        "version": 1,
        "description": "Empirical event-category segment curves. Times are sorted ascending in integer seconds.",
        "segments": list(SEGMENT_COLUMNS),
        "key_format": "modality|sex_label|age_group|year|segment",
        "event_key_format": "modality|sex_label|age_group|year",
        "curves": curves,
        "events": events,
    }


def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    index = build_index()
    with gzip.open(OUTPUT_FILE, "wt", encoding="utf-8") as handle:
        json.dump(index, handle, ensure_ascii=True, separators=(",", ":"))
    print(f"written={OUTPUT_FILE}")
    print(f"events={len(index['events'])}")
    print(f"curves={len(index['curves'])}")


if __name__ == "__main__":
    main()
