from __future__ import annotations

from typing import Any

from .coverage import validate_query_inputs
from .lookups_1d import get_total_percentile_by_time
from .normalization import (
    format_seconds,
    normalize_age_group,
    normalize_modality,
    normalize_sex_category,
    parse_segment_time_to_seconds,
    parse_time_to_seconds,
)
from .lookups_1d import _segment_curve_rows


def _average_segment_seconds(modality: str, sex_label: str, age_group: str, segment: str) -> float:
    points = _segment_curve_rows(modality, sex_label, age_group, segment)
    if not points:
        raise ValueError(f"No {segment} points available for {modality} {sex_label} {age_group}")
    return sum(seconds for seconds, _ in points) / len(points)


def estimate_total_from_main_segments(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    swim_time: Any,
    bike_time: Any,
    run_time: Any,
) -> dict[str, Any]:
    modality = normalize_modality(modality)
    sex_label = normalize_sex_category(sex_category, field="sex_label")
    age_group = normalize_age_group(age_group)

    coverage = validate_query_inputs("segment_curve", modality, sex_label, age_group, segment="T1")
    if not coverage.valid:
        return coverage.to_dict()

    swim_seconds = parse_segment_time_to_seconds(modality, "Swim", swim_time)
    bike_seconds = parse_segment_time_to_seconds(modality, "Bike", bike_time)
    run_seconds = parse_segment_time_to_seconds(modality, "Run", run_time)
    avg_t1_seconds = _average_segment_seconds(modality, sex_label, age_group, "T1")
    avg_t2_seconds = _average_segment_seconds(modality, sex_label, age_group, "T2")
    core_total_seconds = swim_seconds + bike_seconds + run_seconds
    estimated_total_seconds = core_total_seconds + avg_t1_seconds + avg_t2_seconds

    return {
        "valid": True,
        "entity": "derived_total",
        "modality": modality,
        "sex_label": sex_label,
        "age_group": age_group,
        "swim_seconds": swim_seconds,
        "swim_time": format_seconds(swim_seconds),
        "bike_seconds": bike_seconds,
        "bike_time": format_seconds(bike_seconds),
        "run_seconds": run_seconds,
        "run_time": format_seconds(run_seconds),
        "core_total_seconds": core_total_seconds,
        "core_total_time": format_seconds(core_total_seconds),
        "avg_t1_seconds": avg_t1_seconds,
        "avg_t1_time": format_seconds(avg_t1_seconds),
        "avg_t2_seconds": avg_t2_seconds,
        "avg_t2_time": format_seconds(avg_t2_seconds),
        "estimated_total_seconds": estimated_total_seconds,
        "estimated_total_time": format_seconds(estimated_total_seconds),
        "source": coverage.source,
        "sheet": coverage.sheet,
        "method": "swim + bike + run + average T1 + average T2",
    }


def get_estimated_total_percentile_from_segments(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    swim_time: Any,
    bike_time: Any,
    run_time: Any,
) -> dict[str, Any]:
    estimate = estimate_total_from_main_segments(
        modality,
        sex_category,
        age_group,
        swim_time,
        bike_time,
        run_time,
    )
    if not estimate.get("valid", False):
        return estimate

    percentile = get_total_percentile_by_time(
        estimate["modality"],
        estimate["sex_label"],
        estimate["age_group"],
        estimate["estimated_total_seconds"],
    )
    if not percentile.get("entity") == "total_time_curve":
        return percentile

    return {
        "valid": True,
        "entity": "estimated_total_percentile",
        "modality": estimate["modality"],
        "sex_label": estimate["sex_label"],
        "age_group": estimate["age_group"],
        "swim_seconds": estimate["swim_seconds"],
        "swim_time": estimate["swim_time"],
        "bike_seconds": estimate["bike_seconds"],
        "bike_time": estimate["bike_time"],
        "run_seconds": estimate["run_seconds"],
        "run_time": estimate["run_time"],
        "core_total_seconds": estimate["core_total_seconds"],
        "core_total_time": estimate["core_total_time"],
        "avg_t1_seconds": estimate["avg_t1_seconds"],
        "avg_t1_time": estimate["avg_t1_time"],
        "avg_t2_seconds": estimate["avg_t2_seconds"],
        "avg_t2_time": estimate["avg_t2_time"],
        "estimated_total_seconds": estimate["estimated_total_seconds"],
        "estimated_total_time": estimate["estimated_total_time"],
        "performance_percentile": percentile["performance_percentile"],
        "interpolated": percentile["interpolated"],
        "range_status": percentile["range_status"],
        "source": percentile["source"],
        "sheet": percentile["sheet"],
        "method": "swim + bike + run + average T1 + average T2, then official total-time curve",
    }


