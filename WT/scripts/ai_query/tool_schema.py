from __future__ import annotations

from copy import deepcopy
from typing import Any


GLOBAL_RULES = (
    "Use only approved tools for percentile and time calculations.",
    "Ask for clarification when required fields are missing.",
    "Do not suggest substitute or nearby age groups when coverage is unavailable.",
    "Do not expose internal curve iterations to users.",
    "Use Standard, Sprint, F, and O as canonical user-facing values.",
    "Use h:mm:ss for times of one hour or longer, and mm:ss below one hour.",
    "Accept sport performance units as segment inputs: Swim pace mm:ss/100m, Bike speed km/h, and Run pace mm:ss/km. Convert them to segment time using Sprint distances 750m/20km/5km and Standard distances 1500m/40km/10km.",
    "For total-time percentile from only swim, bike, and run, use estimated total with average T1 and T2.",
    "For two-segment joint percentile, use pair planes; do not average marginal percentiles.",
    "For swim-bike-run joint percentile, use the SBR cube; do not average marginal percentiles.",
)


COMMON_REQUIRED = ("modality", "sex_category", "age_group")


AVAILABLE_TOOLS: tuple[dict[str, Any], ...] = (
    {
        "name": "total_percentile_by_time",
        "description": "Return the official total-time performance percentile for a total time.",
        "required": (*COMMON_REQUIRED, "total_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "total_time"),
        "do_not_infer": ("sex_category", "age_group"),
        "examples": [
            {
                "user_request": "What percentile is 1:20:00 for Sprint F 40-44?",
                "payload": {
                    "intent": "total_percentile_by_time",
                    "modality": "Sprint",
                    "sex_category": "F",
                    "age_group": "40-44",
                    "total_time": "1:20:00",
                },
            }
        ],
    },
    {
        "name": "total_time_to_percentile",
        "description": "Alias for total_percentile_by_time. Return the official total-time performance percentile for a total time.",
        "required": (*COMMON_REQUIRED, "total_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "total_time"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "total_time_by_percentile",
        "description": "Return the official total time corresponding to a target percentile.",
        "required": (*COMMON_REQUIRED, "percentile"),
        "clarify_if_missing": (*COMMON_REQUIRED, "percentile"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "percentile_to_total_time",
        "description": "Alias for total_time_by_percentile. Return the official total time corresponding to a target percentile.",
        "required": (*COMMON_REQUIRED, "percentile"),
        "clarify_if_missing": (*COMMON_REQUIRED, "percentile"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "segment_percentile_by_time",
        "description": "Return the marginal performance percentile for one segment time.",
        "required": (*COMMON_REQUIRED, "segment", "segment_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "segment", "segment_time"),
        "do_not_infer": ("sex_category", "age_group", "segment"),
    },
    {
        "name": "segment_time_to_percentile",
        "description": "Alias for segment_percentile_by_time. Return the marginal performance percentile for one segment time.",
        "required": (*COMMON_REQUIRED, "segment", "segment_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "segment", "segment_time"),
        "do_not_infer": ("sex_category", "age_group", "segment"),
    },
    {
        "name": "segment_time_by_percentile",
        "description": "Return the segment time corresponding to a target marginal percentile.",
        "required": (*COMMON_REQUIRED, "segment", "percentile"),
        "clarify_if_missing": (*COMMON_REQUIRED, "segment", "percentile"),
        "do_not_infer": ("sex_category", "age_group", "segment"),
    },
    {
        "name": "estimate_total_from_main_segments",
        "description": "Estimate total time from swim, bike, and run by adding average T1 and T2.",
        "required": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "estimated_total_percentile_from_segments",
        "description": "Estimate total time from swim, bike, and run, then compare it with the official total-time curve.",
        "required": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "run_time_for_target_total",
        "description": "Return the run time required to reach a target total time, given swim and bike, using average T1 and T2.",
        "required": (*COMMON_REQUIRED, "swim_time", "bike_time", "target_total_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "swim_time", "bike_time", "target_total_time"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "run_time_for_total_percentile",
        "description": "Return the run time required to reach a target official total-time percentile, given swim and bike, using average T1 and T2.",
        "required": (*COMMON_REQUIRED, "swim_time", "bike_time", "percentile"),
        "clarify_if_missing": (*COMMON_REQUIRED, "swim_time", "bike_time", "percentile"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "required_missing_segment_for_target_percentile",
        "description": "Return the missing Swim, Bike, or Run time required to reach a target official total-time percentile, given the other two main segment times and average T1/T2.",
        "required": (*COMMON_REQUIRED, "missing_segment", "percentile"),
        "clarify_if_missing": (*COMMON_REQUIRED, "missing_segment", "percentile", "two known main segment times"),
        "do_not_infer": ("sex_category", "age_group", "missing_segment"),
    },
    {
        "name": "gap_to_target_percentile",
        "description": "Return the time gap between a current total or segment time and a target percentile.",
        "required": (*COMMON_REQUIRED, "current_time", "target_percentile"),
        "clarify_if_missing": (*COMMON_REQUIRED, "current_time", "target_percentile"),
        "do_not_infer": ("sex_category", "age_group"),
        "optional": ("segment",),
    },
    {
        "name": "compare_segments",
        "description": "Compare marginal percentiles for two or more provided segment times.",
        "required": COMMON_REQUIRED,
        "clarify_if_missing": (*COMMON_REQUIRED, "at least two segment times"),
        "do_not_infer": ("sex_category", "age_group"),
        "optional": ("swim_time", "bike_time", "run_time", "t1_time", "t2_time", "total_time"),
    },
    {
        "name": "pair_percentile_by_segment_times",
        "description": "Return a two-segment joint percentile from two segment times.",
        "required": (*COMMON_REQUIRED, "pair", "x_time", "y_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "pair", "x_time", "y_time"),
        "do_not_infer": ("sex_category", "age_group", "pair"),
    },
    {
        "name": "pair_percentile_by_segment_percentiles",
        "description": "Return a two-segment joint percentile from two marginal percentiles.",
        "required": (*COMMON_REQUIRED, "pair", "x_percentile", "y_percentile"),
        "clarify_if_missing": (*COMMON_REQUIRED, "pair", "x_percentile", "y_percentile"),
        "do_not_infer": ("sex_category", "age_group", "pair"),
    },
    {
        "name": "pair_times_by_percentiles",
        "description": "Return pair-axis times and joint percentile from two marginal percentiles.",
        "required": (*COMMON_REQUIRED, "pair", "x_percentile", "y_percentile"),
        "clarify_if_missing": (*COMMON_REQUIRED, "pair", "x_percentile", "y_percentile"),
        "do_not_infer": ("sex_category", "age_group", "pair"),
    },
    {
        "name": "sbr_percentile_by_segment_times",
        "description": "Return the swim-bike-run joint percentile from swim, bike, and run times.",
        "required": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "sbr_percentile_by_segment_percentiles",
        "description": "Return the swim-bike-run joint percentile from three marginal percentiles.",
        "required": (*COMMON_REQUIRED, "swim_percentile", "bike_percentile", "run_percentile"),
        "clarify_if_missing": (*COMMON_REQUIRED, "swim_percentile", "bike_percentile", "run_percentile"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "sbr_times_by_percentiles",
        "description": "Return swim, bike, and run axis times plus joint SBR percentile from three marginal percentiles.",
        "required": (*COMMON_REQUIRED, "swim_percentile", "bike_percentile", "run_percentile"),
        "clarify_if_missing": (*COMMON_REQUIRED, "swim_percentile", "bike_percentile", "run_percentile"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "evaluate_main_segment_profile",
        "description": "Evaluate swim, bike, and run marginal percentiles, SBR joint percentile, estimated total percentile, and weakest/strongest main segment.",
        "required": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "full_split_evaluation",
        "description": "Alias for evaluate_main_segment_profile. Evaluate swim, bike, and run marginal percentiles, SBR joint percentile, estimated total percentile, and weakest/strongest main segment.",
        "required": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "find_weakest_main_segment",
        "description": "Find the weakest main segment among swim, bike, and run.",
        "required": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "swim_time", "bike_time", "run_time"),
        "do_not_infer": ("sex_category", "age_group"),
    },
    {
        "name": "compare_segment_scenarios",
        "description": "Compare current and target times for one segment.",
        "required": (*COMMON_REQUIRED, "segment", "current_time", "target_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "segment", "current_time", "target_time"),
        "do_not_infer": ("sex_category", "age_group", "segment"),
    },
    {
        "name": "explain_percentile",
        "description": "Explain what a percentile means without performing a new lookup.",
        "required": ("percentile",),
        "clarify_if_missing": ("percentile",),
        "do_not_infer": (),
        "optional": ("scope", "segment"),
    },
    {
        "name": "conditional_segment_percentile",
        "description": "Return a conditional target segment percentile for a provided target segment time using Bayes over cumulative joint performance distributions. Supports one or two conditioning segments with at_least_as_good, slower_than, or between interval conditions.",
        "required": (*COMMON_REQUIRED, "target_segment", "target_time", "condition_1_segment", "condition_1_time"),
        "clarify_if_missing": (*COMMON_REQUIRED, "target_segment", "target_time", "condition_1_segment", "condition_1_time"),
        "do_not_infer": ("sex_category", "age_group", "target_segment"),
        "optional": (
            "condition_1_operator",
            "condition_1_lower_time",
            "condition_1_upper_time",
            "condition_2_segment",
            "condition_2_time",
            "condition_2_operator",
            "condition_2_lower_time",
            "condition_2_upper_time",
        ),
        "examples": [
            {
                "user_request": "What is my Bike percentile among athletes who swim between 24:00 and 25:00 and run between 47:00 and 50:00 if I bike 1:10:00?",
                "payload": {
                    "intent": "conditional_segment_percentile",
                    "modality": "Standard",
                    "sex_category": "O",
                    "age_group": "40-44",
                    "target_segment": "Bike",
                    "target_time": "1:10:00",
                    "condition_1_segment": "Swim",
                    "condition_1_operator": "between",
                    "condition_1_lower_time": "24:00",
                    "condition_1_upper_time": "25:00",
                    "condition_2_segment": "Run",
                    "condition_2_operator": "between",
                    "condition_2_lower_time": "47:00",
                    "condition_2_upper_time": "50:00",
                },
            },
            {
                "user_request": "Evaluate my Bike time of 1:23:00 among athletes who swim faster than 32:00 and run faster than 1:00:00.",
                "payload": {
                    "intent": "conditional_segment_percentile",
                    "target_segment": "Bike",
                    "target_time": "1:23:00",
                    "condition_1_segment": "Swim",
                    "condition_1_operator": "at_least_as_good",
                    "condition_1_time": "32:00",
                    "condition_2_segment": "Run",
                    "condition_2_operator": "at_least_as_good",
                    "condition_2_time": "1:00:00",
                },
            },
        ],
    },
)


def get_tool_schema() -> dict[str, Any]:
    return {
        "global_rules": list(GLOBAL_RULES),
        "tools": deepcopy(list(AVAILABLE_TOOLS)),
    }


def get_tool_spec(name: str) -> dict[str, Any]:
    for tool in AVAILABLE_TOOLS:
        if tool["name"] == name:
            return deepcopy(tool)
    valid = ", ".join(tool["name"] for tool in AVAILABLE_TOOLS)
    raise ValueError(f"Unknown tool {name!r}. Expected one of: {valid}")


def required_fields_for_intent(intent: str) -> tuple[str, ...]:
    return tuple(get_tool_spec(intent)["required"])


def missing_required_fields(payload: dict[str, Any]) -> list[str]:
    intent = payload.get("intent")
    if not intent:
        return ["intent"]
    if intent == "conditional_segment_percentile":
        missing = [field for field in COMMON_REQUIRED if payload.get(field) is None]
        missing.extend(field for field in ("target_segment", "target_time", "condition_1_segment") if payload.get(field) is None)
        has_threshold = payload.get("condition_1_time") is not None
        has_interval = payload.get("condition_1_lower_time") is not None and payload.get("condition_1_upper_time") is not None
        if not has_threshold and not has_interval:
            missing.append("condition_1_time")
        return missing
    required = required_fields_for_intent(str(intent))
    return [field for field in required if payload.get(field) is None]
