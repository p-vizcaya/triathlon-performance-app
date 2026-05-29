from __future__ import annotations

from typing import Any

from .explain import round_percentile
from .lookups_1d import get_segment_percentile_by_time
from .lookups_2d import get_pair_percentile_by_segment_percentiles
from .lookups_3d import get_sbr_percentile_by_segment_percentiles
from .normalization import normalize_age_group, normalize_modality, normalize_segment, normalize_sex_category, parse_segment_time_to_seconds


PAIR_BY_SEGMENTS = {
    frozenset(("Swim", "Bike")): "swim_bike",
    frozenset(("Swim", "Run")): "swim_run",
    frozenset(("Bike", "Run")): "bike_run",
}


def _marginal_percentile(modality: str, sex_label: str, age_group: str, segment: str, time_value: Any) -> float:
    result = get_segment_percentile_by_time(modality, sex_label, age_group, segment, time_value)
    if not result.get("entity") == "segment_curve":
        raise ValueError(result.get("message", "Could not calculate marginal percentile"))
    return float(result["performance_percentile"])


def _pair_joint(
    modality: str,
    sex_label: str,
    age_group: str,
    first_segment: str,
    first_percentile: float,
    second_segment: str,
    second_percentile: float,
) -> dict[str, Any]:
    pair = PAIR_BY_SEGMENTS[frozenset((first_segment, second_segment))]
    ordered = pair.split("_")
    x_segment = ordered[0].title()
    y_segment = ordered[1].title()
    percentile_by_segment = {
        first_segment: first_percentile,
        second_segment: second_percentile,
    }
    return get_pair_percentile_by_segment_percentiles(
        modality,
        sex_label,
        age_group,
        pair,
        percentile_by_segment[x_segment],
        percentile_by_segment[y_segment],
    )


