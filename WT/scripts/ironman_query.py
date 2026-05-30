from __future__ import annotations

import bisect
import gzip
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any


INDEX_PATH = Path(__file__).resolve().parents[2] / "Ironman" / "outputs" / "Ironman_Query_Index.json.gz"
EVENT_INDEX_PATH = Path(__file__).resolve().parents[2] / "Ironman" / "outputs" / "Ironman_Event_Curves_Index.json.gz"


def _key(*parts: Any) -> str:
    return "|".join(str(part) for part in parts)


@lru_cache(maxsize=1)
def load_index() -> dict:
    with gzip.open(INDEX_PATH, "rt", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_event_index() -> dict:
    with gzip.open(EVENT_INDEX_PATH, "rt", encoding="utf-8") as handle:
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


def cube_query(modality: str, sex: str, age_group: str, swim_percentile: float, bike_percentile: float, run_percentile: float) -> dict:
    rows = load_index()["cubes"][_key(modality, sex, age_group)]
    return {
        "swim_percentile": float(swim_percentile), "bike_percentile": float(bike_percentile), "run_percentile": float(run_percentile),
        "joint_sbr_percentile": _trilinear(rows, swim_percentile, bike_percentile, run_percentile),
    }


def pair_times_query(modality: str, sex: str, age_group: str, pair: str, x_time: Any, y_time: Any) -> dict:
    x_segment, y_segment = {
        "swim_bike": ("Swim", "Bike"),
        "swim_run": ("Swim", "Run"),
        "bike_run": ("Bike", "Run"),
    }[pair]
    x_curve = curve_query(modality, sex, age_group, x_segment, x_time)
    y_curve = curve_query(modality, sex, age_group, y_segment, y_time)
    result = pair_query(
        modality,
        sex,
        age_group,
        pair,
        x_curve["performance_percentile"],
        y_curve["performance_percentile"],
    )
    result.update({"input_x_time": x_curve["time"], "input_y_time": y_curve["time"]})
    return result


def cube_times_query(modality: str, sex: str, age_group: str, swim_time: Any, bike_time: Any, run_time: Any) -> dict:
    curves = {
        "Swim": curve_query(modality, sex, age_group, "Swim", swim_time),
        "Bike": curve_query(modality, sex, age_group, "Bike", bike_time),
        "Run": curve_query(modality, sex, age_group, "Run", run_time),
    }
    result = cube_query(
        modality,
        sex,
        age_group,
        curves["Swim"]["performance_percentile"],
        curves["Bike"]["performance_percentile"],
        curves["Run"]["performance_percentile"],
    )
    result.update({
        "input_swim_time": curves["Swim"]["time"],
        "input_bike_time": curves["Bike"]["time"],
        "input_run_time": curves["Run"]["time"],
    })
    return result


def evaluate_profile(
    modality: str,
    sex: str,
    age_group: str,
    swim_time: Any,
    bike_time: Any,
    run_time: Any,
    *,
    t1_time: Any | None = None,
    t2_time: Any | None = None,
) -> dict:
    inputs = {"Swim": swim_time, "Bike": bike_time, "Run": run_time}
    if t1_time:
        inputs["T1"] = t1_time
    if t2_time:
        inputs["T2"] = t2_time
    segments = [curve_query(modality, sex, age_group, segment, value) for segment, value in inputs.items()]
    for row in segments:
        row["input_time"] = row["time"]

    transition_times = {}
    for transition in ("T1", "T2"):
        if transition in inputs:
            transition_times[transition] = parse_time(inputs[transition])
        else:
            transition_times[transition] = curve_query(modality, sex, age_group, transition, 50, by_percentile=True)["seconds"]

    estimated_total_seconds = sum(parse_time(inputs[segment]) for segment in ("Swim", "Bike", "Run")) + sum(transition_times.values())
    estimated_total = curve_query(modality, sex, age_group, "Total", estimated_total_seconds)
    cube = cube_times_query(modality, sex, age_group, swim_time, bike_time, run_time)
    return {
        "segments": segments,
        "estimated_total": estimated_total,
        "estimated_total_time": format_seconds(estimated_total_seconds),
        "cube": cube,
        "used_median_transitions": not (t1_time and t2_time),
    }


def gap_query(modality: str, sex: str, age_group: str, segment: str, current_time: Any, target_percentile: float) -> dict:
    current = curve_query(modality, sex, age_group, segment, current_time)
    target = curve_query(modality, sex, age_group, segment, target_percentile, by_percentile=True)
    return {
        "segment": segment,
        "current_time": current["time"],
        "current_percentile": current["performance_percentile"],
        "target_percentile": float(target_percentile),
        "target_time": target["time"],
        "improvement_seconds": max(0.0, current["seconds"] - target["seconds"]),
        "improvement_time": format_seconds(max(0.0, current["seconds"] - target["seconds"])),
    }


def required_segment_query(
    modality: str,
    sex: str,
    age_group: str,
    missing_segment: str,
    target_percentile: float,
    known_times: dict[str, Any],
) -> dict:
    target = curve_query(modality, sex, age_group, "Total", target_percentile, by_percentile=True)
    transitions = sum(curve_query(modality, sex, age_group, segment, 50, by_percentile=True)["seconds"] for segment in ("T1", "T2"))
    known_seconds = sum(parse_time(value) for value in known_times.values())
    required_seconds = max(0.0, target["seconds"] - transitions - known_seconds)
    return {
        "missing_segment": missing_segment,
        "target_total_percentile": float(target_percentile),
        "target_total_time": target["time"],
        "required_time": format_seconds(required_seconds),
        "required_segment_percentile": curve_query(modality, sex, age_group, missing_segment, required_seconds)["performance_percentile"],
        "uses_median_transitions": True,
    }


def list_event_options(modality: str, sex: str, age_group: str, segment: str = "Total", *, min_n: int = 20) -> list[dict]:
    index = load_event_index()
    rows = []
    for event in index["events"].values():
        if event["modality"] != modality or event["sex_label"] != sex or event["age_group"] != age_group:
            continue
        curve = index["curves"].get(_key(modality, sex, age_group, event["year"], segment))
        if not curve or len(curve) < min_n:
            continue
        event_name = " | ".join(event.get("event_names", [])) or str(event["year"])
        rows.append({**event, "event_name": event_name, "n": len(curve)})
    return sorted(rows, key=lambda row: row["year"])


def event_time_query(modality: str, sex: str, age_group: str, segment: str, value: Any, years: list[int], *, min_n: int = 20) -> dict:
    seconds = parse_time(value)
    comparisons = []
    index = load_event_index()
    for event in list_event_options(modality, sex, age_group, segment, min_n=min_n):
        if years and event["year"] not in years:
            continue
        curve = index["curves"][_key(modality, sex, age_group, event["year"], segment)]
        if seconds < curve[0] or seconds > curve[-1]:
            comparisons.append({
                "year": event["year"], "event_name": event["event_name"], "n": len(curve),
                "input_time": format_seconds(seconds), "valid": False,
                "status": "outside_empirical_range",
                "empirical_min_time": format_seconds(curve[0]), "empirical_max_time": format_seconds(curve[-1]),
            })
            continue
        position = bisect.bisect_left(curve, seconds) + 1
        percentile = 100.0 * (1.0 - (position - 0.5) / len(curve))
        comparisons.append({
            "year": event["year"], "event_name": event["event_name"], "n": len(curve),
            "input_time": format_seconds(seconds), "estimated_position": position,
            "performance_percentile": percentile, "valid": True,
            "empirical_min_time": format_seconds(curve[0]), "empirical_max_time": format_seconds(curve[-1]),
        })
    return {"query_type": "time_to_position", "segment": segment, "input_time": format_seconds(seconds), "comparisons": comparisons}


def event_percentile_query(modality: str, sex: str, age_group: str, segment: str, percentile: float, years: list[int], *, min_n: int = 20) -> dict:
    comparisons = []
    index = load_event_index()
    for event in list_event_options(modality, sex, age_group, segment, min_n=min_n):
        if years and event["year"] not in years:
            continue
        curve = index["curves"][_key(modality, sex, age_group, event["year"], segment)]
        p_min = 100.0 * (0.5 / len(curve))
        p_max = 100.0 * (1.0 - 0.5 / len(curve))
        if percentile < p_min or percentile > p_max:
            comparisons.append({
                "year": event["year"], "event_name": event["event_name"], "n": len(curve),
                "percentile": float(percentile), "valid": False,
                "status": "outside_empirical_support", "p_min": p_min, "p_max": p_max,
            })
            continue
        position = max(0.0, min(len(curve) - 1.0, (1.0 - percentile / 100.0) * len(curve) - 0.5))
        lower, upper = math.floor(position), math.ceil(position)
        seconds = curve[lower] if lower == upper else curve[lower] + (curve[upper] - curve[lower]) * (position - lower)
        comparisons.append({
            "year": event["year"], "event_name": event["event_name"], "n": len(curve),
            "percentile": float(percentile), "estimated_position": position + 1,
            "estimated_time": format_seconds(seconds), "valid": True,
        })
    return {"query_type": "percentile_to_time", "segment": segment, "percentile": float(percentile), "comparisons": comparisons}
