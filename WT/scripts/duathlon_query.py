from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


INDEX_PATH = Path(__file__).resolve().parents[1] / "outputs" / "WT_Duathlon_Query_Index_1994_2025.json.gz"


def _key(*parts: Any) -> str:
    return "|".join(str(part) for part in parts)


@lru_cache(maxsize=1)
def load_index() -> dict:
    with gzip.open(INDEX_PATH, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def format_seconds(value: float) -> str:
    total = int(round(value))
    return f"{total // 3600}:{(total % 3600) // 60:02d}:{total % 60:02d}" if total >= 3600 else f"{total // 60}:{total % 60:02d}"


def parse_time(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    parts = [float(part) for part in str(value).strip().split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def _interpolate(points: list[list[float]], value: float, *, reverse: bool = False) -> float:
    ordered = sorted(([row[1], row[0]] if reverse else row for row in points), key=lambda row: row[0])
    if value <= ordered[0][0]:
        return float(ordered[0][1])
    if value >= ordered[-1][0]:
        return float(ordered[-1][1])
    for left, right in zip(ordered, ordered[1:]):
        if left[0] <= value <= right[0]:
            ratio = 0 if right[0] == left[0] else (value - left[0]) / (right[0] - left[0])
            return float(left[1] + ratio * (right[1] - left[1]))
    return float(ordered[-1][1])


def _bracket(values, target: float) -> tuple[float, float]:
    ordered = sorted({float(value) for value in values})
    if target <= ordered[0]:
        return ordered[0], ordered[0]
    if target >= ordered[-1]:
        return ordered[-1], ordered[-1]
    for lower, upper in zip(ordered, ordered[1:]):
        if lower <= target <= upper:
            return lower, upper
    return ordered[-1], ordered[-1]


def _lerp(lower_value: float, upper_value: float, lower_axis: float, upper_axis: float, target: float) -> float:
    if lower_axis == upper_axis:
        return float(lower_value)
    weight = (target - lower_axis) / (upper_axis - lower_axis)
    return float(lower_value + weight * (upper_value - lower_value))


def _bilinear(rows, x_target: float, y_target: float) -> float:
    values = {(float(row[2]), float(row[3])): float(row[6]) for row in rows}
    x0, x1 = _bracket((key[0] for key in values), x_target)
    y0, y1 = _bracket((key[1] for key in values), y_target)
    lower = _lerp(values[(x0, y0)], values[(x1, y0)], x0, x1, x_target)
    upper = _lerp(values[(x0, y1)], values[(x1, y1)], x0, x1, x_target)
    return _lerp(lower, upper, y0, y1, y_target)


def _axis_time(rows, percentile_index: int, seconds_index: int, target: float) -> float:
    points = sorted({(float(row[percentile_index]), float(row[seconds_index])) for row in rows})
    return _interpolate([[percentile, seconds] for percentile, seconds in points], target)


def _trilinear(rows, x_target: float, y_target: float, z_target: float) -> float:
    values = {(float(row[0]), float(row[1]), float(row[2])): float(row[3]) for row in rows}
    x0, x1 = _bracket((key[0] for key in values), x_target)
    y0, y1 = _bracket((key[1] for key in values), y_target)
    z0, z1 = _bracket((key[2] for key in values), z_target)

    def interpolate_z(z_value: float) -> float:
        lower = _lerp(values[(x0, y0, z_value)], values[(x1, y0, z_value)], x0, x1, x_target)
        upper = _lerp(values[(x0, y1, z_value)], values[(x1, y1, z_value)], x0, x1, x_target)
        return _lerp(lower, upper, y0, y1, y_target)

    return _lerp(interpolate_z(z0), interpolate_z(z1), z0, z1, z_target)


def curve_query(modality: str, sex: str, age_group: str, segment: str, value: Any, *, by_percentile: bool = False) -> dict:
    index = load_index()
    collection = index["total_curves"] if segment == "Total" else index["segment_curves"]
    curve_key = _key(modality, sex, age_group) if segment == "Total" else _key(modality, sex, age_group, segment)
    points = collection[curve_key]
    if by_percentile:
        seconds = _interpolate(points, float(value), reverse=True)
        return {"segment": segment, "percentile": float(value), "seconds": seconds, "time": format_seconds(seconds)}
    seconds = parse_time(value)
    return {"segment": segment, "seconds": seconds, "time": format_seconds(seconds), "performance_percentile": _interpolate(points, seconds)}


def pair_query(modality: str, sex: str, age_group: str, pair: str, x_percentile: float, y_percentile: float) -> dict:
    rows = load_index()["pair_planes"][_key(modality, sex, age_group, pair)]
    nearest = min(rows, key=lambda row: abs(float(row[2]) - x_percentile) + abs(float(row[3]) - y_percentile))
    return {
        "pair": pair, "x_segment": nearest[0], "y_segment": nearest[1],
        "x_percentile": float(x_percentile), "y_percentile": float(y_percentile),
        "x_time": format_seconds(_axis_time(rows, 2, 4, x_percentile)),
        "y_time": format_seconds(_axis_time(rows, 3, 5, y_percentile)),
        "joint_pair_percentile": _bilinear(rows, x_percentile, y_percentile),
    }


def cube_query(modality: str, sex: str, age_group: str, run1_percentile: float, bike_percentile: float, run2_percentile: float) -> dict:
    rows = load_index()["cubes"][_key(modality, sex, age_group)]
    return {
        "run1_percentile": float(run1_percentile), "bike_percentile": float(bike_percentile), "run2_percentile": float(run2_percentile),
        "joint_rbr_percentile": _trilinear(rows, run1_percentile, bike_percentile, run2_percentile),
    }
