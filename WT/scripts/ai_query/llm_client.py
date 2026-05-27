from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable

from .normalization import normalize_age_group, normalize_modality, normalize_sex_category
from .parser_contract import build_parser_messages, validate_parsed_payload
from .query_agent import run_query_agent


DEFAULT_MODEL = "gpt-5-nano"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class LLMClientError(RuntimeError):
    """Raised when the LLM parser call cannot be completed."""


Transport = Callable[[dict[str, Any]], dict[str, Any]]


PARSER_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["type", "payload", "missing_fields", "question"],
    "properties": {
        "type": {"type": "string", "enum": ["tool_payload", "clarification"]},
        "payload": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "intent",
                "modality",
                "sex_category",
                "age_group",
                "segment",
                "scope",
                "missing_segment",
                "pair",
                "total_time",
                "segment_time",
                "swim_time",
                "t1_time",
                "bike_time",
                "t2_time",
                "run_time",
                "x_time",
                "y_time",
                "current_time",
                "target_time",
                "target_total_time",
                "percentile",
                "target_percentile",
                "target_segment",
                "condition_1_segment",
                "condition_1_time",
                "condition_1_operator",
                "condition_1_lower_time",
                "condition_1_upper_time",
                "condition_2_segment",
                "condition_2_time",
                "condition_2_operator",
                "condition_2_lower_time",
                "condition_2_upper_time",
                "x_percentile",
                "y_percentile",
                "swim_percentile",
                "bike_percentile",
                "run_percentile",
            ],
            "properties": {
                "intent": {"type": ["string", "null"]},
                "modality": {"type": ["string", "null"]},
                "sex_category": {"type": ["string", "null"]},
                "age_group": {"type": ["string", "null"]},
                "segment": {"type": ["string", "null"]},
                "scope": {"type": ["string", "null"]},
                "missing_segment": {"type": ["string", "null"]},
                "pair": {"type": ["string", "null"]},
                "total_time": {"type": ["string", "null"]},
                "segment_time": {"type": ["string", "null"]},
                "swim_time": {"type": ["string", "null"]},
                "t1_time": {"type": ["string", "null"]},
                "bike_time": {"type": ["string", "null"]},
                "t2_time": {"type": ["string", "null"]},
                "run_time": {"type": ["string", "null"]},
                "x_time": {"type": ["string", "null"]},
                "y_time": {"type": ["string", "null"]},
                "current_time": {"type": ["string", "null"]},
                "target_time": {"type": ["string", "null"]},
                "target_total_time": {"type": ["string", "null"]},
                "percentile": {"type": ["number", "null"]},
                "target_percentile": {"type": ["number", "null"]},
                "target_segment": {"type": ["string", "null"]},
                "condition_1_segment": {"type": ["string", "null"]},
                "condition_1_time": {"type": ["string", "null"]},
                "condition_1_operator": {"type": ["string", "null"]},
                "condition_1_lower_time": {"type": ["string", "null"]},
                "condition_1_upper_time": {"type": ["string", "null"]},
                "condition_2_segment": {"type": ["string", "null"]},
                "condition_2_time": {"type": ["string", "null"]},
                "condition_2_operator": {"type": ["string", "null"]},
                "condition_2_lower_time": {"type": ["string", "null"]},
                "condition_2_upper_time": {"type": ["string", "null"]},
                "x_percentile": {"type": ["number", "null"]},
                "y_percentile": {"type": ["number", "null"]},
                "swim_percentile": {"type": ["number", "null"]},
                "bike_percentile": {"type": ["number", "null"]},
                "run_percentile": {"type": ["number", "null"]},
            },
        },
        "missing_fields": {
            "type": ["array", "null"],
            "items": {"type": "string"},
        },
        "question": {"type": ["string", "null"]},
    },
}


def _model_name(model: str | None = None) -> str:
    return model or os.getenv("AI_QUERY_MODEL", DEFAULT_MODEL)


def _api_key(api_key: str | None = None) -> str:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise LLMClientError("OPENAI_API_KEY is required for live LLM parsing")
    return key


def _responses_payload(user_text: str, context: dict[str, Any] | None, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "input": build_parser_messages(user_text, context),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "triathlon_query_parser",
                "strict": True,
                "schema": PARSER_RESPONSE_SCHEMA,
            }
        },
    }


