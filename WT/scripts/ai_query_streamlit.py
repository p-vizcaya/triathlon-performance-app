from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - user-facing runtime guard
    raise SystemExit(
        "Streamlit is not installed. Install it with: python -m pip install streamlit"
    ) from exc


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.ai_query.llm_client import LLMClientError, answer_natural_language_query  # noqa: E402
from scripts.ai_query.query_agent import run_query_agent  # noqa: E402
from scripts.ai_query.sources import (  # noqa: E402
    SEGMENTS,
    STANDARD_AGE_GROUPS,
    SPRINT_AGE_GROUPS,
)


MAIN_SEGMENTS = ("Swim", "Bike", "Run")
CONDITION_OPERATORS = {
    "At least as good as": "at_least_as_good",
    "Slower than": "slower_than",
    "Between": "between",
}

QUERY_EXAMPLES = {
    "Total time to percentile": "Example: Standard O 55-59, total time 2:45:00.",
    "Percentile to total time": "Example: Standard O 70-74, P80.",
    "Segment time to percentile": "Example: Standard O 40-44, Run 45:00, or Run pace 4:30/km.",
    "Percentile to segment time": "Example: Sprint F 45-49, Bike P75.",
    "Estimated total from Swim/Bike/Run": "Example: Swim 32:00, Bike 1:15:00, Run 45:00. Average T1/T2 are added.",
    "Full split evaluation": "Example: Swim 14:00, Bike 36:00, Run 24:30. Reports strongest/weakest main segment.",
    "Gap to target percentile": "Example: current total 2:45:00, target P75.",
    "Required missing segment for target percentile": "Example: given Swim and Bike, find the Run needed for total P75.",
    "Compare segments": "Example: Swim 32:00, Bike 1:15:00, Run 45:00, with optional T1/T2/Total.",
    "Conditional segment percentile": "Example: Run 45:00 among athletes whose Swim is at least as good as 32:00.",
    "Explain percentile": "Example: Explain what P75 means for Total or Run.",
}

UI_TEXT = {
    "en": {
        "context": "Context",
        "language": "Language",
        "modality": "Modality",
        "sex": "Sex",
        "age_group": "Age group",
        "query": "Query",
        "run_query": "Run query",
        "guided_query": "Guided query",
        "dialog": "Dialog",
        "payload": "Payload",
        "get_answer": "Get answer",
        "ask": "Ask",
    },
    "es": {
        "context": "Contexto",
        "language": "Idioma",
        "modality": "Modalidad",
        "sex": "Sexo",
        "age_group": "Grupo por edad",
        "query": "Consulta",
        "run_query": "Consultar",
        "guided_query": "Consulta guiada",
        "dialog": "Diálogo",
        "payload": "Payload",
        "get_answer": "Obtener respuesta",
        "ask": "Preguntar",
    },
}

QUERY_LABELS = {
    "en": {
        "Total time to percentile": "Total time to percentile",
        "Percentile to total time": "Percentile to total time",
        "Segment time to percentile": "Segment time to percentile",
        "Percentile to segment time": "Percentile to segment time",
        "Estimated total from Swim/Bike/Run": "Estimated total from Swim/Bike/Run",
        "Full split evaluation": "Full split evaluation",
        "Gap to target percentile": "Gap to target percentile",
        "Required missing segment for target percentile": "Required missing segment for target percentile",
        "Compare segments": "Compare segments",
        "Conditional segment percentile": "Conditional segment percentile",
        "Explain percentile": "Explain percentile",
    },
    "es": {
        "Total time to percentile": "Percentil por tiempo total",
        "Percentile to total time": "Tiempo total por percentil",
        "Segment time to percentile": "Percentil por segmento",
        "Percentile to segment time": "Tiempo de segmento por percentil",
        "Estimated total from Swim/Bike/Run": "Total estimado por Swim/Bike/Run",
        "Full split evaluation": "Evaluación completa de segmentos",
        "Gap to target percentile": "Brecha frente a percentil objetivo",
        "Required missing segment for target percentile": "Segmento faltante para percentil objetivo",
        "Compare segments": "Comparar segmentos",
        "Conditional segment percentile": "Percentil condicional de segmento",
        "Explain percentile": "Explicar percentil",
    },
}