def conditional_segment_percentile_from_joint(
    modality: Any,
    sex_category: Any,
    age_group: Any,
    target_segment: Any,
    target_time: Any,
    condition_1_segment: Any,
    condition_1_time: Any,
    condition_2_segment: Any | None = None,
    condition_2_time: Any | None = None,
    condition_1_operator: Any | None = None,
    condition_1_lower_time: Any | None = None,
    condition_1_upper_time: Any | None = None,
    condition_2_operator: Any | None = None,
    condition_2_lower_time: Any | None = None,
    condition_2_upper_time: Any | None = None,
) -> dict[str, Any]:
    modality = normalize_modality(modality)
    sex_label = normalize_sex_category(sex_category, field="sex_label")
    age_group = normalize_age_group(age_group)
    target_segment = normalize_segment(target_segment)
    condition_1_segment = normalize_segment(condition_1_segment)
    condition_segments = [condition_1_segment]
    condition_specs = [
        {
            "operator": _normalize_condition_operator(condition_1_operator),
            "time": condition_1_time,
            "lower_time": condition_1_lower_time,
            "upper_time": condition_1_upper_time,
        }
    ]
    if condition_2_segment is not None or condition_2_time is not None or condition_2_lower_time is not None or condition_2_upper_time is not None:
        has_condition_2_threshold = condition_2_time is not None
        has_condition_2_interval = condition_2_lower_time is not None and condition_2_upper_time is not None
        if condition_2_segment is None or not (has_condition_2_threshold or has_condition_2_interval):
            return {
                "valid": False,
                "entity": "conditional_segment_percentile",
                "reason": "incomplete_condition",
                "message": "Second conditions require condition_2_segment plus either condition_2_time or interval bounds.",
            }
        condition_segments.append(normalize_segment(condition_2_segment))
        condition_specs.append(
            {
                "operator": _normalize_condition_operator(condition_2_operator),
                "time": condition_2_time,
                "lower_time": condition_2_lower_time,
                "upper_time": condition_2_upper_time,
            }
        )

    allowed = {"Swim", "Bike", "Run"}
    all_segments = [target_segment, *condition_segments]
    if any(segment not in allowed for segment in all_segments):
        return {
            "valid": False,
            "entity": "conditional_segment_percentile",
            "reason": "unsupported_segment",
            "message": "Conditional profiles from joint distributions currently support Swim, Bike, and Run only.",
        }
    if target_segment in condition_segments:
        return {
            "valid": False,
            "entity": "conditional_segment_percentile",
            "reason": "target_in_conditions",
            "message": "The target segment must be different from the conditioning segment or segments.",
        }
    if len(set(condition_segments)) != len(condition_segments):
        return {
            "valid": False,
            "entity": "conditional_segment_percentile",
            "reason": "duplicate_conditions",
            "message": "Condition segments must be distinct.",
        }
    if len(condition_segments) > 2:
        return {
            "valid": False,
            "entity": "conditional_segment_percentile",
            "reason": "too_many_conditions",
            "message": "This version supports one or two cumulative conditions.",
        }

    try:
        target_percentile = _marginal_percentile(modality, sex_label, age_group, target_segment, target_time)
        parsed_conditions = [
            _condition_event(modality, sex_label, age_group, segment, spec)
            for segment, spec in zip(condition_segments, condition_specs)
        ]
    except ValueError as exc:
        return {
            "valid": False,
            "entity": "conditional_segment_percentile",
            "reason": "outside_empirical_range",
            "message": str(exc),
        }
    invalid_condition = next((condition for condition in parsed_conditions if not condition.get("valid", True)), None)
    if invalid_condition:
        return invalid_condition

    try:
        if len(condition_segments) == 1:
            numerator_probability, denominator_probability = _single_condition_probabilities(
                modality,
                sex_label,
                age_group,
                target_segment,
                target_percentile,
                condition_segments[0],
                parsed_conditions[0],
            )
        else:
            numerator_probability, denominator_probability = _two_condition_probabilities(
                modality,
                sex_label,
                age_group,
                target_segment,
                target_percentile,
                condition_segments[0],
                condition_segments[1],
                parsed_conditions[0],
                parsed_conditions[1],
            )
    except ValueError as exc:
        return {
            "valid": False,
            "entity": "conditional_segment_percentile",
            "reason": "outside_empirical_range",
            "message": str(exc),
            "conditions": parsed_conditions,
        }

    if denominator_probability <= 0:
        return {
            "valid": False,
            "entity": "conditional_segment_percentile",
            "reason": "zero_denominator",
            "message": "The conditioning event has zero probability in the joint table.",
            "conditions": parsed_conditions,
        }

    conditional_percentile = 100 * numerator_probability / denominator_probability
    conditional_percentile = max(0.0, min(100.0, conditional_percentile))
    given_text = " and ".join(_condition_text(condition) for condition in parsed_conditions)
    return {
        "valid": True,
        "entity": "conditional_segment_percentile",
        "modality": modality,
        "sex_label": sex_label,
        "age_group": age_group,
        "target_segment": target_segment,
        "target_time_seconds": parse_segment_time_to_seconds(modality, target_segment, target_time),
        "target_marginal_percentile": target_percentile,
        "conditions": parsed_conditions,
        "numerator_joint_probability": numerator_probability,
        "denominator_probability": denominator_probability,
        "conditional_percentile": conditional_percentile,
        "method": "Bayes ratio over cumulative joint performance distribution",
        "summary": (
            f"For {modality} {sex_label} {age_group}, {target_segment} is approximately "
            f"{round_percentile(conditional_percentile)} conditional on {given_text}."
        ),
    }


def _normalize_condition_operator(value: Any | None) -> str:
    if value is None:
        return "at_least_as_good"
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "faster_than": "at_least_as_good",
        "better_than": "at_least_as_good",
        "at_least_as_good": "at_least_as_good",
        "slower_than": "slower_than",
        "worse_than": "slower_than",
        "between": "between",
        "interval": "between",
    }
    return aliases.get(text, text)