def _post_openai_responses(payload: dict[str, Any], *, api_key: str | None = None, timeout: int = 30) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {_api_key(api_key)}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMClientError(f"OpenAI API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMClientError(f"OpenAI API request failed: {exc}") from exc


def _extract_response_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    output = response.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            content = item.get("content") if isinstance(item, dict) else None
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        if chunks:
            return "".join(chunks)
    raise LLMClientError("OpenAI response did not contain parsable output text")


def _parse_json_text(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMClientError(f"LLM parser returned invalid JSON: {text}") from exc
    if not isinstance(parsed, dict):
        raise LLMClientError("LLM parser JSON must be an object")
    return parsed


def _strip_nulls(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_nulls(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_strip_nulls(item) for item in value]
    return value


def _apply_percentile_language_conventions(parsed: dict[str, Any], user_text: str) -> dict[str, Any]:
    if parsed.get("type") != "tool_payload":
        return parsed
    payload = parsed.get("payload")
    if not isinstance(payload, dict):
        return parsed
    if "target_percentile" not in payload and "percentile" not in payload:
        return parsed

    text = user_text.lower()
    top_percent = re.search(r"\btop\s+(\d+(?:\.\d+)?)\s*%", text)
    if top_percent:
        percentile = 100 - float(top_percent.group(1))
    else:
        top_count = re.search(r"\btop\s+(\d+(?:\.\d+)?)\s+(?:in|of|out of|among|within)\s+(\d+(?:\.\d+)?)\b", text)
        if not top_count:
            return parsed
        numerator = float(top_count.group(1))
        denominator = float(top_count.group(2))
        if denominator <= 0:
            return parsed
        percentile = 100 * (1 - numerator / denominator)

    percentile = max(0.0, min(100.0, percentile))
    payload = dict(payload)
    if "target_percentile" in payload:
        payload["target_percentile"] = percentile
    elif "percentile" in payload:
        payload["percentile"] = percentile
    return {**parsed, "payload": payload}


def _apply_intent_conventions(parsed: dict[str, Any], user_text: str) -> dict[str, Any]:
    if parsed.get("type") != "tool_payload":
        return parsed
    payload = parsed.get("payload")
    if not isinstance(payload, dict):
        return parsed
    text = user_text.lower()
    asks_split_comparison = (
        re.search(r"\b(strongest|weakest|best|worst)\b", text)
        and re.search(r"\b(part|split|segment|transition|t1|t2)\b", text)
    )
    has_transition_values = re.search(r"\bt1\b", text) or re.search(r"\bt2\b", text)
    if asks_split_comparison and has_transition_values:
        payload = dict(payload)
        payload["intent"] = "compare_segments"
        return {**parsed, "payload": payload}
    if payload.get("intent") == "conditional_segment_percentile":
        payload = _apply_conditional_language_conventions(dict(payload), user_text)
        return {**parsed, "payload": payload}
    return parsed


def _apply_conditional_language_conventions(payload: dict[str, Any], user_text: str) -> dict[str, Any]:
    text = user_text.lower()
    if re.search(r"\bslower\s+than\b|\bworse\s+than\b", text):
        payload["condition_1_operator"] = "slower_than"
    elif re.search(r"\bfaster\s+than\b|\bbetter\s+than\b", text):
        payload["condition_1_operator"] = "at_least_as_good"

    between = re.search(
        r"\b(?:between|from)\s+(\d{1,2}:\d{2}(?::\d{2})?)\s+(?:and|to|-)\s+(\d{1,2}:\d{2}(?::\d{2})?)\b",
        text,
    )
    compact_interval = None
    condition_time = payload.get("condition_1_time")
    if isinstance(condition_time, str):
        compact_interval = re.match(
            r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*$",
            condition_time,
        )
    interval = between or compact_interval
    if interval:
        payload["condition_1_operator"] = "between"
        payload["condition_1_lower_time"] = interval.group(1)
        payload["condition_1_upper_time"] = interval.group(2)
        payload["condition_1_time"] = None
    return payload


def _requires_top_count_clarification(user_text: str) -> dict[str, Any] | None:
    text = user_text.lower()
    if re.search(r"\btop\s+\d+(?:\.\d+)?\s*%", text):
        return None
    if re.search(r"\btop\s+\d+(?:\.\d+)?\s+(?:in|of|out of|among|within)\s+\d+(?:\.\d+)?\b", text):
        return None
    if re.search(r"\btop\s+\d+(?:\.\d+)?\b", text):
        return {
            "type": "clarification",
            "missing_fields": ["field_size"],
            "question": "Please provide the total number of athletes in the category so I can convert the top-N target into a percentile.",
        }
    return None


def _requires_unsupported_conditional_inverse(user_text: str) -> dict[str, Any] | None:
    text = user_text.lower()
    has_condition_context = bool(
        re.search(r"\b(among|condition(?:al|ed)?|comparable|whose|with)\b", text)
        and re.search(r"\b(swim|bike|run|athletes?|runners?|swimmers?|bikers?)\b", text)
    )
    asks_inverse_time = bool(
        re.search(r"\bwhat\s+(?:swim|bike|run|total)?\s*time\b", text)
        or re.search(r"\b(?:swim|bike|run|total)\s+time\s+(?:corresponds|would|should|needed|target)\b", text)
        or re.search(r"\b(?:swim|bike|run|total)\s+split\s+(?:corresponds|would|should|needed|target)\b", text)
        or re.search(r"\bwhat\s+(?:swim|bike|run|total)?\s*split\b", text)
    )
    has_target_percentile = bool(
        re.search(r"\bp\s*\d+(?:\.\d+)?\b", text)
        or re.search(r"\bmedian\b", text)
        or re.search(r"\btop\s+\d+(?:\.\d+)?\s*%", text)
        or re.search(r"\bbeat\s+\d+(?:\.\d+)?\s*%", text)
        or re.search(r"\bahead\s+of\s+\d+(?:\.\d+)?\s*%", text)
    )
    if has_condition_context and asks_inverse_time and has_target_percentile:
        return {
            "type": "unsupported",
            "reason": "conditional_inverse_time",
            "message": (
                "Conditional inverse time queries are not supported. The tables can directly answer a "
                "conditional percentile for a provided time, but not the time corresponding to a target "
                "conditional percentile."
            ),
        }
    return None


def _requires_around_clarification(user_text: str) -> dict[str, Any] | None:
    text = user_text.lower()
    if "around" not in text:
        return None
    if not re.search(r"\b(among|condition(?:al|ed)?|comparable|whose|with)\b", text):
        return None
    if not re.search(r"\b(swim|bike|run)\b", text):
        return None
    return {
        "type": "clarification",
        "missing_fields": ["condition_window"],
        "question": (
            "Please specify the time window for each 'around' condition, for example "
            "Swim between 39:30 and 40:30 and Run between 1:04:00 and 1:06:00."
        ),
    }


def _parse_common_context(user_text: str) -> dict[str, str] | None:
    modality_match = re.search(r"\b(Standard|Sprint)\b", user_text, re.IGNORECASE)
    age_match = re.search(r"\b(\d{2}-\d{2})\b", user_text)
    sex_match = re.search(r"\b(F|O|Open|Female|Male)\b", user_text, re.IGNORECASE)
    if not (modality_match and age_match and sex_match):
        return None
    return {
        "modality": normalize_modality(modality_match.group(1)),
        "sex_category": normalize_sex_category(sex_match.group(1)),
        "age_group": normalize_age_group(age_match.group(1)),
    }


def _time_pattern() -> str:
    return r"\d{1,2}:\d{2}(?::\d{2})?"


def _deterministic_conditional_percentile(user_text: str) -> dict[str, Any] | None:
    text = user_text.lower()
    if not re.search(r"\b(among|whose|who|with)\b", text):
        return None
    if not re.search(r"\b(percentile|evaluate|how good)\b", text):
        return None
    context = _parse_common_context(user_text)
    if context is None:
        return None

    time_re = _time_pattern()
    target_patterns = [
        rf"\b(?:evaluate\s+my|what\s+is\s+my)\s+(swim|bike|run)(?:\s+(?:time|split))?(?:\s+of)?\s+({time_re})\b",
        rf"\bhow\s+good\s+is\s+(?:a|my)?\s*({time_re})\s+(swim|bike|run)(?:\s+split)?\b",
        rf"\bif\s+i\s+(swim|bike|run)\s+({time_re})\b",
    ]
    target_segment = None
    target_time = None
    for pattern in target_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        if re.match(time_re, match.group(1)):
            target_time = match.group(1)
            target_segment = match.group(2)
        else:
            target_segment = match.group(1)
            target_time = match.group(2)
        break
    if not target_segment or not target_time:
        return None

    conditions: list[dict[str, str | None]] = []
    for match in re.finditer(rf"\b(swim|bike|run)\s+between\s+({time_re})\s+(?:and|to|-)\s+({time_re})\b", text):
        conditions.append(
            {
                "segment": match.group(1),
                "operator": "between",
                "time": None,
                "lower_time": match.group(2),
                "upper_time": match.group(3),
            }
        )
    for match in re.finditer(rf"\b(swim|bike|run)\s+faster\s+than\s+({time_re})\b", text):
        conditions.append(
            {
                "segment": match.group(1),
                "operator": "at_least_as_good",
                "time": match.group(2),
                "lower_time": None,
                "upper_time": None,
            }
        )
    conditions = [condition for condition in conditions if condition["segment"] != target_segment]
    if not conditions:
        return None
    conditions = conditions[:2]

    payload: dict[str, Any] = {
        "intent": "conditional_segment_percentile",
        **context,
        "target_segment": target_segment.title(),
        "target_time": target_time,
        "condition_1_segment": str(conditions[0]["segment"]).title(),
        "condition_1_operator": conditions[0]["operator"],
        "condition_1_time": conditions[0]["time"],
        "condition_1_lower_time": conditions[0]["lower_time"],
        "condition_1_upper_time": conditions[0]["upper_time"],
    }
    if len(conditions) > 1:
        payload.update(
            {
                "condition_2_segment": str(conditions[1]["segment"]).title(),
                "condition_2_operator": conditions[1]["operator"],
                "condition_2_time": conditions[1]["time"],
                "condition_2_lower_time": conditions[1]["lower_time"],
                "condition_2_upper_time": conditions[1]["upper_time"],
            }
        )
    return {"type": "tool_payload", "payload": payload}


def _deterministic_sbr_joint(user_text: str) -> dict[str, Any] | None:
    text = user_text.lower()
    if not re.search(r"\bjoint\s+swim[- ]bike[- ]run\s+percentile\b", text):
        return None
    context = _parse_common_context(user_text)
    if context is None:
        return None
    time_re = _time_pattern()
    swim = re.search(rf"\bswim\s+({time_re})\b", text)
    bike = re.search(rf"\bbike\s+({time_re})\b", text)
    run = re.search(rf"\brun\s+({time_re})\b", text)
    if not (swim and bike and run):
        return None
    return {
        "type": "tool_payload",
        "payload": {
            "intent": "sbr_percentile_by_segment_times",
            **context,
            "swim_time": swim.group(1),
            "bike_time": bike.group(1),
            "run_time": run.group(1),
        },
    }


def _conceptual_response(user_text: str) -> dict[str, Any] | None:
    text = user_text.lower()
    if "marginal run percentile" in text and "conditional" in text:
        return {
            "type": "conceptual",
            "message": (
                "A marginal Run percentile ranks a run time against the full reference group. "
                "A conditional Run percentile ranks that same run only within a subgroup, such as athletes "
                "whose Swim is at least as good as a threshold or within a stated interval."
            ),
        }
    if "conditional run percentile" in text and "joint swim-run" in text and "coaching" in text:
        return {
            "type": "conceptual",
            "message": (
                "A joint Swim-Run percentile measures how rare the combined event is, so it can be low even "
                "when one segment is solid. For coaching, the conditional Run percentile is more actionable "
                "because it asks how the run compares among athletes with similar swim ability."
            ),
        }
    if "p70" in text and "p45" in text and "swim like me" in text:
        return {
            "type": "conceptual",
            "message": (
                "It means the run looks strong in the full field, but weaker among athletes with comparable "
                "swim performance. In practical terms, the athlete may be a good runner overall while still "
                "underperforming relative to peers who exit the water in a similar position."
            ),
        }
    if "evaluate my bike" in text and "similar swim and run" in text:
        return {
            "type": "conceptual",
            "message": (
                "It means ranking the Bike split inside a subgroup defined by comparable Swim and Run "
                "performance. The result is a conditional Bike percentile: it answers whether the bike leg is "
                "strong or weak relative to athletes with a similar surrounding race profile."
            ),
        }
    if "total-time percentile" in text and "conditional run percentile" in text:
        return {
            "type": "conceptual",
            "message": (
                "A high total-time percentile can coexist with a low conditional Run percentile when Swim, Bike, "
                "or transitions are strong enough to lift the total result. The conditional Run percentile isolates "
                "whether the run is strong among comparable athletes, so it can reveal a segment-specific weakness."
            ),
        }
    if "among comparable athletes" in text:
        return {
            "type": "conceptual",
            "message": (
                "Among comparable athletes means the reference group is restricted by one or two conditions, "
                "such as Swim between two times or Bike at least as good as a threshold. The percentile then "
                "describes performance within that subgroup, not within the whole age-group table."
            ),
        }
    if "joint swim-run percentile" in text and "conditional" in text and "actionable" in text:
        return {
            "type": "conceptual",
            "message": (
                "The joint percentile describes the probability of meeting both Swim and Run thresholds together. "
                "The conditional interpretation is usually more actionable: it asks how the Run ranks among athletes "
                "with a comparable Swim, which points more directly to segment strengths and weaknesses."
            ),
        }
    return None


def parse_natural_language_query(
    user_text: str,
    context: dict[str, Any] | None = None,
    *,
    model: str | None = None,
    transport: Transport | None = None,
    api_key: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    conceptual = _conceptual_response(user_text)
    if conceptual:
        return conceptual
    unsupported = _requires_unsupported_conditional_inverse(user_text)
    if unsupported:
        return unsupported
    around_clarification = _requires_around_clarification(user_text)
    if around_clarification:
        return validate_parsed_payload(around_clarification)
    top_count_clarification = _requires_top_count_clarification(user_text)
    if top_count_clarification:
        return validate_parsed_payload(top_count_clarification)
    deterministic = _deterministic_conditional_percentile(user_text)
    if deterministic:
        return validate_parsed_payload(deterministic)
    deterministic_sbr = _deterministic_sbr_joint(user_text)
    if deterministic_sbr:
        return validate_parsed_payload(deterministic_sbr)
    payload = _responses_payload(user_text, context, _model_name(model))
    response = transport(payload) if transport else _post_openai_responses(payload, api_key=api_key, timeout=timeout)
    parsed = _strip_nulls(_parse_json_text(_extract_response_text(response)))
    parsed = _apply_percentile_language_conventions(parsed, user_text)
    parsed = _apply_intent_conventions(parsed, user_text)
    return validate_parsed_payload(parsed)


def answer_natural_language_query(
    user_text: str,
    context: dict[str, Any] | None = None,
    *,
    model: str | None = None,
    transport: Transport | None = None,
    api_key: str | None = None,
    include_result: bool = True,
    timeout: int = 30,
) -> dict[str, Any]:
    parsed = parse_natural_language_query(
        user_text,
        context,
        model=model,
        transport=transport,
        api_key=api_key,
        timeout=timeout,
    )
    if parsed["type"] == "clarification":
        return {
            "valid": False,
            "needs_clarification": True,
            "missing_fields": parsed["missing_fields"],
            "message": parsed["question"],
            "parsed": parsed,
        }
    if parsed["type"] == "unsupported":
        return {
            "valid": False,
            "needs_clarification": False,
            "reason": parsed["reason"],
            "message": parsed["message"],
            "parsed": parsed,
        }
    if parsed["type"] == "conceptual":
        return {
            "valid": True,
            "needs_clarification": False,
            "intent": "conceptual_explanation",
            "explanation": parsed["message"],
            "message": parsed["message"],
            "parsed": parsed,
        }

    agent_response = run_query_agent(parsed["payload"], include_result=include_result)
    return {
        **agent_response,
        "parsed": parsed,
    }