QUERY_EXAMPLES_ES = {
    "Total time to percentile": "Ejemplo: Standard O 55-59, tiempo total 2:45:00.",
    "Percentile to total time": "Ejemplo: Standard O 70-74, P80.",
    "Segment time to percentile": "Ejemplo: Standard O 40-44, Run 45:00, o ritmo de Run 4:30/km.",
    "Percentile to segment time": "Ejemplo: Sprint F 45-49, Bike P75.",
    "Estimated total from Swim/Bike/Run": "Ejemplo: Swim 32:00, Bike 1:15:00, Run 45:00. Se suman T1/T2 promedio.",
    "Full split evaluation": "Ejemplo: Swim 14:00, Bike 36:00, Run 24:30. Reporta segmento principal más fuerte y más débil.",
    "Gap to target percentile": "Ejemplo: tiempo total actual 2:45:00, objetivo P75.",
    "Required missing segment for target percentile": "Ejemplo: con Swim y Bike conocidos, encontrar el Run necesario para P75 total.",
    "Compare segments": "Ejemplo: Swim 32:00, Bike 1:15:00, Run 45:00, con T1/T2/Total opcionales.",
    "Conditional segment percentile": "Ejemplo: Run 45:00 entre atletas cuyo Swim es al menos tan bueno como 32:00.",
    "Explain percentile": "Ejemplo: explicar qué significa P75 en Total o Run.",
}


def _ui(locale: str, key: str) -> str:
    return UI_TEXT.get(locale, UI_TEXT["en"]).get(key, UI_TEXT["en"].get(key, key))


def _query_label(locale: str, value: str) -> str:
    return QUERY_LABELS.get(locale, QUERY_LABELS["en"]).get(value, value)


def _clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, "")}


def _run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return run_query_agent(_clean_payload(payload))


def _show_response(response: dict[str, Any]) -> None:
    if response.get("needs_clarification"):
        st.warning(response.get("message") or response.get("clarification_question"))
    elif response.get("valid", False):
        st.success(response.get("explanation") or response.get("message") or "Query completed.")
    else:
        st.error(response.get("message") or response.get("explanation") or "Query could not be completed.")

    with st.expander("Structured response", expanded=False):
        st.json(response)

    result = response.get("result")
    if isinstance(result, dict):
        rows = _summary_rows(result)
        if rows:
            st.table(rows)


def _summary_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    preferred = (
        "entity",
        "modality",
        "sex_label",
        "age_group",
        "segment",
        "target_segment",
        "input_time",
        "time",
        "total_time",
        "estimated_total_time",
        "performance_percentile",
        "conditional_percentile",
        "joint_pair_percentile",
        "joint_sbr_percentile",
        "percentile",
        "target_percentile",
        "target_time",
        "improvement_time",
        "source",
        "sheet",
    )
    for key in preferred:
        value = result.get(key)
        if isinstance(value, (str, int, float, bool)):
            rows.append({"field": key, "value": value})
    return rows


def _language_control() -> str:
    label = st.sidebar.selectbox("Language / Idioma", ("English", "Español"))
    return "es" if label == "Español" else "en"


def _context_controls(locale: str = "en") -> tuple[str, str, str]:
    st.sidebar.header(_ui(locale, "context"))
    modality = st.sidebar.selectbox(_ui(locale, "modality"), ("Standard", "Sprint"))
    sex_category = st.sidebar.selectbox(_ui(locale, "sex"), ("O", "F"), help="O includes Open/Male; F is Female.")
    age_groups = STANDARD_AGE_GROUPS if modality == "Standard" else SPRINT_AGE_GROUPS
    age_group = st.sidebar.selectbox(_ui(locale, "age_group"), age_groups)
    return modality, sex_category, age_group


def _time_or_sport_unit(label: str, segment: str, modality: str, *, key: str) -> str:
    if segment not in MAIN_SEGMENTS:
        return st.text_input(label, placeholder="mm:ss or h:mm:ss", key=f"{key}_time")

    options = ["Time"]
    if segment == "Swim":
        options.append("Pace /100m")
    elif segment == "Bike":
        options.append("Speed km/h")
    elif segment == "Run":
        options.append("Pace /km")

    mode = st.selectbox(f"{label} input", options, key=f"{key}_mode")
    if mode == "Time":
        return st.text_input(label, placeholder="mm:ss or h:mm:ss", key=f"{key}_time")
    if mode == "Pace /100m":
        value = st.text_input(label, placeholder="1:40/100m", key=f"{key}_pace100")
        return f"{value}/100m" if value and "/100m" not in value else value
    if mode == "Speed km/h":
        value = st.text_input(label, placeholder="32", key=f"{key}_kmh")
        return f"{value} km/h" if value and "km" not in value.lower() else value
    value = st.text_input(label, placeholder="5:00/km", key=f"{key}_pacekm")
    return f"{value}/km" if value and "/km" not in value else value


