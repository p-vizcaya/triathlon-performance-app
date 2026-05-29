from __future__ import annotations

import bisect
import gzip
import json
import math
from functools import lru_cache
from typing import Any

from .normalization import (
    NormalizationError,
    format_seconds,
    normalize_age_group,
    normalize_modality,
    normalize_segment,
    normalize_sex_category,
    parse_segment_time_to_seconds,
    parse_time_to_seconds,
)
from .sources import OUTPUTS_DIR


EVENT_CURVES_INDEX_PATH = OUTPUTS_DIR / "WT_Event_Curves_Index_1989_2025.json.gz"
MIN_USABLE_N = 20
LOW_CONFIDENCE_N = 30
HIGH_CONFIDENCE_N = 50


def _key(*parts: Any) -> str:
    return "|".join(str(part) for part in parts)


@lru_cache(maxsize=1)
def load_event_curves_index() -> dict[str, Any] | None:
    if not EVENT_CURVES_INDEX_PATH.exists():
        return None
    with gzip.open(EVENT_CURVES_INDEX_PATH, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_years(event_years: Any) -> list[int] | None:
    if event_years in (None, "", "All", "all"):
        return None
    if isinstance(event_years, str):
        parts = [part.strip() for part in event_years.replace(";", ",").split(",")]
    elif isinstance(event_years, (list, tuple, set)):
        parts = list(event_years)
    else:
        parts = [event_years]
    years = sorted({int(part) for part in parts if str(part).strip()})
    return years or None


def _context(modality: Any, sex_category: Any, age_group: Any, segment: Any) -> tuple[str, str, str, str]:
    return (
        normalize_modality(modality),
        normalize_sex_category(sex_category, field="sex_label"),
        normalize_age_group(age_group),
        normalize_segment(segment),
    )


def list_event_options(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    segment: Any = "Total",
    *,
    min_n: int = 1,
) -> list[dict[str, Any]]:
    index = load_event_curves_index()
    if index is None:
        return []
    modality, sex_label, age_group, segment = _context(modality, sex_category, age_group, segment)
    rows = []
    for event_key, event in index.get("events", {}).items():
        if (
            event.get("modality") != modality
            or event.get("sex_label") != sex_label
            or event.get("age_group") != age_group
        ):
            continue
        curve = index.get("curves", {}).get(_key(modality, sex_label, age_group, event["year"], segment))
        if not curve or len(curve) < min_n:
            continue
        rows.append(
            {
                "event_key": event_key,
                "year": int(event["year"]),
                "event_name": event.get("event_name") or str(event["year"]),
                "n": len(curve),
                "confidence": _confidence_label(len(curve)),
            }
        )
    return sorted(rows, key=lambda row: row["year"])


def compare_time_to_event_curves(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    segment: Any,
    time_value: Any,
    event_years: Any = None,
    *,
    min_n: int = MIN_USABLE_N,
) -> dict[str, Any]:
    modality, sex_label, age_group, segment = _context(modality, sex_category, age_group, segment)
    seconds = parse_time_to_seconds(time_value) if segment == "Total" else parse_segment_time_to_seconds(time_value, segment, modality)
    rows = _matching_event_rows(modality, sex_label, age_group, segment, event_years, min_n=min_n)
    comparisons = [_time_result(row, seconds) for row in rows]
    return _comparison_result(
        modality=modality,
        sex_label=sex_label,
        age_group=age_group,
        segment=segment,
        query_type="time_to_position",
        input_seconds=seconds,
        input_time=format_seconds(seconds),
        min_n=min_n,
        comparisons=comparisons,
    )


def compare_percentile_to_event_curves(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    segment: Any,
    percentile: Any,
    event_years: Any = None,
    *,
    min_n: int = MIN_USABLE_N,
) -> dict[str, Any]:
    modality, sex_label, age_group, segment = _context(modality, sex_category, age_group, segment)
    percentile_value = float(percentile)
    if not 0 <= percentile_value <= 100:
        raise NormalizationError("Percentile must be between 0 and 100")
    rows = _matching_event_rows(modality, sex_label, age_group, segment, event_years, min_n=min_n)
    comparisons = [_percentile_result(row, percentile_value) for row in rows]
    return _comparison_result(
        modality=modality,
        sex_label=sex_label,
        age_group=age_group,
        segment=segment,
        query_type="percentile_to_time",
        percentile=percentile_value,
        min_n=min_n,
        comparisons=comparisons,
    )


def _matching_event_rows(
    modality: str,
    sex_label: str,
    age_group: str,
    segment: str,
    event_years: Any,
    *,
    min_n: int,
) -> list[dict[str, Any]]:
    index = load_event_curves_index()
    if index is None:
        raise NormalizationError("Event curves index is not available")
    selected_years = _normalize_years(event_years)
    rows = []
    for option in list_event_options(modality, sex_label, age_group, segment, min_n=min_n):
        if selected_years is not None and option["year"] not in selected_years:
            continue
        curve = index["curves"][_key(modality, sex_label, age_group, option["year"], segment)]
        rows.append({**option, "curve": [int(value) for value in curve]})
    return rows


def _time_result(row: dict[str, Any], seconds: float) -> dict[str, Any]:
    curve = row["curve"]
    n = len(curve)
    faster_count = bisect.bisect_left(curve, seconds)
    tie_left = bisect.bisect_left(curve, int(round(seconds)))
    tie_right = bisect.bisect_right(curve, int(round(seconds)))
    tie_count = max(0, tie_right - tie_left)
    slower_count = max(0, n - bisect.bisect_right(curve, seconds))
    insertion = bisect.bisect_left(curve, seconds)
    percentile = max(0.0, min(100.0, 100.0 * (1.0 - (insertion + 0.5) / n)))
    range_status = "faster_than_field" if insertion == 0 and seconds < curve[0] else "slower_than_field" if insertion == n else None
    return {
        "year": row["year"],
        "event_name": row["event_name"],
        "n": n,
        "input_time": format_seconds(seconds),
        "input_seconds": seconds,
        "estimated_position": insertion + 1,
        "faster_count": faster_count,
        "tie_count": tie_count,
        "slower_count": slower_count,
        "performance_percentile": percentile,
        "range_status": range_status,
        "confidence": _confidence_label(n),
    }


def _percentile_result(row: dict[str, Any], percentile: float) -> dict[str, Any]:
    curve = row["curve"]
    n = len(curve)
    p_min = 100.0 * (0.5 / n)
    p_max = 100.0 * (1.0 - 0.5 / n)
    raw_position = (1.0 - percentile / 100.0) * n - 0.5
    range_status = "above_empirical_support" if percentile > p_max else "below_empirical_support" if percentile < p_min else None
    position = max(0.0, min(float(n - 1), raw_position))
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        seconds = float(curve[lower])
    else:
        ratio = position - lower
        seconds = float(curve[lower] + (curve[upper] - curve[lower]) * ratio)
    return {
        "year": row["year"],
        "event_name": row["event_name"],
        "n": n,
        "percentile": percentile,
        "estimated_position": position + 1.0,
        "estimated_time": format_seconds(seconds),
        "estimated_seconds": seconds,
        "p_min": p_min,
        "p_max": p_max,
        "range_status": range_status,
        "confidence": _confidence_label(n),
    }


def _comparison_result(
    *,
    modality: str,
    sex_label: str,
    age_group: str,
    segment: str,
    query_type: str,
    min_n: int,
    comparisons: list[dict[str, Any]],
    input_seconds: float | None = None,
    input_time: str | None = None,
    percentile: float | None = None,
) -> dict[str, Any]:
    valid = bool(comparisons)
    result = {
        "valid": valid,
        "entity": "event_curve_comparison",
        "modality": modality,
        "sex_label": sex_label,
        "age_group": age_group,
        "segment": segment,
        "query_type": query_type,
        "min_n": min_n,
        "comparisons": comparisons,
    }
    if input_seconds is not None:
        result["input_seconds"] = input_seconds
    if input_time is not None:
        result["input_time"] = input_time
    if percentile is not None:
        result["percentile"] = percentile
    if not valid:
        result["reason"] = "no_matching_event_curves"
        result["message"] = "No matching championship event curves are available for this context and minimum n."
    return result


def _confidence_label(n: int) -> str:
    if n >= HIGH_CONFIDENCE_N:
        return "high"
    if n >= LOW_CONFIDENCE_N:
        return "valid"
    if n >= MIN_USABLE_N:
        return "usable_with_caution"
    if n >= 10:
        return "exploratory"
    return "insufficient"
