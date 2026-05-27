from __future__ import annotations

from typing import Any


def round_percentile(value: Any) -> str:
    number = float(value)
    rounded = round(number, 1)
    if rounded.is_integer():
        return f"P{int(rounded)}"
    return f"P{rounded:.1f}"


def _context(result: dict[str, Any]) -> str:
    return f"{result.get('modality')} {result.get('sex_label')} {result.get('age_group')}"


def _range_note(result: dict[str, Any]) -> str:
    status = result.get("range_status")
    if status == "below_range":
        return " The input is faster than the available reference range, so the result is capped at the top of the curve."
    if status == "above_range":
        return " The input is slower than the available reference range, so the result is capped at the bottom of the curve."
    return ""


def _invalid_message(result: dict[str, Any]) -> str:
    message = result.get("message")
    if message:
        return str(message)
    entity = result.get("entity", "query")
    return f"The {entity} query is not available for {_context(result)}."


def _total_time_explanation(result: dict[str, Any]) -> str:
    if "performance_percentile" in result:
        return (
            f"For {_context(result)}, a total time of {result['input_total_time']} "
            f"corresponds to approximately {round_percentile(result['performance_percentile'])}."
            f"{_range_note(result)}"
        )
    return (
        f"For {_context(result)}, {round_percentile(result['percentile'])} "
        f"corresponds to a total time of approximately {result['total_time']}."
        f"{_range_note(result)}"
    )


def _segment_explanation(result: dict[str, Any]) -> str:
    segment = result.get("segment")
    if "performance_percentile" in result:
        return (
            f"For {_context(result)}, a {segment} time of {result['input_time']} "
            f"corresponds to approximately {round_percentile(result['performance_percentile'])}."
            f"{_range_note(result)}"
        )
    return (
        f"For {_context(result)}, {round_percentile(result['percentile'])} "
        f"corresponds to a {segment} time of approximately {result['time']}."
        f"{_range_note(result)}"
    )


def _derived_total_explanation(result: dict[str, Any]) -> str:
    return (
        f"For {_context(result)}, swim {result['swim_time']}, bike {result['bike_time']}, "
        f"and run {result['run_time']} estimate to a total time of {result['estimated_total_time']} "
        f"after adding average T1 ({result['avg_t1_time']}) and average T2 ({result['avg_t2_time']})."
    )


def _estimated_total_percentile_explanation(result: dict[str, Any]) -> str:
    return (
        f"For {_context(result)}, the estimated total time is {result['estimated_total_time']}, "
        f"which corresponds to approximately {round_percentile(result['performance_percentile'])}. "
        f"The estimate adds average T1 ({result['avg_t1_time']}) and average T2 ({result['avg_t2_time']}) "
        f"to the provided swim, bike, and run times."
        f"{_range_note(result)}"
    )


def _required_run_explanation(result: dict[str, Any]) -> str:
    target = (
        f"{round_percentile(result['target_total_percentile'])} total time"
        if result.get("entity") == "run_time_for_total_percentile"
        else f"a total time of {result['target_total_time']}"
    )
    return (
        f"For {_context(result)}, with swim {result['swim_time']} and bike {result['bike_time']}, "
        f"the required run is approximately {result['required_run_time']} to reach {target}. "
        f"This subtracts average T1 ({result['avg_t1_time']}) and average T2 ({result['avg_t2_time']}) "
        f"from the target total."
    )


def _required_missing_segment_explanation(result: dict[str, Any]) -> str:
    target = (
        f"{round_percentile(result['target_total_percentile'])} total time"
        if result.get("entity") == "required_missing_segment_for_target_percentile"
        else f"a total time of {result['target_total_time']}"
    )
    return (
        f"For {_context(result)}, the required {result['missing_segment']} is approximately "
        f"{result['required_time']} to reach {target}. This uses average T1 "
        f"({result['avg_t1_time']}) and average T2 ({result['avg_t2_time']})."
    )


def _gap_explanation(result: dict[str, Any]) -> str:
    if result["direction"] == "already_at_or_above_target":
        return (
            f"For {_context(result)}, current {result['scope']} performance is "
            f"{round_percentile(result['current_percentile'])}, already at or above "
            f"{round_percentile(result['target_percentile'])}."
        )
    return (
        f"For {_context(result)}, current {result['scope']} performance is "
        f"{round_percentile(result['current_percentile'])}. To reach "
        f"{round_percentile(result['target_percentile'])}, the target time is approximately "
        f"{result['target_time']}, requiring an improvement of about {result['improvement_time']}."
    )
def _pair_explanation(result: dict[str, Any]) -> str:
    return (
        f"For {_context(result)}, the {result['pair']} combination "
        f"({result['x_segment']} {round_percentile(result['x_performance_percentile'])}, "
        f"{result['y_segment']} {round_percentile(result['y_performance_percentile'])}) "
        f"corresponds to approximately {round_percentile(result['joint_pair_percentile'])} jointly."
        f"{_range_note(result)}"
    )


def _sbr_explanation(result: dict[str, Any]) -> str:
    return (
        f"For {_context(result)}, the swim-bike-run combination "
        f"(Swim {round_percentile(result['swim_performance_percentile'])}, "
        f"Bike {round_percentile(result['bike_performance_percentile'])}, "
        f"Run {round_percentile(result['run_performance_percentile'])}) "
        f"corresponds to approximately {round_percentile(result['joint_sbr_percentile'])} jointly."
        f"{_range_note(result)}"
    )


def explain_result(result: dict[str, Any], locale: str = "en") -> str:
    if locale != "en":
        raise ValueError("Only English explanations are currently supported")
    if not result.get("valid", True):
        return _invalid_message(result)

    entity = result.get("entity")
    if entity == "total_time_curve":
        return _total_time_explanation(result)
    if entity == "segment_curve":
        return _segment_explanation(result)
    if entity == "derived_total":
        return _derived_total_explanation(result)
    if entity == "estimated_total_percentile":
        return _estimated_total_percentile_explanation(result)
    if entity in ("run_time_for_target_total", "run_time_for_total_percentile"):
        return _required_run_explanation(result)
    if entity in ("required_missing_segment_for_target_total", "required_missing_segment_for_target_percentile"):
        return _required_missing_segment_explanation(result)
    if entity == "gap_to_target_percentile":
        return _gap_explanation(result)
    if entity == "compare_segments":
        return str(result.get("summary", "Segment comparison completed."))
    if entity == "explain_percentile":
        return str(result.get("summary", "Percentile explanation completed."))
    if entity == "conditional_segment_percentile":
        return str(result.get("summary", "Conditional percentile completed."))
    if entity == "segment_pair_plane":
        return _pair_explanation(result)
    if entity == "sbr_cube":
        return _sbr_explanation(result)
    return "The query completed, but no explanation template is available for this result type."