def _percentile_input(label: str, *, key: str) -> float:
    return st.number_input(label, min_value=0.0, max_value=100.0, value=75.0, step=1.0, key=key)


def _guided_payload(modality: str, sex_category: str, age_group: str, locale: str = "en") -> dict[str, Any] | None:
    query_options = (
        "Total time to percentile",
        "Percentile to total time",
        "Segment time to percentile",
        "Percentile to segment time",
        "Estimated total from Swim/Bike/Run",
        "Full split evaluation",
        "Gap to target percentile",
        "Required missing segment for target percentile",
        "Compare segments",
        "Conditional segment percentile",
        "Explain percentile",
    )
    query_type = st.selectbox(
        _ui(locale, "query"),
        query_options,
        format_func=lambda value: _query_label(locale, value),
    )
    examples = QUERY_EXAMPLES_ES if locale == "es" else QUERY_EXAMPLES
    st.caption(examples.get(query_type, ""))

    base = {"modality": modality, "sex_category": sex_category, "age_group": age_group}

    if query_type == "Total time to percentile":
        total_time = st.text_input("Total time", placeholder="2:45:00")
        return {**base, "intent": "total_percentile_by_time", "total_time": total_time}

    if query_type == "Percentile to total time":
        percentile = _percentile_input("Percentile", key="total_percentile")
        return {**base, "intent": "total_time_by_percentile", "percentile": percentile}

    if query_type == "Segment time to percentile":
        segment = st.selectbox("Segment", SEGMENTS)
        segment_time = _time_or_sport_unit("Segment time", segment, modality, key="segment_time")
        return {**base, "intent": "segment_percentile_by_time", "segment": segment, "segment_time": segment_time}

    if query_type == "Percentile to segment time":
        segment = st.selectbox("Segment", SEGMENTS)
        percentile = _percentile_input("Percentile", key="segment_percentile")
        return {**base, "intent": "segment_time_by_percentile", "segment": segment, "percentile": percentile}

    if query_type in ("Estimated total from Swim/Bike/Run", "Full split evaluation"):
        swim_time = _time_or_sport_unit("Swim", "Swim", modality, key="sbr_swim")
        bike_time = _time_or_sport_unit("Bike", "Bike", modality, key="sbr_bike")
        run_time = _time_or_sport_unit("Run", "Run", modality, key="sbr_run")
        intent = {
            "Estimated total from Swim/Bike/Run": "estimated_total_percentile_from_segments",
            "Full split evaluation": "full_split_evaluation",
        }[query_type]
        return {**base, "intent": intent, "swim_time": swim_time, "bike_time": bike_time, "run_time": run_time}

    if query_type == "Gap to target percentile":
        scope = st.selectbox("Scope", ("Total", "Swim", "Bike", "Run", "T1", "T2"))
        current_time = _time_or_sport_unit("Current time", scope, modality, key="gap_current") if scope != "Total" else st.text_input("Current total time", placeholder="2:45:00")
        target_percentile = _percentile_input("Target percentile", key="gap_target")
        segment = None if scope == "Total" else scope
        return {
            **base,
            "intent": "gap_to_target_percentile",
            "segment": segment,
            "current_time": current_time,
            "target_percentile": target_percentile,
        }

    if query_type == "Required missing segment for target percentile":
        missing_segment = st.selectbox("Missing segment", MAIN_SEGMENTS)
        percentile = _percentile_input("Target total percentile", key="missing_target")
        payload = {**base, "intent": "required_missing_segment_for_target_percentile", "missing_segment": missing_segment, "percentile": percentile}
        for segment in MAIN_SEGMENTS:
            if segment == missing_segment:
                continue
            payload[f"{segment.lower()}_time"] = _time_or_sport_unit(segment, segment, modality, key=f"missing_{segment.lower()}")
        return payload

    if query_type == "Compare segments":
        payload = {**base, "intent": "compare_segments"}
        col1, col2, col3 = st.columns(3)
        with col1:
            payload["swim_time"] = _time_or_sport_unit("Swim", "Swim", modality, key="cmp_swim")
        with col2:
            payload["bike_time"] = _time_or_sport_unit("Bike", "Bike", modality, key="cmp_bike")
        with col3:
            payload["run_time"] = _time_or_sport_unit("Run", "Run", modality, key="cmp_run")
        col4, col5, col6 = st.columns(3)
        with col4:
            payload["t1_time"] = st.text_input("T1", placeholder="2:30")
        with col5:
            payload["t2_time"] = st.text_input("T2", placeholder="1:50")
        with col6:
            payload["total_time"] = st.text_input("Total", placeholder="1:21:26")
        return payload

    if query_type == "Conditional segment percentile":
        target_segment = st.selectbox("Target segment", MAIN_SEGMENTS, index=2)
        target_time = _time_or_sport_unit("Target time", target_segment, modality, key="cond_target")
        payload = {
            **base,
            "intent": "conditional_segment_percentile",
            "target_segment": target_segment,
            "target_time": target_time,
        }
        _condition_controls(payload, 1, target_segment, modality)
        use_second = st.checkbox("Add second condition")
        if use_second:
            _condition_controls(payload, 2, target_segment, modality)
        return payload

    if query_type == "Explain percentile":
        percentile = _percentile_input("Percentile", key="explain_percentile")
        scope = st.selectbox("Scope", ("Total", "Swim", "Bike", "Run", "Segment profile"))
        return {"intent": "explain_percentile", "percentile": percentile, "scope": scope}

    return None


