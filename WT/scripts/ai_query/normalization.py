from __future__ import annotations

import re
import unicodedata
from typing import Any

from .sources import MODALITIES, PAIRS, SEGMENTS, STANDARD_AGE_GROUPS, SPRINT_AGE_GROUPS


class NormalizationError(ValueError):
    """Raised when a value cannot be normalized safely."""


SEGMENT_DISTANCES = {
    "Sprint": {
        "Swim": {"meters": 750.0},
        "Bike": {"kilometers": 20.0},
        "Run": {"kilometers": 5.0},
    },
    "Standard": {
        "Swim": {"meters": 1500.0},
        "Bike": {"kilometers": 40.0},
        "Run": {"kilometers": 10.0},
    },
}


def _clean(value: Any) -> str:
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[_/]+", " ", text)
    text = re.sub(r"[^a-z0-9:+.\-\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_modality(value: Any) -> str:
    cleaned = _clean(value)
    aliases = {
        "sprint": "Sprint",
        "short": "Sprint",
        "short distance": "Sprint",
        "standard": "Standard",
        "estand ar": "Standard",
        "estandar": "Standard",
        "olympic": "Standard",
        "olimpica": "Standard",
        "olimpico": "Standard",
        "olympic distance": "Standard",
    }
    if cleaned in aliases:
        return aliases[cleaned]
    title = str(value).strip().title()
    if title in MODALITIES:
        return title
    raise NormalizationError(f"Unknown modality: {value!r}")


def normalize_sex_category(value: Any, *, field: str = "sex_label") -> str:
    cleaned = _clean(value)
    aliases = {
        "f": "F",
        "female": "F",
        "femenino": "F",
        "mujer": "F",
        "women": "F",
        "woman": "F",
        "o": "O",
        "open": "O",
        "m": "O",
        "male": "O",
        "masculino": "O",
        "hombre": "O",
        "men": "O",
        "man": "O",
    }
    if cleaned not in aliases:
        raise NormalizationError(f"Unknown sex category: {value!r}")
    sex_label = aliases[cleaned]
    if field == "sex_label":
        return sex_label
    if field == "sex":
        return "F" if sex_label == "F" else "M"
    raise ValueError("field must be 'sex_label' or 'sex'")


def normalize_age_group(value: Any) -> str:
    cleaned = _clean(value)
    if cleaned == "all":
        raise NormalizationError("'All' is not exposed as a query age group")
    match = re.fullmatch(r"(\d{1,3})\s*-\s*(\d{1,3})", cleaned)
    if match:
        return f"{int(match.group(1))}-{int(match.group(2))}"
    raise NormalizationError(f"Unknown age group: {value!r}")


def resolve_age_group(age: Any, modality: Any) -> str:
    modality = normalize_modality(modality)
    try:
        age_int = int(age)
    except (TypeError, ValueError) as exc:
        raise NormalizationError(f"Age must be an integer: {age!r}") from exc

    if modality == "Sprint" and 16 <= age_int <= 19:
        return "16-19"
    if modality == "Standard" and 18 <= age_int <= 19:
        return "18-19"
    if age_int < 20:
        raise NormalizationError(f"Age {age_int} is not covered for {modality}")

    lower = 20 + ((age_int - 20) // 5) * 5
    upper = lower + 4
    group = f"{lower}-{upper}"
    valid_groups = SPRINT_AGE_GROUPS if modality == "Sprint" else STANDARD_AGE_GROUPS
    if group not in valid_groups:
        raise NormalizationError(f"Age group {group} is not exposed for {modality}")
    return group


def normalize_segment(value: Any) -> str:
    cleaned = _clean(value)
    aliases = {
        "swim": "Swim",
        "swimming": "Swim",
        "natacion": "Swim",
        "bike": "Bike",
        "cycling": "Bike",
        "bici": "Bike",
        "ciclismo": "Bike",
        "run": "Run",
        "running": "Run",
        "carrera": "Run",
        "t1": "T1",
        "transition 1": "T1",
        "transicion 1": "T1",
        "transition1": "T1",
        "t2": "T2",
        "transition 2": "T2",
        "transicion 2": "T2",
        "transition2": "T2",
        "total": "Total",
        "total time": "Total",
    }
    if cleaned in aliases:
        return aliases[cleaned]
    title = str(value).strip().title()
    if title in SEGMENTS:
        return title
    raise NormalizationError(f"Unknown segment: {value!r}")


def normalize_pair(value: Any) -> str:
    cleaned = _clean(value)
    compact = cleaned.replace(" ", "_").replace("-", "_")
    aliases = {
        "swim_bike": "swim_bike",
        "swim_bici": "swim_bike",
        "natacion_bike": "swim_bike",
        "natacion_ciclismo": "swim_bike",
        "swim_run": "swim_run",
        "natacion_run": "swim_run",
        "natacion_carrera": "swim_run",
        "bike_run": "bike_run",
        "bike_carrera": "bike_run",
        "ciclismo_run": "bike_run",
        "ciclismo_carrera": "bike_run",
    }
    if compact in aliases:
        return aliases[compact]

    parts = [normalize_segment(part) for part in re.split(r"\s+(?:and|y|con)\s+|[,+]", cleaned) if part.strip()]
    key = "_".join(part.lower() for part in parts)
    if key in PAIRS:
        return key
    reversed_key = "_".join(reversed([part.lower() for part in parts]))
    if reversed_key in PAIRS:
        return reversed_key
    raise NormalizationError(f"Unknown segment pair: {value!r}")


def parse_time_to_seconds(value: Any) -> float:
    if isinstance(value, (int, float)):
        if value < 0:
            raise NormalizationError("Time cannot be negative")
        return float(value)

    cleaned = _clean(value)
    if not cleaned:
        raise NormalizationError("Time cannot be blank")

    colon_parts = cleaned.split(":")
    if len(colon_parts) in (2, 3) and all(re.fullmatch(r"\d+(?:\.\d+)?", p) for p in colon_parts):
        nums = [float(p) for p in colon_parts]
        if len(nums) == 2:
            minutes, seconds = nums
            return minutes * 60 + seconds
        hours, minutes, seconds = nums
        return hours * 3600 + minutes * 60 + seconds

    total = 0.0
    matched = False
    patterns = (
        (r"(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours|hora|horas)", 3600),
        (r"(\d+(?:\.\d+)?)\s*(?:m|min|mins|minute|minutes|minuto|minutos)", 60),
        (r"(\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds|seg|segundo|segundos)", 1),
    )
    for pattern, multiplier in patterns:
        for match in re.finditer(pattern, cleaned):
            total += float(match.group(1)) * multiplier
            matched = True
    if matched:
        return total

    if re.fullmatch(r"\d+(?:\.\d+)?", cleaned):
        return float(cleaned)
    raise NormalizationError(f"Unknown time format: {value!r}")


def _performance_text(value: Any) -> str:
    return str(value).strip().lower().replace(",", ".")


def _pace_value_to_seconds(value: str) -> float:
    value = value.strip()
    if ":" in value:
        return parse_time_to_seconds(value)
    minutes = float(value)
    if minutes <= 0:
        raise NormalizationError("Pace must be positive")
    return minutes * 60


def _extract_swim_pace_per_100m(value: Any) -> float | None:
    text = _performance_text(value)
    match = re.search(r"(\d+(?::\d{2}){0,2}|\d+(?:\.\d+)?)\s*(?:/|per\s*)?\s*100\s*m\b", text)
    if not match:
        return None
    return _pace_value_to_seconds(match.group(1))


def _extract_run_pace_per_km(value: Any) -> float | None:
    text = _performance_text(value)
    match = re.search(r"(\d+(?::\d{2}){0,2}|\d+(?:\.\d+)?)\s*(?:/|per\s*)?\s*k(?:m|ilometer|ilometro)\b", text)
    if not match:
        match = re.search(r"(\d+(?::\d{2}){0,2}|\d+(?:\.\d+)?)\s*min\s*(?:/|per\s*)?\s*k(?:m|ilometer|ilometro)\b", text)
    if not match:
        return None
    return _pace_value_to_seconds(match.group(1))


def _extract_bike_speed_kmh(value: Any) -> float | None:
    text = _performance_text(value)
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:km\s*/\s*h|kmh|kph|kilometers?\s+per\s+hour|kilometros?\s+por\s+hora)\b", text)
    if not match:
        return None
    speed = float(match.group(1))
    if speed <= 0:
        raise NormalizationError("Bike speed must be positive")
    return speed


def parse_segment_time_to_seconds(modality: Any, segment: Any, value: Any) -> float:
    """Parse a segment time or sport-specific performance unit into segment seconds."""
    modality = normalize_modality(modality)
    segment = normalize_segment(segment)
    text = _clean(value)

    if segment == "Swim":
        pace = _extract_swim_pace_per_100m(value)
        if pace is not None:
            return pace * (SEGMENT_DISTANCES[modality]["Swim"]["meters"] / 100.0)
    elif segment == "Bike":
        speed = _extract_bike_speed_kmh(value)
        if speed is not None:
            return SEGMENT_DISTANCES[modality]["Bike"]["kilometers"] / speed * 3600.0
    elif segment == "Run":
        pace = _extract_run_pace_per_km(value)
        if pace is not None:
            return pace * SEGMENT_DISTANCES[modality]["Run"]["kilometers"]

    seconds = parse_time_to_seconds(value)
    if segment in {"Swim", "Bike", "Run"} and seconds < 5 * 60:
        ambiguous_minutes = re.fullmatch(r"0+\s*:\s*(\d{1,2})", text)
        if ambiguous_minutes:
            return float(ambiguous_minutes.group(1)) * 60
    return seconds


def format_seconds(seconds: Any) -> str:
    try:
        total = int(round(float(seconds)))
    except (TypeError, ValueError) as exc:
        raise NormalizationError(f"Seconds must be numeric: {seconds!r}") from exc
    if total < 0:
        raise NormalizationError("Seconds cannot be negative")
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def normalize_query_inputs(raw_inputs: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    if "modality" in raw_inputs and raw_inputs["modality"] is not None:
        normalized["modality"] = normalize_modality(raw_inputs["modality"])

    sex_value = raw_inputs.get("sex_category", raw_inputs.get("sex_label", raw_inputs.get("sex")))
    if sex_value is not None:
        normalized["sex_label"] = normalize_sex_category(sex_value, field="sex_label")
        normalized["sex"] = normalize_sex_category(sex_value, field="sex")

    if "age_group" in raw_inputs and raw_inputs["age_group"] is not None:
        normalized["age_group"] = normalize_age_group(raw_inputs["age_group"])
    elif "age" in raw_inputs and raw_inputs["age"] is not None:
        if "modality" not in normalized:
            raise NormalizationError("Modality is required to resolve an exact age")
        normalized["age_group"] = resolve_age_group(raw_inputs["age"], normalized["modality"])

    if "segment" in raw_inputs and raw_inputs["segment"] is not None:
        normalized["segment"] = normalize_segment(raw_inputs["segment"])

    if "pair" in raw_inputs and raw_inputs["pair"] is not None:
        normalized["pair"] = normalize_pair(raw_inputs["pair"])

    for key in ("time", "total_time", "t1_time", "t2_time"):
        if key in raw_inputs and raw_inputs[key] is not None:
            normalized[key.replace("_time", "_seconds") if key != "time" else "seconds"] = parse_time_to_seconds(raw_inputs[key])
    for key, segment in (("swim_time", "Swim"), ("bike_time", "Bike"), ("run_time", "Run")):
        if key in raw_inputs and raw_inputs[key] is not None:
            if "modality" not in normalized:
                raise NormalizationError("Modality is required to parse segment pace or speed")
            normalized[key.replace("_time", "_seconds")] = parse_segment_time_to_seconds(normalized["modality"], segment, raw_inputs[key])
    unit_fields = {
        "swim_pace_100m": ("swim_seconds", "Swim"),
        "bike_speed_kmh": ("bike_seconds", "Bike"),
        "run_pace_km": ("run_seconds", "Run"),
    }
    for key, (output_key, segment) in unit_fields.items():
        if key in raw_inputs and raw_inputs[key] is not None:
            if "modality" not in normalized:
                raise NormalizationError("Modality is required to parse segment pace or speed")
            normalized[output_key] = parse_segment_time_to_seconds(normalized["modality"], segment, raw_inputs[key])

    if "percentile" in raw_inputs and raw_inputs["percentile"] is not None:
        percentile = float(raw_inputs["percentile"])
        if not 0 <= percentile <= 100:
            raise NormalizationError("Percentile must be between 0 and 100")
        normalized["percentile"] = percentile

    return normalized
