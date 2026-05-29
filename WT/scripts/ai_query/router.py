from __future__ import annotations

from typing import Any, Callable

from .derived_totals import (
    estimate_total_from_main_segments,
    get_estimated_total_percentile_from_segments,
    get_required_missing_segment_for_target_percentile,
    get_required_missing_segment_for_target_total,
    get_run_time_for_target_total,
    get_run_time_for_total_percentile,
)
from .analysis_intents import compare_segments, explain_percentile, gap_to_target_percentile
from .conditional import conditional_segment_percentile_from_joint
from .event_curves import compare_percentile_to_event_curves, compare_time_to_event_curves
from .explain import explain_result
from .lookups_1d import (
    get_segment_percentile_by_time,
    get_segment_time_by_percentile,
    get_total_percentile_by_time,
    get_total_time_by_percentile,
)
from .lookups_2d import (
    get_pair_percentile_by_segment_percentiles,
    get_pair_percentile_by_segment_times,
    get_pair_times_by_percentiles,
)
from .lookups_3d import (
    get_sbr_percentile_by_segment_percentiles,
    get_sbr_percentile_by_segment_times,
    get_sbr_times_by_percentiles,
)


class RoutingError(ValueError):
    """Raised when an intent payload cannot be routed safely."""


def _required(payload: dict[str, Any], *fields: str) -> list[str]:
    return [field for field in fields if payload.get(field) is None]


def _missing_result(intent: str, missing: list[str]) -> dict[str, Any]:
    return {
        "valid": False,
        "entity": "router",
        "intent": intent,
        "reason": "missing_required_fields",
        "missing_fields": missing,
        "message": f"Missing required field(s): {', '.join(missing)}.",
    }


def _call_if_complete(
    payload: dict[str, Any],
    intent: str,
    required_fields: tuple[str, ...],
    function: Callable[..., dict[str, Any]],
    argument_fields: tuple[str, ...],
) -> dict[str, Any]:
    missing = _required(payload, *required_fields)
    if missing:
        return _missing_result(intent, missing)
    return function(*(payload[field] for field in argument_fields))