def get_run_time_for_target_total(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    swim_time: Any,
    bike_time: Any,
    target_total_time: Any,
) -> dict[str, Any]:
    modality = normalize_modality(modality)
    sex_label = normalize_sex_category(sex_category, field="sex_label")
    age_group = normalize_age_group(age_group)

    coverage = validate_query_inputs("segment_curve", modality, sex_label, age_group, segment="T1")
    if not coverage.valid:
        return coverage.to_dict()

    swim_seconds = parse_segment_time_to_seconds(modality, "Swim", swim_time)
    bike_seconds = parse_segment_time_to_seconds(modality, "Bike", bike_time)
    target_total_seconds = parse_time_to_seconds(target_total_time)
    avg_t1_seconds = _average_segment_seconds(modality, sex_label, age_group, "T1")
    avg_t2_seconds = _average_segment_seconds(modality, sex_label, age_group, "T2")
    required_run_seconds = target_total_seconds - swim_seconds - bike_seconds - avg_t1_seconds - avg_t2_seconds

    if required_run_seconds <= 0:
        return {
            "valid": False,
            "entity": "run_time_for_target_total",
            "modality": modality,
            "sex_label": sex_label,
            "age_group": age_group,
            "reason": "impossible_target_total",
            "message": "The target total time is not feasible with the provided swim and bike times plus average transitions.",
            "swim_seconds": swim_seconds,
            "bike_seconds": bike_seconds,
            "target_total_seconds": target_total_seconds,
            "avg_t1_seconds": avg_t1_seconds,
            "avg_t2_seconds": avg_t2_seconds,
        }

    return {
        "valid": True,
        "entity": "run_time_for_target_total",
        "modality": modality,
        "sex_label": sex_label,
        "age_group": age_group,
        "swim_seconds": swim_seconds,
        "swim_time": format_seconds(swim_seconds),
        "bike_seconds": bike_seconds,
        "bike_time": format_seconds(bike_seconds),
        "target_total_seconds": target_total_seconds,
        "target_total_time": format_seconds(target_total_seconds),
        "avg_t1_seconds": avg_t1_seconds,
        "avg_t1_time": format_seconds(avg_t1_seconds),
        "avg_t2_seconds": avg_t2_seconds,
        "avg_t2_time": format_seconds(avg_t2_seconds),
        "required_run_seconds": required_run_seconds,
        "required_run_time": format_seconds(required_run_seconds),
        "source": coverage.source,
        "sheet": coverage.sheet,
        "method": "target total - swim - bike - average T1 - average T2",
    }


