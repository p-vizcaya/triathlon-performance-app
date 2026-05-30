from __future__ import annotations

import argparse
import re
from datetime import time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DEFAULT_CANONICAL = BASE / "data" / "canonical" / "WT_Triathlon_Sprint_Standard_Canonical_1989_2025.xlsx"
DEFAULT_OUTPUT_COPY = BASE / "outputs" / "WT_Triathlon_Sprint_Standard_Canonical_1989_2025.xlsx"


def time_to_seconds(value: Any) -> float:
    if value is None or pd.isna(value):
        return np.nan
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, time):
        return value.hour * 3600 + value.minute * 60 + value.second
    if isinstance(value, (int, float, np.integer, np.floating)):
        if not np.isfinite(value):
            return np.nan
        return float(value) * 86400 if 0 < float(value) < 10 else float(value)
    text = str(value).strip()
    if not text:
        return np.nan
    parts = text.split(":")
    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        return np.nan
    if len(numbers) == 3:
        return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
    if len(numbers) == 2:
        return numbers[0] * 60 + numbers[1]
    return np.nan


def seconds_to_hms(value: float) -> str:
    total = int(round(value))
    return f"{total // 3600}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def sex_from_sheet(source_sheet: str) -> str:
    return "F" if "Female" in source_sheet else "M"


def age_group_from_sheet(source_sheet: str) -> str:
    match = re.search(r"(\d{2}-\d{2}|\d{2}\+)", source_sheet)
    if not match:
        raise ValueError(f"Could not parse age group from {source_sheet!r}")
    return match.group(1)


def canonicalize_sprint_2025(source: Path) -> pd.DataFrame:
    frame = pd.read_excel(source, sheet_name="Consolidado")
    frame = frame[frame["Status"].fillna("").astype(str).str.strip().eq("")].copy()
    fields = {
        "swim": "Swim",
        "t1": "T1",
        "bike": "Bike",
        "t2": "T2",
        "run": "Run",
        "total": "Total Time",
    }
    for key, column in fields.items():
        frame[f"{key}_seconds"] = frame[column].map(time_to_seconds)
    frame = frame[
        frame["total_seconds"].gt(0)
        & frame[["swim_seconds", "t1_seconds", "bike_seconds", "t2_seconds", "run_seconds"]].ge(0).all(axis=1)
    ].copy()
    segment_sum = frame[["swim_seconds", "t1_seconds", "bike_seconds", "t2_seconds", "run_seconds"]].sum(axis=1)
    source_sheet = frame["SourceSheet"].astype(str)
    result = pd.DataFrame(
        {
            "year": 2025,
            "venue": "World Triathlon Age-Group Championships Wollongong Sprint",
            "modality": "Sprint",
            "sex": source_sheet.map(sex_from_sheet),
            "age_group": source_sheet.map(age_group_from_sheet),
            "program_id": frame["Program ID"],
            "program": source_sheet,
            "athlete_id": frame["Athlete ID"],
            "first_name": frame["Athlete First Name"],
            "last_name": frame["Athlete Last Name"],
            "country": frame["Country"],
            "start_number": frame["Start Number"],
            "position": frame["Position"],
            "swim_seconds": frame["swim_seconds"],
            "t1_seconds": frame["t1_seconds"],
            "bike_seconds": frame["bike_seconds"],
            "t2_seconds": frame["t2_seconds"],
            "run_seconds": frame["run_seconds"],
            "total_seconds": frame["total_seconds"],
            "swim_time": frame["swim_seconds"].map(seconds_to_hms),
            "t1_time": frame["t1_seconds"].map(seconds_to_hms),
            "bike_time": frame["bike_seconds"].map(seconds_to_hms),
            "t2_time": frame["t2_seconds"].map(seconds_to_hms),
            "run_time": frame["run_seconds"].map(seconds_to_hms),
            "total_time": frame["total_seconds"].map(seconds_to_hms),
            "segment_sum_seconds": segment_sum,
            "total_minus_segments_seconds": frame["total_seconds"] - segment_sum,
            "split_times_reported": True,
            "transition_times_reported": frame["t1_seconds"].gt(0) & frame["t2_seconds"].gt(0),
            "total_only_record": False,
            "status": "",
            "source_file": frame["SourceFile"],
            "source_sheet": frame["SourceSheet"],
            "source_row": frame.index + 2,
        }
    )
    return result


def summary_year_modality_sex(canonical: pd.DataFrame) -> pd.DataFrame:
    return (
        canonical.groupby(["year", "modality", "sex"], dropna=False)
        .size()
        .reset_index(name="records")
        .sort_values(["year", "modality", "sex"])
    )


def summary_modality_sex_ag(canonical: pd.DataFrame) -> pd.DataFrame:
    return (
        canonical.groupby(["modality", "sex", "age_group"], dropna=False)
        .size()
        .reset_index(name="records")
        .sort_values(["modality", "sex", "age_group"])
    )


def summary_source(canonical: pd.DataFrame) -> pd.DataFrame:
    return (
        canonical.groupby(["source_file", "year", "modality", "sex"], dropna=False)
        .size()
        .reset_index(name="accepted_records")
        .sort_values(["year", "source_file", "modality", "sex"])
    )


def write_updated_master(original: Path, output: Path, sprint_2025: pd.DataFrame) -> None:
    sheets = pd.read_excel(original, sheet_name=None)
    canonical = sheets["Canonical_Results"]
    canonical = canonical[~((canonical["year"] == 2025) & (canonical["modality"] == "Sprint"))].copy()
    canonical = pd.concat([canonical, sprint_2025], ignore_index=True)
    duplicate_key = ["year", "program_id", "athlete_id", "modality", "sex", "age_group"]
    duplicates = canonical[canonical.duplicated(duplicate_key, keep=False)].copy()
    if not duplicates.empty:
        raise ValueError(f"Integration would create {len(duplicates)} duplicate canonical rows")
    canonical = canonical.sort_values(["modality", "sex", "age_group", "year", "total_seconds"])
    sheets["Canonical_Results"] = canonical
    sheets["Summary_Year_Modality_Sex"] = summary_year_modality_sex(canonical)
    sheets["Summary_Modality_Sex_AG"] = summary_modality_sex_ag(canonical)
    sheets["Summary_Source"] = summary_source(canonical)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, index=False, sheet_name=name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL)
    parser.add_argument("--output-copy", type=Path, default=DEFAULT_OUTPUT_COPY)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sprint_2025 = canonicalize_sprint_2025(args.source)
    print(f"valid_sprint_2025={len(sprint_2025)}")
    print(sprint_2025.groupby(["sex", "age_group"]).size().to_string())
    write_updated_master(args.canonical, args.canonical, sprint_2025)
    if args.output_copy.resolve() != args.canonical.resolve():
        write_updated_master(args.canonical, args.output_copy, sprint_2025)
    print(f"updated={args.canonical}")
    if args.output_copy.resolve() != args.canonical.resolve():
        print(f"updated={args.output_copy}")


if __name__ == "__main__":
    main()
