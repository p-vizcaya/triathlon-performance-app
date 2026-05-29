from __future__ import annotations

from typing import Any

from .explain import explain_result
from .orchestrator import (
    compare_segment_scenarios,
    evaluate_full_split_profile,
    evaluate_main_segment_profile,
    explain_profile_result,
    find_weakest_main_segment,
)
from .router import route_query
from .tool_schema import get_tool_spec, missing_required_fields


ORCHESTRATED_INTENTS = {
    "evaluate_main_segment_profile",
    "full_split_evaluation",
    "find_weakest_main_segment",
    "compare_segments",
    "compare_segment_scenarios",
}


def _clarification_response(payload: dict[str, Any], missing: list[str]) -> dict[str, Any]:
    intent = payload.get("intent")
    question = "Please provide: " + ", ".join(missing) + "."
    if intent:
        try:
            spec = get_tool_spec(str(intent))
            question = (
                f"To run {intent}, please provide: "
                f"{', '.join(spec.get('clarify_if_missing', missing))}."
            )
        except ValueError:
            pass
    return {
        "valid": False,
        "needs_clarification": True,
        "intent": intent,
        "missing_fields": missing,
        "clarification_question": question,
        "message": question,
    }


def _orchestrated_call(payload: dict[str, Any]) -> dict[str, Any]:
    intent = payload["intent"]
    if intent == "evaluate_main_segment_profile":
        return evaluate_main_segment_profile(
            payload["modality"],
            payload["sex_category"],
            payload["age_group"],
            payload["swim_time"],
            payload["bike_time"],
            payload["run_time"],
        )
    if intent == "full_split_evaluation":
        return evaluate_full_split_profile(
            payload["modality"],
            payload["sex_category"],
            payload["age_group"],
            payload["swim_time"],
            payload["t1_time"],
            payload["bike_time"],
            payload["t2_time"],
            payload["run_time"],
            total_time=payload.get("total_time"),
        )
    if intent == "find_weakest_main_segment":
        return find_weakest_main_segment(
            payload["modality"],
            payload["sex_category"],
            payload["age_group"],
            payload["swim_time"],
            payload["bike_time"],
            payload["run_time"],
        )
    if intent == "compare_segment_scenarios":
        return compare_segment_scenarios(
            payload["modality"],
            payload["sex_category"],
            payload["age_group"],
            payload["segment"],
            payload["current_time"],
            payload["target_time"],
        )
    if intent == "compare_segments":
        from .analysis_intents import compare_segments

        return compare_segments(
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
    raise ValueError(f"Unsupported orchestrated intent: {intent}")


def run_query_agent(payload: dict[str, Any], *, include_result: bool = True) -> dict[str, Any]:
    missing = missing_required_fields(payload)
    if missing:
        return _clarification_response(payload, missing)

    intent = str(payload["intent"])
    if intent in ORCHESTRATED_INTENTS:
        result = _orchestrated_call(payload)
        explanation = explain_profile_result(result) if intent == "evaluate_main_segment_profile" else result.get("summary")
        if not explanation and isinstance(result, dict):
            explanation = result.get("message")
    else:
        result = route_query(payload, explain=False)
        explanation = explain_result(result)

    response = {
        "valid": bool(result.get("valid", True)),
        "needs_clarification": False,
        "intent": intent,
        "explanation": explanation,
    }
    if not response["valid"]:
        response["message"] = result.get("message", explanation)
        response["reason"] = result.get("reason")
    if include_result:
        response["result"] = result
    return response


def run_query_plan_agent(plan: list[dict[str, Any]]) -> dict[str, Any]:
    responses = []
    for index, payload in enumerate(plan, start=1):
        response = run_query_agent(payload)
        responses.append({"step": index, "response": response})
        if response.get("needs_clarification") or not response.get("valid", True):
            return {
                "valid": False,
                "needs_clarification": bool(response.get("needs_clarification")),
                "failed_step": index,
                "responses": responses,
                "message": response.get("message") or response.get("clarification_question"),
            }
    return {
        "valid": True,
        "needs_clarification": False,
        "responses": responses,
        "explanations": [item["response"]["explanation"] for item in responses],
    }