def get_required_missing_segment_for_target_total(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    missing_segment: Any,
    target_total_time: Any,
    swim_time: Any | None = None,
    bike_time: Any | None = None,
    run_time: Any | None = None,
) -> dict[str, Any]:
    from .normalization import normalize_segment

    modality = normalize_modality(modality)
    sex_label = normalize_sex_category(sex_category, field="sex_label")
    age_group = normalize_age_group(age_group)
    missing_segment = normalize_segment(missing_segment)
    if missing_segment not in ("Swim", "Bike", "Run"):
        return {
            "valid": False,
            "entity": "required_missing_segment_for_target_total",
            "modality": modality,
            "sex_label": sex_label,
            "age_group": age_group,
            "missing_segment": missing_segment,
            "reason": "unsupported_missing_segment",
            "message": "Only Swim, Bike, or Run can be solved as the missing main segment.",
        }

    provided = {
        "Swim": swim_time,
        "Bike": bike_time,
        "Run": run_time,
    }
    missing_inputs = [segment for segment, value in provided.items() if segment != missing_segment and value is None]
    if missing_inputs:
        return {
            "valid": False,
            "entity": "required_missing_segment_for_target_total",
            "modality": modality,
            "sex_label": sex_label,
            "age_group": age_group,
            "missing_segment": missing_segment,
            "reason": "missing_required_fields",
            "missing_fields": [f"{segment.lower()}_time" for segment in missing_inputs],
            "message": "Two known main segment times are required to solve the missing segment.",
        }

    coverage = validate_query_inputs("segment_curve", modality, sex_label, age_group, segment="T1")
    if not coverage.valid:
        return coverage.to_dict()

    target_total_seconds = parse_time_to_seconds(target_total_time)
    avg_t1_seconds = _average_segment_seconds(modality, sex_label, age_group, "T1")
    avg_t2_seconds = _average_segment_seconds(modality, sex_label, age_group, "T2")
    known_seconds = {}
    for segment, value in provided.items():
        if segment != missing_segment and value is not None:
            known_seconds[segment] = parse_segment_time_to_seconds(modality, segment, value)

    required_seconds = target_total_seconds - sum(known_seconds.values()) - avg_t1_seconds - avg_t2_seconds
    if required_seconds <= 0:
        return {
            "valid": False,
            "entity": "required_missing_segment_for_target_total",
            "modality": modality,
            "sex_label": sex_label,
            "age_group": age_group,
            "missing_segment": missing_segment,
            "reason": "impossible_target_total",
            "message": "The target total time is not feasible with the provided segment times plus average transitions.",
            "target_total_seconds": target_total_seconds,
            "known_seconds": known_seconds,
            "avg_t1_seconds": avg_t1_seconds,
            "avg_t2_seconds": avg_t2_seconds,
        }

    result = {
        "valid": True,
        "entity": "required_missing_segment_for_target_total",
        "modality": modality,
        "sex_label": sex_label,
        "age_group": age_group,
        "missing_segment": missing_segment,
        "target_total_seconds": target_total_seconds,
        "target_total_time": format_seconds(target_total_seconds),
        "avg_t1_seconds": avg_t1_seconds,
        "avg_t1_time": format_seconds(avg_t1_seconds),
        "avg_t2_seconds": avg_t2_seconds,
        "avg_t2_time": format_seconds(avg_t2_seconds),
        "required_seconds": required_seconds,
        "required_time": format_seconds(required_seconds),
        "source": coverage.source,
        "sheet": coverage.sheet,
        "method": "target total - known main segments - average T1 - average T2",
    }
    for segment, seconds in known_seconds.items():
        key = segment.lower()
        result[f"{key}_seconds"] = seconds
        result[f"{key}_time"] = format_seconds(seconds)
    return result


def get_run_time_for_total_percentile(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    swim_time: Any,
    bike_time: Any,
    percentile: Any,
) -> dict[str, Any]:
    from .lookups_1d import get_total_time_by_percentile

    total_target = get_total_time_by_percentile(modality, sex_category, age_group, percentile)
    if not total_target.get("entity") == "total_time_curve":
        return total_target

    result = get_run_time_for_target_total(
        modality,
        sex_category,
        age_group,
        swim_time,
        bike_time,
        total_target["total_seconds"],
    )
    if not result.get("valid", False):
        return result
    return {
        **result,
        "entity": "run_time_for_total_percentile",
        "percentile": float(percentile),
        "target_total_percentile": total_target["percentile"],
        "target_total_source": total_target["source"],
        "method": "official total-time percentile target, then target total - swim - bike - average T1 - average T2",
    }


def get_required_missing_segment_for_target_percentile(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    missing_segment: Any,
    percentile: Any,
    swim_time: Any | None = None,
    bike_time: Any | None = None,
    run_time: Any | None = None,
) -> dict[str, Any]:
    from .lookups_1d import get_total_time_by_percentile

    total_target = get_total_time_by_percentile(modality, sex_category, age_group, percentile)
    if not total_target.get("entity") == "total_time_curve":
        return total_target

    result = get_required_missing_segment_for_target_total(
        modality,
        sex_category,
        age_group,
        missing_segment,
        total_target["total_seconds"],
        swim_time=swim_time,
        bike_time=bike_time,
        run_time=run_time,
    )
    if not result.get("valid", False):
        return result
    return {
        **result,
        "entity": "required_missing_segment_for_target_percentile",
        "percentile": float(percentile),
        "target_total_percentile": total_target["percentile"],
        "target_total_source": total_target["source"],
        "method": "official total-time percentile target, then target total - known main segments - average T1 - average T2",
    }