def _condition_controls(payload: dict[str, Any], index: int, target_segment: str, modality: str) -> None:
    available = [segment for segment in MAIN_SEGMENTS if segment != target_segment]
    prefix = f"condition_{index}"
    st.subheader(f"Condition {index}")
    segment = st.selectbox(f"Condition {index} segment", available, key=f"{prefix}_segment")
    operator_label = st.selectbox(f"Condition {index} operator", tuple(CONDITION_OPERATORS), key=f"{prefix}_operator")
    operator = CONDITION_OPERATORS[operator_label]
    payload[f"{prefix}_segment"] = segment
    payload[f"{prefix}_operator"] = operator
    if operator == "between":
        col1, col2 = st.columns(2)
        with col1:
            payload[f"{prefix}_lower_time"] = _time_or_sport_unit("Lower time", segment, modality, key=f"{prefix}_lower")
        with col2:
            payload[f"{prefix}_upper_time"] = _time_or_sport_unit("Upper time", segment, modality, key=f"{prefix}_upper")
    else:
        payload[f"{prefix}_time"] = _time_or_sport_unit("Condition time", segment, modality, key=f"{prefix}_time")


def _natural_language_tab(modality: str, sex_category: str, age_group: str) -> None:
    default_context = {"modality": modality, "sex_category": sex_category, "age_group": age_group}
    use_context = st.checkbox("Use sidebar context", value=True)
    question = st.text_area(
        "Question",
        placeholder="What percentile is a 45:00 run for Standard O 40-44?",
        height=110,
    )
    timeout = st.number_input("Request timeout seconds", min_value=10, max_value=180, value=45, step=5)
    model = st.text_input("Model", value=os.getenv("AI_QUERY_MODEL", "gpt-5-nano"))
    if st.button("Ask", type="primary", disabled=not question.strip()):
        try:
            response = answer_natural_language_query(
                question.strip(),
                context=default_context if use_context else None,
                model=model or None,
                timeout=int(timeout),
            )
        except (LLMClientError, ValueError) as exc:
            st.error(str(exc))
        else:
            _show_response(response)


def main() -> None:
    st.set_page_config(page_title="Triathlon Performance Query", layout="wide")
    st.title("Triathlon Performance Query")

    locale = _language_control()
    modality, sex_category, age_group = _context_controls(locale)

    guided, dialog, payload_tab = st.tabs([_ui(locale, "guided_query"), _ui(locale, "dialog"), _ui(locale, "payload")])

    with guided:
        payload = _guided_payload(modality, sex_category, age_group, locale)
        if payload:
            if st.button(_ui(locale, "run_query"), type="primary"):
                try:
                    _show_response(_run_payload(payload))
                except Exception as exc:  # pragma: no cover - UI guard
                    st.error(str(exc))

    with dialog:
        _natural_language_tab(modality, sex_category, age_group)

    with payload_tab:
        st.caption("Paste a JSON payload when you want to test the machine contract directly.")
        text = st.text_area("Payload JSON", height=220, placeholder='{"intent": "total_percentile_by_time", "modality": "Standard", ...}')
        if st.button("Run payload", disabled=not text.strip()):
            try:
                payload = json.loads(text)
                if not isinstance(payload, dict):
                    raise ValueError("Payload must be a JSON object.")
                _show_response(_run_payload(payload))
            except (json.JSONDecodeError, ValueError) as exc:
                st.error(str(exc))


if __name__ == "__main__":
    main()