def _condition_event(
    modality: str,
    sex_label: str,
    age_group: str,
    segment: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    operator = spec["operator"]
    if operator == "between":
        lower_time = spec.get("lower_time")
        upper_time = spec.get("upper_time")
        if lower_time is None or upper_time is None:
            return {
                "valid": False,
                "entity": "conditional_segment_percentile",
                "reason": "missing_interval_bounds",
                "message": "Interval conditions require both lower and upper time bounds.",
            }
        lower_seconds = parse_segment_time_to_seconds(modality, segment, lower_time)
        upper_seconds = parse_segment_time_to_seconds(modality, segment, upper_time)
        if lower_seconds > upper_seconds:
            lower_time, upper_time = upper_time, lower_time
            lower_seconds, upper_seconds = upper_seconds, lower_seconds
        lower_percentile = _marginal_percentile(modality, sex_label, age_group, segment, lower_time)
        upper_percentile = _marginal_percentile(modality, sex_label, age_group, segment, upper_time)
        probability = max(0.0, lower_percentile - upper_percentile)
        return {
            "segment": segment,
            "operator": "between",
            "lower_time_seconds": lower_seconds,
            "upper_time_seconds": upper_seconds,
            "lower_performance_percentile": lower_percentile,
            "upper_performance_percentile": upper_percentile,
            "event_probability": probability,
        }

    time_value = spec.get("time")
    if time_value is None:
        return {
            "valid": False,
            "entity": "conditional_segment_percentile",
            "reason": "missing_condition_time",
            "message": "Cumulative conditions require condition time.",
        }
    percentile = _marginal_percentile(modality, sex_label, age_group, segment, time_value)
    if operator == "at_least_as_good":
        probability = 100.0 - percentile
    elif operator == "slower_than":
        probability = percentile
    else:
        return {
            "valid": False,
            "entity": "conditional_segment_percentile",
            "reason": "unsupported_condition_operator",
            "message": f"Unsupported condition operator: {operator}.",
        }
    return {
        "segment": segment,
        "time_seconds": parse_segment_time_to_seconds(modality, segment, time_value),
        "performance_percentile": percentile,
        "operator": operator,
        "event_probability": probability,
    }


def _single_condition_probabilities(
    modality: str,
    sex_label: str,
    age_group: str,
    target_segment: str,
    target_percentile: float,
    condition_segment: str,
    condition: dict[str, Any],
) -> tuple[float, float]:
    operator = condition["operator"]
    if operator == "at_least_as_good":
        numerator = _pair_joint(
            modality,
            sex_label,
            age_group,
            target_segment,
            target_percentile,
            condition_segment,
            condition["performance_percentile"],
        )
        if not numerator.get("valid", False):
            raise ValueError(numerator.get("message", "Could not calculate joint numerator"))
        conditional_numerator = target_percentile - float(numerator["joint_pair_percentile"])
        return max(0.0, conditional_numerator), float(condition["event_probability"])

    if operator == "slower_than":
        joint_good = _pair_joint(
            modality,
            sex_label,
            age_group,
            target_segment,
            target_percentile,
            condition_segment,
            condition["performance_percentile"],
        )
        if not joint_good.get("valid", False):
            raise ValueError(joint_good.get("message", "Could not calculate joint numerator"))
        return float(joint_good["joint_pair_percentile"]), float(condition["event_probability"])

    if operator == "between":
        lower_joint = _pair_joint(
            modality,
            sex_label,
            age_group,
            target_segment,
            target_percentile,
            condition_segment,
            condition["lower_performance_percentile"],
        )
        upper_joint = _pair_joint(
            modality,
            sex_label,
            age_group,
            target_segment,
            target_percentile,
            condition_segment,
            condition["upper_performance_percentile"],
        )
        if not lower_joint.get("valid", False):
            raise ValueError(lower_joint.get("message", "Could not calculate interval lower joint numerator"))
        if not upper_joint.get("valid", False):
            raise ValueError(upper_joint.get("message", "Could not calculate interval upper joint numerator"))
        numerator = float(lower_joint["joint_pair_percentile"]) - float(upper_joint["joint_pair_percentile"])
        return max(0.0, numerator), float(condition["event_probability"])

    raise ValueError(f"Unsupported condition operator: {operator}")


def _condition_bounds(condition: dict[str, Any]) -> tuple[float, float]:
    if condition["operator"] == "between":
        values = [condition["lower_performance_percentile"], condition["upper_performance_percentile"]]
        return min(values), max(values)
    if condition["operator"] == "slower_than":
        return 0.0, condition["performance_percentile"]
    if condition["operator"] == "at_least_as_good":
        return condition["performance_percentile"], 100.0
    raise ValueError(f"Unsupported condition operator: {condition['operator']}")


def _pair_cdf(
    modality: str,
    sex_label: str,
    age_group: str,
    first_segment: str,
    first_percentile: float,
    second_segment: str,
    second_percentile: float,
) -> float:
    result = _pair_joint(
        modality,
        sex_label,
        age_group,
        first_segment,
        first_percentile,
        second_segment,
        second_percentile,
    )
    if not result.get("valid", False):
        raise ValueError(result.get("message", "Could not calculate pair CDF"))
    return float(result["joint_pair_percentile"])


def _sbr_cdf(
    modality: str,
    sex_label: str,
    age_group: str,
    percentile_by_segment: dict[str, float],
) -> float:
    result = get_sbr_percentile_by_segment_percentiles(
        modality,
        sex_label,
        age_group,
        percentile_by_segment["Swim"],
        percentile_by_segment["Bike"],
        percentile_by_segment["Run"],
    )
    if not result.get("valid", False):
        raise ValueError(result.get("message", "Could not calculate SBR CDF"))
    return float(result["joint_sbr_percentile"])


def _two_condition_probabilities(
    modality: str,
    sex_label: str,
    age_group: str,
    target_segment: str,
    target_percentile: float,
    condition_1_segment: str,
    condition_2_segment: str,
    condition_1: dict[str, Any],
    condition_2: dict[str, Any],
) -> tuple[float, float]:
    c1_low, c1_high = _condition_bounds(condition_1)
    c2_low, c2_high = _condition_bounds(condition_2)

    denominator = (
        _pair_cdf(modality, sex_label, age_group, condition_1_segment, c1_high, condition_2_segment, c2_high)
        - _pair_cdf(modality, sex_label, age_group, condition_1_segment, c1_low, condition_2_segment, c2_high)
        - _pair_cdf(modality, sex_label, age_group, condition_1_segment, c1_high, condition_2_segment, c2_low)
        + _pair_cdf(modality, sex_label, age_group, condition_1_segment, c1_low, condition_2_segment, c2_low)
    )

    def cdf(c1_percentile: float, c2_percentile: float) -> float:
        percentile_by_segment = {
            target_segment: target_percentile,
            condition_1_segment: c1_percentile,
            condition_2_segment: c2_percentile,
        }
        return _sbr_cdf(modality, sex_label, age_group, percentile_by_segment)

    numerator = (
        cdf(c1_high, c2_high)
        - cdf(c1_low, c2_high)
        - cdf(c1_high, c2_low)
        + cdf(c1_low, c2_low)
    )
    return max(0.0, numerator), max(0.0, denominator)


def _condition_text(condition: dict[str, Any]) -> str:
    if condition["operator"] == "between":
        return (
            f"{condition['segment']} between "
            f"{condition['lower_performance_percentile']:.1f} and "
            f"{condition['upper_performance_percentile']:.1f} percentile"
        )
    if condition["operator"] == "slower_than":
        return f"{condition['segment']} slower than {condition['performance_percentile']:.1f} percentile threshold"
    return f"{condition['segment']} at least as good as {condition['performance_percentile']:.1f} percentile"
