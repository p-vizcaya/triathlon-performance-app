from __future__ import annotations

from typing import Any

from .tool_schema import GLOBAL_RULES, get_tool_schema, missing_required_fields


class ParserContractError(ValueError):
    """Raised when an LLM parser output violates the contract."""


ALLOWED_OUTPUT_TYPES = ("tool_payload", "clarification")


def parser_system_prompt() -> str:
    schema = get_tool_schema()
    tool_lines = []
    for tool in schema["tools"]:
        required = ", ".join(tool["required"])
        tool_lines.append(f"- {tool['name']}: {tool['description']} Required fields: {required}.")

    rules = "\n".join(f"- {rule}" for rule in GLOBAL_RULES)
    tools = "\n".join(tool_lines)
    return (
        "You parse triathlon performance questions into structured JSON.\n"
        "You do not calculate percentiles, times, or rankings. You only select an approved intent and fields.\n\n"
        "Rules:\n"
        f"{rules}\n\n"
        "Approved intents:\n"
        f"{tools}\n\n"
        "Return exactly one JSON object in one of these forms:\n"
        '{ "type": "tool_payload", "payload": { "intent": "...", "...": "..." } }\n'
        "or\n"
        '{ "type": "clarification", "missing_fields": ["..."], "question": "..." }\n\n'
        "When constrained by a strict schema, set unused fields to null.\n"
        "If a required field is missing or ambiguous, return clarification. "
        "Do not infer sex category, age group, or segment when ambiguous. "
        "If the user gives sport units, preserve them as the relevant time field string: "
        "Swim pace like 1:40/100m goes in swim_time or segment_time for Swim; Bike speed like "
        "32 km/h goes in bike_time or segment_time for Bike; Run pace like 5:00/km goes in "
        "run_time or segment_time for Run. The deterministic engine converts them by modality. "
        "Distinguish top X% from top N. Interpret top X% as performance percentile 100-X; "
        "for example, top 10% means P90, not P10. Interpret top N out of M, top N among M, "
        "or top N in M as performance percentile 100*(1-N/M); for example, top 10 among 200 "
        "means top 5%, therefore P95. If the user asks for top N without a percentage or field size, "
        "ask for the total number of athletes in the category. "
        "For conditional profile questions, use conditional_segment_percentile. Conditions are cumulative "
        "thresholds: 'swim better than 32:00' means athletes with Swim performance at least as good as 32:00, "
        "not athletes exactly equal to 32:00. For 'slower than' conditions, set condition_1_operator to "
        "'slower_than'. For 'between X and Y' conditions, set condition_1_operator to 'between', "
        "condition_1_lower_time to X, condition_1_upper_time to Y, and condition_1_time to null. "
        "The conditional_segment_percentile intent supports one or two conditioning segments. "
        "For target phrasing like 'if I bike 1:10:00' or 'evaluate my Bike time of 1:23:00', "
        "set target_segment to Bike and target_time to the provided bike time. "
        "Do not ask for target_time when the user already provided the evaluated segment time. "
        "If the user asks which part, split, segment, transition, strongest, or weakest, and provides T1/T2 "
        "or multiple split times, use compare_segments. Do not use full_split_evaluation for that question."
    )


def validate_parsed_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        raise ParserContractError("Parsed output must be a dictionary")
    output_type = parsed.get("type")
    if output_type not in ALLOWED_OUTPUT_TYPES:
        raise ParserContractError("Parsed output must have type 'tool_payload' or 'clarification'")

    if output_type == "clarification":
        missing_fields = parsed.get("missing_fields")
        question = parsed.get("question")
        if not isinstance(missing_fields, list) or not all(isinstance(item, str) for item in missing_fields):
            raise ParserContractError("Clarification output requires missing_fields as a list of strings")
        if not isinstance(question, str) or not question.strip():
            raise ParserContractError("Clarification output requires a non-empty question")
        return {
            "type": "clarification",
            "missing_fields": missing_fields,
            "question": question.strip(),
        }

    payload = parsed.get("payload")
    if not isinstance(payload, dict):
        raise ParserContractError("tool_payload output requires payload as a dictionary")
    missing = missing_required_fields(payload)
    if missing:
        return {
            "type": "clarification",
            "missing_fields": missing,
            "question": "Please provide: " + ", ".join(missing) + ".",
        }
    return {
        "type": "tool_payload",
        "payload": payload,
    }


def build_parser_messages(user_text: str, context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    context_text = ""
    if context:
        context_text = "\nContext JSON:\n" + str(context)
    return [
        {"role": "system", "content": parser_system_prompt()},
        {"role": "user", "content": user_text + context_text},
    ]
