from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
OUTPUTS = BASE / "outputs"
FINAL_REFERENCE = "Iteration 2"
OUT = OUTPUTS / "WT_1D_Query_Index_1989_2025.json.gz"
TOTAL_WORKBOOKS = {
    "Sprint": OUTPUTS / "WT_Sprint_All_AgeGroup_Reference_Curves_Total_Time_1989_2025.xlsx",
    "Standard": OUTPUTS / "WT_Standard_All_AgeGroup_Reference_Curves_Total_Time_1989_2025.xlsx",
}
SEGMENT_WORKBOOK = OUTPUTS / "WT_Segment_Reference_Curves_1989_2025.xlsx"


def _key(*parts: Any) -> str:
    return "|".join(str(part) for part in parts)


def _sex_label(sex: Any) -> str:
    return "O" if str(sex) == "M" else "F"


def _records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    return frame[columns].where(pd.notna(frame[columns]), None).to_dict("records")


def build_total_curves() -> dict[str, list[list[float]]]:
    curves: dict[str, list[list[float]]] = {}
    for modality, path in TOTAL_WORKBOOKS.items():
        data = pd.read_excel(path, sheet_name="Reference_Curves")
        data = data[data["reference"].eq(FINAL_REFERENCE)].copy()
        for (sex, age_group), group in data.groupby(["sex", "age_group"]):
            group = group.sort_values("total_seconds")
            curves[_key(modality, _sex_label(sex), age_group)] = [
                [float(row.total_seconds), float(row.performance_percentile)]
                for row in group.itertuples(index=False)
            ]
    return curves


def build_total_params() -> dict[str, list[dict[str, Any]]]:
    params: dict[str, list[dict[str, Any]]] = {}
    columns = ["modality", "sex", "sex_label", "age_group", "iteration", "year", "records", "alpha", "beta", "r2", "rmse_log", "mae_seconds_on_grid"]
    for modality, path in TOTAL_WORKBOOKS.items():
        data = pd.read_excel(path, sheet_name="Event_Transform_Params")
        data["sex_label"] = data["sex"].map(_sex_label)
        for (sex_label, age_group), group in data.groupby(["sex_label", "age_group"]):
            group = group.sort_values(["year", "iteration"])
            params[_key(modality, sex_label, age_group)] = _records(group, columns)
    return params


def build_total_meta() -> dict[str, dict[str, Any]]:
    meta: dict[str, dict[str, Any]] = {}
    for modality, path in TOTAL_WORKBOOKS.items():
        data = pd.read_excel(path, sheet_name="Group_Summary")
        data["sex_label"] = data["sex"].map(_sex_label)
        for row in data.itertuples(index=False):
            meta[_key(modality, row.sex_label, row.age_group)] = {
                "modality": modality,
                "sex": row.sex,
                "sex_label": row.sex_label,
                "age_group": row.age_group,
                "records": int(row.records),
                "events": int(row.events),
                "status": row.status,
            }
    return meta


def build_segment_curves() -> dict[str, list[list[float]]]:
    data = pd.read_excel(SEGMENT_WORKBOOK, sheet_name="Reference_Curves")
    data = data[data["reference"].eq(FINAL_REFERENCE)].copy()
    data["sex_label"] = data["sex"].map(_sex_label)
    curves: dict[str, list[list[float]]] = {}
    for (modality, sex_label, age_group, segment), group in data.groupby(["modality", "sex_label", "age_group", "segment"]):
        group = group.sort_values("seconds")
        curves[_key(modality, sex_label, age_group, segment)] = [
            [float(row.seconds), float(row.performance_percentile)]
            for row in group.itertuples(index=False)
        ]
    return curves


def build_segment_params() -> dict[str, list[dict[str, Any]]]:
    data = pd.read_excel(SEGMENT_WORKBOOK, sheet_name="Event_Transform_Params")
    data["sex_label"] = data["sex"].map(_sex_label)
    columns = [
        "modality",
        "sex",
        "sex_label",
        "age_group",
        "segment",
        "iteration",
        "year",
        "event_records",
        "alpha",
        "beta",
        "r2",
        "correlation_r",
        "rmse_log",
        "mae_seconds_on_grid",
    ]
    params: dict[str, list[dict[str, Any]]] = {}
    for (modality, sex_label, age_group, segment), group in data.groupby(["modality", "sex_label", "age_group", "segment"]):
        group = group.sort_values(["year", "iteration"])
        params[_key(modality, sex_label, age_group, segment)] = _records(group, columns)
    return params


def build_segment_meta() -> dict[str, dict[str, Any]]:
    data = pd.read_excel(SEGMENT_WORKBOOK, sheet_name="Group_Segment_Summary")
    data["sex_label"] = data["sex"].map(_sex_label)
    meta: dict[str, dict[str, Any]] = {}
    for row in data.itertuples(index=False):
        meta[_key(row.modality, row.sex_label, row.age_group, row.segment)] = {
            "modality": row.modality,
            "sex": row.sex,
            "sex_label": row.sex_label,
            "age_group": row.age_group,
            "segment": row.segment,
            "records": int(row.records),
            "events": int(row.events),
            "status": row.status,
            "curve_points": int(row.curve_points) if pd.notna(row.curve_points) else None,
        }
    return meta


def main() -> None:
    index = {
        "schema_version": 2,
        "final_reference": FINAL_REFERENCE,
        "segment_source": SEGMENT_WORKBOOK.name,
        "total_sources": {key: path.name for key, path in TOTAL_WORKBOOKS.items()},
        "total_curves": build_total_curves(),
        "total_meta": build_total_meta(),
        "total_params": build_total_params(),
        "segment_curves": build_segment_curves(),
        "segment_meta": build_segment_meta(),
        "segment_params": build_segment_params(),
    }
    with gzip.open(OUT, "wt", encoding="utf-8") as handle:
        json.dump(index, handle, separators=(",", ":"))
    print(f"Wrote {OUT}")
    print(f"total_curves={len(index['total_curves'])}")
    print(f"segment_curves={len(index['segment_curves'])}")


if __name__ == "__main__":
    main()
