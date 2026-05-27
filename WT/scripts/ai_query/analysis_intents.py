from __future__ import annotations

from typing import Any

from .explain import round_percentile
from .lookups_1d import (
    get_segment_percentile_by_time,
    get_segment_time_by_percentile,
    get_total_percentile_by_time,
    get_total_time_by_percentile,
)
from .normalization import format_seconds, normalize_age_group, normalize_modality, normalize_segment, normalize_sex_category, parse_time_to_seconds


def gap_to_target_percentile(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    current_time: Any,
    target_percentile: Any,
    *,
    segment: Any | None = None,
) -> dict[str, Any]:
    modality = normalize_modality(modality)
    sex_label = normalize_sex_category(sex_category, field="sex_label")
    age_group = normalize_age_group(age_group)
    target_percentile = float(target_percentile)

    if segment is None:
        current = get_total_percentile_by_time(modality, sex_label, age_group, current_time)
        target = get_total_time_by_percentile(modality, sex_label, age_group, target_percentile)
        entity = "gap_to_target_percentile"
        scope = "Total"
        current_seconds_key = "input_total_seconds"
        target_seconds_key = "total_seconds"
        target_time_key = "total_time"
    else:
        segment = normalize_segment(segment)
        current = get_segment_percentile_by_time(modality, sex_label, age_group, segment, current_time)
        target = get_segment_time_by_percentile(modality, sex_label, age_group, segment, target_percentile)
        entity = "gap_to_target_percentile"
        scope = segment
        current_seconds_key = "input_seconds"
        target_seconds_key = "seconds"
        target_time_key = "time"

    if not current.get("entity") in ("total_time_curve", "segment_curve"):
        return current
    if not target.get("entity") in ("total_time_curve", "segment_curve"):
        return target

    current_seconds = float(current[current_seconds_key])
    target_seconds = float(target[target_seconds_key])
    improvement_seconds = current_seconds - target_seconds
    percentile_gap = target_percentile - float(current["performance_percentile"])

    return {
        "valid": True,
        "entity": entity,
        "modality": modality,
        "sex_label": sex_label,
        "age_group": age_group,
        "scope": scope,
        "current_seconds": current_seconds,
        "current_time": format_seconds(current_seconds),
        "current_percentile": current["performance_percentile"],
        "target_percentile": target_percentile,
        "target_seconds": target_seconds,
        "target_time": target[target_time_key],
        "improvement_seconds": improvement_seconds,
        "improvement_time": format_seconds(abs(improvement_seconds)),
        "percentile_gap": percentile_gap,
        "direction": "improve" if improvement_seconds > 0 else "already_at_or_above_target",
        "source": target.get("source"),
        "sheet": target.get("sheet"),
    }


def compare_segments(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    swim_time: Any | None = None,
    bike_time: Any | None = None,
    run_time: Any | None = None,
    t1_time: Any | None = None,
    t2_time: Any | None = None,
    total_time: Any | None = None,
) -> dict[str, Any]:
    modality = normalize_modality(modality)
    sex_label = normalize_sex_category(sex_category, field="sex_label")
    age_group = normalize_age_group(age_group)
    inputs = {
        "Swim": swim_time,
        "T1": t1_time,
        "Bike": bike_time,
        "T2": t2_time,
        "Run": run_time,
        "Total": total_time,
    }
    provided = {segment: value for segment, value in inputs.items() if value is not None}
    if len(provided) < 2:
        return {
            "valid": False,
            "entity": "compare_segments",
            "modality": modality,
            "sex_label": sex_label,
            "age_group": age_group,
            "reason": "insufficient_segments",
            "message": "At least two segment times are required to compare segments.",
        }

    segment_results = []
    for segment, value in provided.items():
        result = get_segment_percentile_by_time(modality, sex_label, age_group, segment, value)
        if not result.get("entity") == "segment_curve":
            return result
        segment_results.append(result)

    ranked = sorted(segment_results, key=lambda item: float(item["performance_percentile"]))
    weakest = ranked[0]
    strongest = ranked[-1]
    return {
        "valid": True,
        "entity": "compare_segments",
        "modality": modality,
        "sex_label": sex_label,
        "age_group": age_group,
        "segments": segment_results,
        "ranked_segments": ranked,
        "weakest_segment": weakest,
        "strongest_segment": strongest,
        "summary": (
            f"Weakest provided segment: {weakest['segment']} at {round_percentile(weakest['performance_percentile'])}. "
            f"Strongest provided segment: {strongest['segment']} at {round_percentile(strongest['performance_percentile'])}."
        ),
    }


def explain_percentile(
    percentile: Any,
    *,
    scope: Any | None = None,
) -> dict[str, Any]:
    percentile = float(percentile)
    if not 0 <= percentile <= 100:
        return {
            "valid": False,
            "entity": "explain_percentile",
            "reason": "invalid_percentile",
            "message": "Percentile must be between 0 and 100.",
        }
    scope_text = str(scope).strip() if scope is not None else "the selected reference group"
    return {
        "valid": True,
        "entity": "explain_percentile",
        "percentile": percentile,
        "scope": scope_text,
        "summary": (
            f"{round_percentile(percentile)} means the performance is better than approximately "
            f"{percentile:.1f}% of {scope_text}, using the relevant reference curve or joint table."
        ),
    }
