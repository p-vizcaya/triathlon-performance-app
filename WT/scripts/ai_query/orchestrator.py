from __future__ import annotations

from typing import Any

from .explain import explain_result, round_percentile
from .normalization import format_seconds, normalize_segment, parse_time_to_seconds
from .router import route_query, route_query_plan


MAIN_SEGMENTS = ("Swim", "Bike", "Run")


def build_profile_plan(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    swim_time: Any,
    bike_time: Any,
    run_time: Any,
    *,
    include_sbr: bool = True,
    include_estimated_total: bool = True,
) -> list[dict[str, Any]]:
    plan = [
        {
            "intent": "segment_percentile_by_time",
            "modality": modality,
            "sex_category": sex_category,
            "age_group": age_group,
            "segment": "Swim",
            "segment_time": swim_time,
        },
        {
            "intent": "segment_percentile_by_time",
            "modality": modality,
            "sex_category": sex_category,
            "age_group": age_group,
            "segment": "Bike",
            "segment_time": bike_time,
        },
        {
            "intent": "segment_percentile_by_time",
            "modality": modality,
            "sex_category": sex_category,
            "age_group": age_group,
            "segment": "Run",
            "segment_time": run_time,
        },
    ]
    if include_sbr:
        plan.append(
            {
                "intent": "sbr_percentile_by_segment_times",
                "modality": modality,
                "sex_category": sex_category,
                "age_group": age_group,
                "swim_time": swim_time,
                "bike_time": bike_time,
                "run_time": run_time,
            }
        )
    if include_estimated_total:
        plan.append(
            {
                "intent": "estimated_total_percentile_from_segments",
                "modality": modality,
                "sex_category": sex_category,
                "age_group": age_group,
                "swim_time": swim_time,
                "bike_time": bike_time,
                "run_time": run_time,
            }
        )
    return plan


def _segment_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        step["result"]
        for step in results
        if step["result"].get("entity") == "segment_curve"
        and "performance_percentile" in step["result"]
        and step["result"].get("segment") in MAIN_SEGMENTS
    ]


def _weakest_segment(segment_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not segment_results:
        return None
    return min(segment_results, key=lambda result: float(result["performance_percentile"]))


def _strongest_segment(segment_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not segment_results:
        return None
    return max(segment_results, key=lambda result: float(result["performance_percentile"]))


def evaluate_main_segment_profile(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    swim_time: Any,
    bike_time: Any,
    run_time: Any,
    *,
    explain: bool = True,
) -> dict[str, Any]:
    plan = build_profile_plan(modality, sex_category, age_group, swim_time, bike_time, run_time)
    plan_result = route_query_plan(plan, explain=explain)
    if not plan_result.get("valid", False):
        return plan_result

    segments = _segment_results(plan_result["results"])
    weakest = _weakest_segment(segments)
    strongest = _strongest_segment(segments)
    sbr = next((step["result"] for step in plan_result["results"] if step["result"].get("entity") == "sbr_cube"), None)
    estimated_total = next(
        (step["result"] for step in plan_result["results"] if step["result"].get("entity") == "estimated_total_percentile"),
        None,
    )

    summary = None
    if weakest and strongest:
        summary = (
            f"Weakest main segment: {weakest['segment']} at {round_percentile(weakest['performance_percentile'])}. "
            f"Strongest main segment: {strongest['segment']} at {round_percentile(strongest['performance_percentile'])}."
        )
        if sbr:
            summary += f" Joint SBR performance is approximately {round_percentile(sbr['joint_sbr_percentile'])}."
        if estimated_total:
            summary += (
                f" Estimated total time is {estimated_total['estimated_total_time']} "
                f"at approximately {round_percentile(estimated_total['performance_percentile'])}."
            )

    return {
        "valid": True,
        "entity": "main_segment_profile",
        "plan": plan,
        "results": plan_result["results"],
        "weakest_segment": weakest,
        "strongest_segment": strongest,
        "sbr_result": sbr,
        "estimated_total_result": estimated_total,
        "summary": summary,
    }


def find_weakest_main_segment(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    swim_time: Any,
    bike_time: Any,
    run_time: Any,
) -> dict[str, Any]:
    profile = evaluate_main_segment_profile(
        modality,
        sex_category,
        age_group,
        swim_time,
        bike_time,
        run_time,
        explain=False,
    )
    if not profile.get("valid", False):
        return profile
    weakest = profile["weakest_segment"]
    return {
        "valid": True,
        "entity": "weakest_main_segment",
        "modality": weakest["modality"],
        "sex_label": weakest["sex_label"],
        "age_group": weakest["age_group"],
        "segment": weakest["segment"],
        "performance_percentile": weakest["performance_percentile"],
        "time": weakest["input_time"],
        "summary": (
            f"Weakest main segment: {weakest['segment']} at "
            f"{round_percentile(weakest['performance_percentile'])}."
        ),
    }


def compare_segment_scenarios(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    segment: Any,
    current_time: Any,
    target_time: Any,
) -> dict[str, Any]:
    segment = normalize_segment(segment)
    current = route_query(
        {
            "intent": "segment_percentile_by_time",
            "modality": modality,
            "sex_category": sex_category,
            "age_group": age_group,
            "segment": segment,
            "segment_time": current_time,
        }
    )
    if not current.get("entity") == "segment_curve":
        return current

    target = route_query(
        {
            "intent": "segment_percentile_by_time",
            "modality": modality,
            "sex_category": sex_category,
            "age_group": age_group,
            "segment": segment,
            "segment_time": target_time,
        }
    )
    if not target.get("entity") == "segment_curve":
        return target

    current_seconds = parse_time_to_seconds(current_time)
    target_seconds = parse_time_to_seconds(target_time)
    percentile_delta = target["performance_percentile"] - current["performance_percentile"]
    seconds_delta = target_seconds - current_seconds

    return {
        "valid": True,
        "entity": "segment_scenario_comparison",
        "modality": current["modality"],
        "sex_label": current["sex_label"],
        "age_group": current["age_group"],
        "segment": segment,
        "current": current,
        "target": target,
        "seconds_delta": seconds_delta,
        "time_delta": format_seconds(abs(seconds_delta)),
        "percentile_delta": percentile_delta,
        "summary": (
            f"For {current['modality']} {current['sex_label']} {current['age_group']}, changing {segment} "
            f"from {current['input_time']} ({round_percentile(current['performance_percentile'])}) "
            f"to {target['input_time']} ({round_percentile(target['performance_percentile'])}) "
            f"changes the marginal percentile by {percentile_delta:+.1f} points."
        ),
    }


def explain_profile_result(profile: dict[str, Any]) -> str:
    if not profile.get("valid", False):
        return str(profile.get("message", "The profile could not be evaluated."))
    if profile.get("summary"):
        return str(profile["summary"])
    explanations = [explain_result(step["result"]) for step in profile.get("results", [])]
    return " ".join(explanations)