def route_query(payload: dict[str, Any], *, explain: bool = False) -> dict[str, Any]:
    intent = payload.get("intent")
    if not intent:
        return _missing_result("", ["intent"])

    routes: dict[str, tuple[Callable[..., dict[str, Any]], tuple[str, ...]]] = {
        "total_percentile_by_time": (
            get_total_percentile_by_time,
            ("modality", "sex_category", "age_group", "total_time"),
        ),
        "total_time_to_percentile": (
            get_total_percentile_by_time,
            ("modality", "sex_category", "age_group", "total_time"),
        ),
        "total_time_by_percentile": (
            get_total_time_by_percentile,
            ("modality", "sex_category", "age_group", "percentile"),
        ),
        "percentile_to_total_time": (
            get_total_time_by_percentile,
            ("modality", "sex_category", "age_group", "percentile"),
        ),
        "segment_percentile_by_time": (
            get_segment_percentile_by_time,
            ("modality", "sex_category", "age_group", "segment", "segment_time"),
        ),
        "segment_time_to_percentile": (
            get_segment_percentile_by_time,
            ("modality", "sex_category", "age_group", "segment", "segment_time"),
        ),
        "segment_time_by_percentile": (
            get_segment_time_by_percentile,
            ("modality", "sex_category", "age_group", "segment", "percentile"),
        ),
        "estimate_total_from_main_segments": (
            estimate_total_from_main_segments,
            ("modality", "sex_category", "age_group", "swim_time", "bike_time", "run_time"),
        ),
        "estimated_total_percentile_from_segments": (
            get_estimated_total_percentile_from_segments,
            ("modality", "sex_category", "age_group", "swim_time", "bike_time", "run_time"),
        ),
        "run_time_for_target_total": (
            get_run_time_for_target_total,
            ("modality", "sex_category", "age_group", "swim_time", "bike_time", "target_total_time"),
        ),
        "run_time_for_total_percentile": (
            get_run_time_for_total_percentile,
            ("modality", "sex_category", "age_group", "swim_time", "bike_time", "percentile"),
        ),
        "required_missing_segment_for_target_total": (
            get_required_missing_segment_for_target_total,
            ("modality", "sex_category", "age_group", "missing_segment", "target_total_time", "swim_time", "bike_time", "run_time"),
        ),
        "required_missing_segment_for_target_percentile": (
            get_required_missing_segment_for_target_percentile,
            ("modality", "sex_category", "age_group", "missing_segment", "percentile", "swim_time", "bike_time", "run_time"),
        ),
        "gap_to_target_percentile": (
            gap_to_target_percentile,
            ("modality", "sex_category", "age_group", "current_time", "target_percentile", "segment"),
        ),
        "compare_segments": (
            compare_segments,
            ("modality", "sex_category", "age_group", "swim_time", "bike_time", "run_time", "t1_time", "t2_time", "total_time"),
        ),
        "event_time_to_position": (
            compare_time_to_event_curves,
            ("modality", "sex_category", "age_group", "segment", "time_value", "event_years", "min_n"),
        ),
        "event_time_by_percentile": (
            compare_percentile_to_event_curves,
            ("modality", "sex_category", "age_group", "segment", "percentile", "event_years", "min_n"),
        ),
        "explain_percentile": (
            explain_percentile,
            ("percentile",),
        ),
        "conditional_segment_percentile": (
            conditional_segment_percentile_from_joint,
            ("modality", "sex_category", "age_group", "target_segment", "target_time", "condition_1_segment", "condition_1_time"),
        ),
        "pair_percentile_by_segment_times": (
            get_pair_percentile_by_segment_times,
            ("modality", "sex_category", "age_group", "pair", "x_time", "y_time"),
        ),
        "pair_percentile_by_segment_percentiles": (
            get_pair_percentile_by_segment_percentiles,
            ("modality", "sex_category", "age_group", "pair", "x_percentile", "y_percentile"),
        ),
        "pair_times_by_percentiles": (
            get_pair_times_by_percentiles,
            ("modality", "sex_category", "age_group", "pair", "x_percentile", "y_percentile"),
        ),
        "sbr_percentile_by_segment_times": (
            get_sbr_percentile_by_segment_times,
            ("modality", "sex_category", "age_group", "swim_time", "bike_time", "run_time"),
        ),
        "sbr_percentile_by_segment_percentiles": (
            get_sbr_percentile_by_segment_percentiles,
            ("modality", "sex_category", "age_group", "swim_percentile", "bike_percentile", "run_percentile"),
        ),
        "sbr_times_by_percentiles": (
            get_sbr_times_by_percentiles,
            ("modality", "sex_category", "age_group", "swim_percentile", "bike_percentile", "run_percentile"),
        ),
    }

    if intent not in routes:
        valid_intents = ", ".join(sorted(routes))
        return {
            "valid": False,
            "entity": "router",
            "intent": intent,
            "reason": "unknown_intent",
            "message": f"Unknown intent {intent!r}.",
            "valid_intents": sorted(routes),
            "valid_intents_text": valid_intents,
        }

    if intent == "gap_to_target_percentile":
        missing = _required(payload, "modality", "sex_category", "age_group", "current_time", "target_percentile")
        if missing:
            return _missing_result(intent, missing)
        result = gap_to_target_percentile(
            payload["modality"],
            payload["sex_category"],
            payload["age_group"],
            payload["current_time"],
            payload["target_percentile"],
            segment=payload.get("segment"),
        )
        if explain:
            result = {**result, "explanation": explain_result(result)}
        return result

    if intent == "compare_segments":
        missing = _required(payload, "modality", "sex_category", "age_group")
        if missing:
            return _missing_result(intent, missing)
        result = compare_segments(
            payload["modality"],
            payload["sex_category"],
            payload["age_group"],
            swim_time=payload.get("swim_time"),
            bike_time=payload.get("bike_time"),
            run_time=payload.get("run_time"),
            t1_time=payload.get("t1_time"),
            t2_time=payload.get("t2_time"),
            total_time=payload.get("total_time"),
        )
        if explain:
            result = {**result, "explanation": explain_result(result)}
        return result

    if intent == "explain_percentile":
        missing = _required(payload, "percentile")
        if missing:
            return _missing_result(intent, missing)
        result = explain_percentile(payload["percentile"], scope=payload.get("scope") or payload.get("segment"))
        if explain:
            result = {**result, "explanation": explain_result(result)}
        return result

    if intent in ("event_time_to_position", "event_time_by_percentile"):
        lookup_field = "time_value" if intent == "event_time_to_position" else "percentile"
        missing = _required(payload, "modality", "sex_category", "age_group", "segment", lookup_field)
        if missing:
            return _missing_result(intent, missing)
        function = compare_time_to_event_curves if intent == "event_time_to_position" else compare_percentile_to_event_curves
        result = function(
            payload["modality"],
            payload["sex_category"],
            payload["age_group"],
            payload["segment"],
            payload[lookup_field],
            event_years=payload.get("event_years"),
            min_n=int(payload.get("min_n") or 20),
        )
        if explain:
            result = {**result, "explanation": explain_result(result)}
        return result

    if intent == "conditional_segment_percentile":
        missing = _required(payload, "modality", "sex_category", "age_group", "target_segment", "target_time", "condition_1_segment")
        has_threshold = payload.get("condition_1_time") is not None
        has_interval = payload.get("condition_1_lower_time") is not None and payload.get("condition_1_upper_time") is not None
        if not has_threshold and not has_interval:
            missing.append("condition_1_time")
        if missing:
            return _missing_result(intent, missing)
        result = conditional_segment_percentile_from_joint(
            payload["modality"],
            payload["sex_category"],
            payload["age_group"],
            payload["target_segment"],
            payload["target_time"],
            payload["condition_1_segment"],
            payload["condition_1_time"],
            condition_2_segment=payload.get("condition_2_segment"),
            condition_2_time=payload.get("condition_2_time"),
            condition_1_operator=payload.get("condition_1_operator"),
            condition_1_lower_time=payload.get("condition_1_lower_time"),
            condition_1_upper_time=payload.get("condition_1_upper_time"),
            condition_2_operator=payload.get("condition_2_operator"),
            condition_2_lower_time=payload.get("condition_2_lower_time"),
            condition_2_upper_time=payload.get("condition_2_upper_time"),
        )
        if explain:
            result = {**result, "explanation": explain_result(result)}
        return result

    if intent in ("required_missing_segment_for_target_total", "required_missing_segment_for_target_percentile"):
        required = ["modality", "sex_category", "age_group", "missing_segment"]
        required.append("target_total_time" if intent.endswith("target_total") else "percentile")
        missing = _required(payload, *required)
        if missing:
            return _missing_result(intent, missing)
        function = get_required_missing_segment_for_target_total if intent.endswith("target_total") else get_required_missing_segment_for_target_percentile
        result = function(
            payload["modality"],
            payload["sex_category"],
            payload["age_group"],
            payload["missing_segment"],
            payload[required[-1]],
            swim_time=payload.get("swim_time"),
            bike_time=payload.get("bike_time"),
            run_time=payload.get("run_time"),
        )
        if explain:
            result = {**result, "explanation": explain_result(result)}
        return result

    function, fields = routes[intent]
    result = _call_if_complete(payload, intent, fields, function, fields)
    if explain:
        result = {**result, "explanation": explain_result(result)}
    return result


def route_query_plan(plan: list[dict[str, Any]], *, explain: bool = False) -> dict[str, Any]:
    results = []
    for index, payload in enumerate(plan, start=1):
        result = route_query(payload, explain=explain)
        results.append({"step": index, "intent": payload.get("intent"), "result": result})
        if not result.get("valid", True):
            return {
                "valid": False,
                "entity": "query_plan",
                "failed_step": index,
                "results": results,
                "message": result.get("message", "Query plan failed."),
            }
    return {
        "valid": True,
        "entity": "query_plan",
        "results": results,
    }
