from __future__ import annotations

import json
import os
import sys
import html
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
from scripts.ai_query.event_curves import list_event_options  # noqa: E402
from scripts.ai_query.query_agent import run_query_agent  # noqa: E402
from scripts.ai_query.sources import (  # noqa: E402
    SEGMENTS,
    STANDARD_AGE_GROUPS,
    SPRINT_AGE_GROUPS,
)


MAIN_SEGMENTS = ("Swim", "Bike", "Run")
TYPICALITY_WORKBOOK = SCRIPT_DIR.parent / "outputs" / "WT_Typicality_By_Event_Modality_Sex_AgeGroup_1989_2025.xlsx"
LOGO_PATH = SCRIPT_DIR.parent / "assets" / "LogoSimple.png"
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
    "Full split evaluation": "Example: Swim 14:00, T1 1:20, Bike 36:00, T2 1:10, Run 24:30. Reports each split and total percentile.",
    "Gap to target percentile": "Example: current total 2:45:00, target P75.",
    "Required missing segment for target percentile": "Example: given Swim and Bike, find the Run needed for total P75.",
    "Compare segments": "Example: Swim 32:00, Bike 1:15:00, Run 45:00, with optional T1/T2/Total.",
    "Direct championship comparison": "Example: Total 2:18:30 directly against Gold Coast 2009 and Wollongong 2025, with no adjustment.",
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
        "championships": "Championships to compare",
        "available_events": "Available events",
        "event_pick": "Select events",
        "event_missing": "No championship event list is available in this package.",
        "app_title": "Triathlon Performance Tables",
        "app_subtitle": "Compare your times with athletes in the same distance, sex, and age group.",
        "brand": "Global Triathlon Colombia",
        "ui_build": "UI build 2026-05-29",
        "query_route": "What do you want to do?",
        "query_detail": "Choose the specific question",
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
        "championships": "Campeonatos para comparar",
        "available_events": "Eventos disponibles",
        "event_pick": "Selecciona eventos",
        "event_missing": "No hay una lista de campeonatos disponible en este paquete.",
        "app_title": "Tablas de Desempe\u00f1o en Triatl\u00f3n",
        "app_subtitle": "Compara tus tiempos con deportistas de tu misma distancia, sexo y grupo de edad.",
        "brand": "Global Triathlon Colombia",
        "ui_build": "Versi\u00f3n UI 2026-05-29",
        "query_route": "\u00bfQu\u00e9 quieres hacer?",
        "query_detail": "Elige la pregunta espec\u00edfica",
    },
}

QUERY_ROUTES = {
    "Evaluate a time": (
        "Total time to percentile",
        "Segment time to percentile",
    ),
    "Find a target time": (
        "Percentile to total time",
        "Percentile to segment time",
    ),
    "Compare with a championship": (
        "Direct championship comparison",
    ),
    "Analyze segments": (
        "Estimated total from Swim/Bike/Run",
        "Full split evaluation",
        "Compare segments",
    ),
    "Improve toward a goal": (
        "Gap to target percentile",
        "Required missing segment for target percentile",
    ),
    "Advanced / help": (
        "Conditional segment percentile",
        "Explain percentile",
    ),
}

ROUTE_LABELS = {
    "en": {
        "Evaluate a time": "Evaluate a time",
        "Find a target time": "Find a target time",
        "Compare with a championship": "Compare with a championship",
        "Analyze segments": "Analyze segments",
        "Improve toward a goal": "Improve toward a goal",
        "Advanced / help": "Advanced / help",
    },
    "es": {
        "Evaluate a time": "Evaluar un tiempo",
        "Find a target time": "Buscar un tiempo objetivo",
        "Compare with a championship": "Compararme con un campeonato",
        "Analyze segments": "Evaluar mis segmentos",
        "Improve toward a goal": "Mejorar hacia un objetivo",
        "Advanced / help": "Avanzadas / ayuda",
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
        "Direct championship comparison": "Direct championship comparison",
        "Conditional segment percentile": "Conditional segment percentile",
        "Explain percentile": "Explain percentile",
    },
    "es": {
        "Total time to percentile": "Percentil por tiempo total",
        "Percentile to total time": "Tiempo total por percentil",
        "Segment time to percentile": "Percentil por segmento",
        "Percentile to segment time": "Tiempo de segmento por percentil",
        "Estimated total from Swim/Bike/Run": "Total estimado por Nataci\u00f3n/Ciclismo/Carrera",
        "Full split evaluation": "Evaluación completa de segmentos",
        "Gap to target percentile": "Brecha frente a percentil objetivo",
        "Required missing segment for target percentile": "Segmento faltante para percentil objetivo",
        "Compare segments": "Comparar segmentos",
        "Direct championship comparison": "Comparaci\u00f3n directa con campeonatos",
        "Conditional segment percentile": "Percentil condicional de segmento",
        "Explain percentile": "Explicar percentil",
    },
}

QUERY_EXAMPLES_ES = {
    "Total time to percentile": "Ejemplo: Standard O 55-59, tiempo total 2:45:00.",
    "Percentile to total time": "Ejemplo: Standard O 70-74, P80.",
    "Segment time to percentile": "Ejemplo: Standard O 40-44, Carrera 45:00, o ritmo de Carrera 4:30/km.",
    "Percentile to segment time": "Ejemplo: Sprint F 45-49, Ciclismo P75.",
    "Estimated total from Swim/Bike/Run": "Ejemplo: Nataci\u00f3n 32:00, Ciclismo 1:15:00, Carrera 45:00. Se suman T1/T2 promedio.",
    "Full split evaluation": "Ejemplo: Nataci\u00f3n 14:00, T1 1:20, Ciclismo 36:00, T2 1:10, Carrera 24:30. Reporta cada percentil y el total.",
    "Gap to target percentile": "Ejemplo: tiempo total actual 2:45:00, objetivo P75.",
    "Required missing segment for target percentile": "Ejemplo: con Nataci\u00f3n y Ciclismo conocidos, encontrar la Carrera necesaria para P75 total.",
    "Compare segments": "Ejemplo: Nataci\u00f3n 32:00, Ciclismo 1:15:00, Carrera 45:00, con T1/T2/Total opcionales.",
    "Direct championship comparison": "Ejemplo: Total 2:18:30 directamente contra Gold Coast 2009 y Wollongong 2025, sin ajuste.",
    "Conditional segment percentile": "Ejemplo: Carrera 45:00 entre atletas cuya Nataci\u00f3n es al menos tan buena como 32:00.",
    "Explain percentile": "Ejemplo: explicar qu\u00e9 significa P75 en Total o Carrera.",
}


def _ui(locale: str, key: str) -> str:
    return UI_TEXT.get(locale, UI_TEXT["en"]).get(key, UI_TEXT["en"].get(key, key))


def _query_label(locale: str, value: str) -> str:
    return QUERY_LABELS.get(locale, QUERY_LABELS["en"]).get(value, value)


def _route_label(locale: str, value: str) -> str:
    return ROUTE_LABELS.get(locale, ROUTE_LABELS["en"]).get(value, value)


def _segment_label(locale: str, value: str) -> str:
    if locale == "es":
        return {
            "Swim": "Nataci\u00f3n",
            "Bike": "Ciclismo",
            "Run": "Carrera",
            "Total": "Total",
            "Segment profile": "Perfil de segmentos",
        }.get(value, value)
    return value


def _field_label(locale: str, value: str) -> str:
    if locale == "es":
        return {
            "Total time": "Tiempo total",
            "Percentile": "Percentil",
            "Segment": "Segmento",
            "Segment time": "Tiempo del segmento",
            "Scope": "Alcance",
            "Current time": "Tiempo actual",
            "Current total time": "Tiempo total actual",
            "Target percentile": "Percentil objetivo",
            "Missing segment": "Segmento faltante",
            "Target total percentile": "Percentil total objetivo",
            "Target segment": "Segmento objetivo",
            "Target time": "Tiempo objetivo",
            "Time": "Tiempo",
            "Condition time": "Tiempo de la condici\u00f3n",
            "Lower time": "Tiempo inferior",
            "Upper time": "Tiempo superior",
            "Add second condition": "Agregar segunda condici\u00f3n",
            "Run payload": "Ejecutar payload",
        }.get(value, value)
    return value


def _input_mode_label(locale: str, value: str) -> str:
    if locale == "es":
        return {
            "Time": "Tiempo",
            "Pace /100m": "Ritmo /100 m",
            "Speed km/h": "Velocidad km/h",
            "Pace /km": "Ritmo /km",
        }.get(value, value)
    return value


def _apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --gtc-blue: #1377b9;
            --gtc-sky: #5f9ed7;
            --gtc-red: #ef3f3f;
            --gtc-yellow: #f2d21a;
            --gtc-ink: #1d2433;
            --gtc-muted: #667085;
            --gtc-soft: #f4f8fc;
        }
        .block-container {
            padding-top: 2.2rem;
            max-width: 1180px;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f6f9fc 0%, #eef4fa 100%);
        }
        .gtc-hero {
            display: flex;
            align-items: center;
            gap: 1.25rem;
            padding: 1.2rem 1.35rem;
            margin-bottom: 1.25rem;
            border: 1px solid #d8e7f4;
            border-radius: 8px;
            background: linear-gradient(135deg, #ffffff 0%, #f4f9fd 100%);
        }
        .gtc-logo {
            width: 96px;
            height: 96px;
            object-fit: contain;
            flex: 0 0 96px;
        }
        .gtc-brand {
            color: var(--gtc-blue);
            font-size: .82rem;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: .25rem;
        }
        .gtc-title {
            color: var(--gtc-ink);
            font-size: clamp(2rem, 4vw, 3rem);
            line-height: 1.05;
            font-weight: 800;
            margin: 0;
        }
        .gtc-subtitle {
            color: var(--gtc-muted);
            font-size: 1.05rem;
            margin-top: .5rem;
            max-width: 760px;
        }
        .gtc-build {
            color: var(--gtc-muted);
            font-size: .76rem;
            margin-top: .45rem;
        }
        .gtc-disciplines {
            display: flex;
            gap: .5rem;
            flex-wrap: wrap;
            margin-top: .75rem;
        }
        .gtc-chip {
            border: 1px solid #d7e6f2;
            border-radius: 999px;
            padding: .28rem .68rem;
            color: #27445f;
            background: #ffffff;
            font-size: .86rem;
            font-weight: 650;
        }
        .gtc-chip:nth-child(1) { border-left: 4px solid var(--gtc-sky); }
        .gtc-chip:nth-child(2) { border-left: 4px solid var(--gtc-yellow); }
        .gtc-chip:nth-child(3) { border-left: 4px solid var(--gtc-red); }
        .gtc-result-card {
            border: 1px solid #d8e7f4;
            border-left: 6px solid var(--gtc-blue);
            border-radius: 8px;
            padding: 1rem 1.15rem;
            background: #ffffff;
            box-shadow: 0 10px 28px rgba(19, 119, 185, .08);
            margin: .8rem 0 1rem;
        }
        .gtc-result-label {
            color: var(--gtc-muted);
            font-size: .85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .06em;
        }
        .gtc-result-value {
            color: var(--gtc-ink);
            font-size: 2.1rem;
            line-height: 1.1;
            font-weight: 800;
            margin-top: .2rem;
        }
        .gtc-result-detail {
            color: var(--gtc-muted);
            font-size: .98rem;
            margin-top: .45rem;
        }
        .stButton > button[kind="primary"] {
            background: var(--gtc-red);
            border-color: var(--gtc-red);
        }
        @media (max-width: 760px) {
            .gtc-hero { align-items: flex-start; }
            .gtc-logo { width: 72px; height: 72px; flex-basis: 72px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _brand_header(locale: str) -> None:
    logo_html = ""
    if LOGO_PATH.exists():
        import base64

        encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
        logo_html = f'<img class="gtc-logo" src="data:image/png;base64,{encoded}" alt="Global Triathlon Colombia logo">'
    st.markdown(
        f"""
        <section class="gtc-hero">
            {logo_html}
            <div>
                <div class="gtc-brand">{html.escape(_ui(locale, "brand"))}</div>
                <h1 class="gtc-title">{html.escape(_ui(locale, "app_title"))}</h1>
                <div class="gtc-subtitle">{html.escape(_ui(locale, "app_subtitle"))}</div>
                <div class="gtc-build">{html.escape(_ui(locale, "ui_build"))}</div>
                <div class="gtc-disciplines">
                    <span class="gtc-chip">{'Swim' if locale == 'en' else 'Nataci\u00f3n'}</span>
                    <span class="gtc-chip">{'Bike' if locale == 'en' else 'Ciclismo'}</span>
                    <span class="gtc-chip">{'Run' if locale == 'en' else 'Carrera'}</span>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


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
        if response.get("valid", False):
            _result_card(result)
        if result.get("entity") == "event_curve_comparison" and result.get("comparisons"):
            st.dataframe(_event_comparison_table(result), hide_index=True, use_container_width=True)
        rows = _summary_rows(result)
        if rows:
            st.table(rows)


def _result_card(result: dict[str, Any]) -> None:
    card = _result_card_data(result)
    if not card:
        return
    st.markdown(
        f"""
        <div class="gtc-result-card">
            <div class="gtc-result-label">{html.escape(card['label'])}</div>
            <div class="gtc-result-value">{html.escape(card['value'])}</div>
            <div class="gtc-result-detail">{html.escape(card['detail'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _result_card_data(result: dict[str, Any]) -> dict[str, str] | None:
    entity = result.get("entity")
    context = f"{result.get('modality')} {result.get('sex_label')} {result.get('age_group')}"
    if entity == "total_time_curve" and "performance_percentile" in result:
        return {
            "label": f"{context} | Total time",
            "value": f"P{float(result['performance_percentile']):.1f}",
            "detail": f"Total time {result.get('input_total_time')} compared with the reference table.",
        }
    if entity == "segment_curve" and "performance_percentile" in result:
        segment = str(result.get("segment"))
        return {
            "label": f"{context} | {segment}",
            "value": f"P{float(result['performance_percentile']):.1f}",
            "detail": f"{segment} time {result.get('input_time')} compared with the reference table.",
        }
    if entity == "event_curve_comparison":
        comparisons = result.get("comparisons") or []
        if not comparisons:
            return None
        first = next((item for item in comparisons if item.get("valid", True)), comparisons[0])
        if not first.get("valid", True):
            detail = first.get("message") or result.get("message") or "Outside the empirical range."
            if first.get("empirical_min_time") and first.get("empirical_max_time"):
                detail = (
                    f"{detail} Range: {first.get('empirical_min_time')} to "
                    f"{first.get('empirical_max_time')} (n={first.get('n')})."
                )
            elif first.get("p_min") is not None and first.get("p_max") is not None:
                detail = f"{detail} Range: P{float(first.get('p_min')):.1f} to P{float(first.get('p_max')):.1f} (n={first.get('n')})."
            return {
                "label": f"{context} | {result.get('segment')} in {first.get('year')}",
                "value": "Outside range",
                "detail": detail,
            }
        if result.get("query_type") == "percentile_to_time":
            return {
                "label": f"{context} | {result.get('segment')} in {first.get('year')}",
                "value": str(first.get("estimated_time")),
                "detail": f"Estimated time for P{float(result.get('percentile')):.1f} in {first.get('event_name')} (n={first.get('n')}).",
            }
        return {
            "label": f"{context} | {result.get('segment')} in {first.get('year')}",
            "value": f"Position {first.get('estimated_position')} of {first.get('n')}",
            "detail": f"{result.get('input_time')} is approximately P{float(first.get('performance_percentile')):.1f} in {first.get('event_name')}.",
        }
    return None


def _event_comparison_table(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    if result.get("query_type") == "percentile_to_time":
        for item in result.get("comparisons", []):
            if not item.get("valid", True):
                rows.append(
                    {
                        "year": item.get("year"),
                        "championship": item.get("event_name"),
                        "n": item.get("n"),
                        "position": None,
                        "time": None,
                        "status": item.get("message") or "Outside empirical range",
                        "range": _event_range_text(item),
                    }
                )
                continue
            rows.append(
                {
                    "year": item.get("year"),
                    "championship": item.get("event_name"),
                    "n": item.get("n"),
                    "position": round(float(item["estimated_position"]), 1),
                    "time": item.get("estimated_time"),
                }
            )
        return rows

    for item in result.get("comparisons", []):
        if not item.get("valid", True):
            rows.append(
                {
                    "year": item.get("year"),
                    "championship": item.get("event_name"),
                    "n": item.get("n"),
                    "position": None,
                    "percentile": None,
                    "status": item.get("message") or "Outside empirical range",
                    "range": _event_range_text(item),
                }
            )
            continue
        rows.append(
            {
                "year": item.get("year"),
                "championship": item.get("event_name"),
                "n": item.get("n"),
                "position": item.get("estimated_position"),
                "percentile": round(float(item["performance_percentile"]), 1),
            }
        )
    return rows


def _event_range_text(item: dict[str, Any]) -> str | None:
    if item.get("empirical_min_time") and item.get("empirical_max_time"):
        return f"{item.get('empirical_min_time')} to {item.get('empirical_max_time')}"
    if item.get("p_min") is not None and item.get("p_max") is not None:
        return f"P{float(item.get('p_min')):.1f} to P{float(item.get('p_max')):.1f}"
    return None


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


@st.cache_data(show_spinner=False)
def _load_event_typicality(path: str) -> list[dict[str, Any]]:
    try:
        import pandas as pd
    except ModuleNotFoundError:
        return []

    workbook = Path(path)
    if not workbook.exists():
        return []

    columns = [
        "modality",
        "sex",
        "age_group",
        "year",
        "n",
        "p50_time",
        "median_shift_pct_vs_group",
        "rms_log_quantile_diff",
        "review_note",
        "source_files",
    ]
    try:
        data = pd.read_excel(workbook, sheet_name="Event_Typicality", usecols=columns)
    except Exception:
        return []

    data["source_files"] = data["source_files"].fillna("").astype(str)
    data["event"] = (
        data["source_files"]
        .str.split(";")
        .str[0]
        .str.replace(".xlsx", "", regex=False)
        .str.strip()
    )
    data["review_note"] = data["review_note"].fillna("").astype(str)
    data = data.sort_values(["modality", "sex", "age_group", "year"])
    return data.to_dict("records")


def _event_label(row: dict[str, Any]) -> str:
    event = str(row.get("event") or row.get("source_files") or row.get("year"))
    return f"{int(row['year'])} - {event}"


def _event_coverage_text(rows: list[dict[str, Any]], locale: str) -> str:
    years = sorted({int(row["year"]) for row in rows})
    if not years:
        return ""
    if locale == "es":
        return f"{len(years)} eventos disponibles entre {years[0]} y {years[-1]}. La lista tiene desplazamiento vertical."
    return f"{len(years)} events available between {years[0]} and {years[-1]}. Scroll the list to see all years."


def _championship_event_controls(modality: str, sex_category: str, age_group: str, locale: str) -> None:
    event_sex = "M" if sex_category == "O" else sex_category
    rows = [
        row
        for row in _load_event_typicality(str(TYPICALITY_WORKBOOK))
        if row.get("modality") == modality
        and row.get("sex") == event_sex
        and row.get("age_group") == age_group
    ]
    with st.sidebar.expander(_ui(locale, "championships"), expanded=False):
        if not rows:
            st.caption(_ui(locale, "event_missing"))
            return

        st.caption(_event_coverage_text(rows, locale))
        table_rows = [
            {
                "year": int(row["year"]),
                "event": row.get("event"),
            }
            for row in rows
        ]
        st.dataframe(table_rows, hide_index=True, use_container_width=True)


def _context_controls(locale: str = "en") -> tuple[str, str, str]:
    st.sidebar.header(_ui(locale, "context"))
    modality = st.sidebar.selectbox(_ui(locale, "modality"), ("Standard", "Sprint"))
    sex_category = st.sidebar.selectbox(_ui(locale, "sex"), ("O", "F"), help="O includes Open/Male; F is Female.")
    age_groups = STANDARD_AGE_GROUPS if modality == "Standard" else SPRINT_AGE_GROUPS
    age_group = st.sidebar.selectbox(_ui(locale, "age_group"), age_groups)
    return modality, sex_category, age_group


def _time_or_sport_unit(label: str, segment: str, modality: str, *, key: str, locale: str = "en") -> str:
    visible_label = _field_label(locale, label)
    if segment not in MAIN_SEGMENTS:
        return st.text_input(visible_label, placeholder="mm:ss or h:mm:ss", key=f"{key}_time")

    options = ["Time"]
    if segment == "Swim":
        options.append("Pace /100m")
    elif segment == "Bike":
        options.append("Speed km/h")
    elif segment == "Run":
        options.append("Pace /km")

    mode = st.selectbox(
        f"{visible_label} input" if locale == "en" else f"Entrada de {visible_label.lower()}",
        options,
        key=f"{key}_mode",
        format_func=lambda value: _input_mode_label(locale, value),
    )
    if mode == "Time":
        return st.text_input(visible_label, placeholder="40:00 or 1:10:00", key=f"{key}_time")
    if mode == "Pace /100m":
        value = st.text_input(visible_label, placeholder="1:40/100m", key=f"{key}_pace100")
        return f"{value}/100m" if value and "/100m" not in value else value
    if mode == "Speed km/h":
        value = st.text_input(visible_label, placeholder="32", key=f"{key}_kmh")
        return f"{value} km/h" if value and "km" not in value.lower() else value
    value = st.text_input(visible_label, placeholder="5:00/km", key=f"{key}_pacekm")
    return f"{value}/km" if value and "/km" not in value else value


def _percentile_input(label: str, *, key: str, locale: str = "en") -> float:
    return st.number_input(_field_label(locale, label), min_value=0.0, max_value=100.0, value=75.0, step=1.0, key=key)


def _guided_payload(modality: str, sex_category: str, age_group: str, locale: str = "en") -> dict[str, Any] | None:
    route = st.radio(
        _ui(locale, "query_route"),
        tuple(QUERY_ROUTES),
        format_func=lambda value: _route_label(locale, value),
        horizontal=True,
    )
    query_options = QUERY_ROUTES[route]
    query_type = st.selectbox(
        _ui(locale, "query_detail"),
        query_options,
        format_func=lambda value: _query_label(locale, value),
    )
    examples = QUERY_EXAMPLES_ES if locale == "es" else QUERY_EXAMPLES
    st.caption(examples.get(query_type, ""))

    base = {"modality": modality, "sex_category": sex_category, "age_group": age_group}

    if query_type == "Total time to percentile":
        total_time = st.text_input(_field_label(locale, "Total time"), placeholder="2:45:00")
        return {**base, "intent": "total_percentile_by_time", "total_time": total_time}

    if query_type == "Percentile to total time":
        percentile = _percentile_input("Percentile", key="total_percentile", locale=locale)
        return {**base, "intent": "total_time_by_percentile", "percentile": percentile}

    if query_type == "Segment time to percentile":
        segment = st.selectbox(_field_label(locale, "Segment"), SEGMENTS, format_func=lambda value: _segment_label(locale, value))
        segment_time = _time_or_sport_unit("Segment time", segment, modality, key="segment_time", locale=locale)
        return {**base, "intent": "segment_percentile_by_time", "segment": segment, "segment_time": segment_time}

    if query_type == "Percentile to segment time":
        segment = st.selectbox(_field_label(locale, "Segment"), SEGMENTS, format_func=lambda value: _segment_label(locale, value))
        percentile = _percentile_input("Percentile", key="segment_percentile", locale=locale)
        return {**base, "intent": "segment_time_by_percentile", "segment": segment, "percentile": percentile}

    if query_type == "Estimated total from Swim/Bike/Run":
        swim_time = _time_or_sport_unit(_segment_label(locale, "Swim"), "Swim", modality, key="sbr_swim", locale=locale)
        bike_time = _time_or_sport_unit(_segment_label(locale, "Bike"), "Bike", modality, key="sbr_bike", locale=locale)
        run_time = _time_or_sport_unit(_segment_label(locale, "Run"), "Run", modality, key="sbr_run", locale=locale)
        return {**base, "intent": "estimated_total_percentile_from_segments", "swim_time": swim_time, "bike_time": bike_time, "run_time": run_time}

    if query_type == "Full split evaluation":
        swim_time = _time_or_sport_unit(_segment_label(locale, "Swim"), "Swim", modality, key="full_swim", locale=locale)
        t1_time = st.text_input("T1", placeholder="1:20", key="full_t1")
        bike_time = _time_or_sport_unit(_segment_label(locale, "Bike"), "Bike", modality, key="full_bike", locale=locale)
        t2_time = st.text_input("T2", placeholder="1:10", key="full_t2")
        run_time = _time_or_sport_unit(_segment_label(locale, "Run"), "Run", modality, key="full_run", locale=locale)
        return {
            **base,
            "intent": "full_split_evaluation",
            "swim_time": swim_time,
            "t1_time": t1_time,
            "bike_time": bike_time,
            "t2_time": t2_time,
            "run_time": run_time,
        }

    if query_type == "Gap to target percentile":
        scope = st.selectbox(_field_label(locale, "Scope"), ("Total", "Swim", "Bike", "Run", "T1", "T2"), format_func=lambda value: _segment_label(locale, value))
        current_time = _time_or_sport_unit("Current time", scope, modality, key="gap_current", locale=locale) if scope != "Total" else st.text_input(_field_label(locale, "Current total time"), placeholder="2:45:00")
        target_percentile = _percentile_input("Target percentile", key="gap_target", locale=locale)
        segment = None if scope == "Total" else scope
        return {
            **base,
            "intent": "gap_to_target_percentile",
            "segment": segment,
            "current_time": current_time,
            "target_percentile": target_percentile,
        }

    if query_type == "Required missing segment for target percentile":
        missing_segment = st.selectbox(_field_label(locale, "Missing segment"), MAIN_SEGMENTS, format_func=lambda value: _segment_label(locale, value))
        percentile = _percentile_input("Target total percentile", key="missing_target", locale=locale)
        payload = {**base, "intent": "required_missing_segment_for_target_percentile", "missing_segment": missing_segment, "percentile": percentile}
        for segment in MAIN_SEGMENTS:
            if segment == missing_segment:
                continue
            payload[f"{segment.lower()}_time"] = _time_or_sport_unit(_segment_label(locale, segment), segment, modality, key=f"missing_{segment.lower()}", locale=locale)
        return payload

    if query_type == "Compare segments":
        payload = {**base, "intent": "compare_segments"}
        col1, col2, col3 = st.columns(3)
        with col1:
            payload["swim_time"] = _time_or_sport_unit(_segment_label(locale, "Swim"), "Swim", modality, key="cmp_swim", locale=locale)
        with col2:
            payload["bike_time"] = _time_or_sport_unit(_segment_label(locale, "Bike"), "Bike", modality, key="cmp_bike", locale=locale)
        with col3:
            payload["run_time"] = _time_or_sport_unit(_segment_label(locale, "Run"), "Run", modality, key="cmp_run", locale=locale)
        col4, col5, col6 = st.columns(3)
        with col4:
            payload["t1_time"] = st.text_input("T1", placeholder="2:30")
        with col5:
            payload["t2_time"] = st.text_input("T2", placeholder="1:50")
        with col6:
            payload["total_time"] = st.text_input(_field_label(locale, "Total time"), placeholder="1:21:26")
        return payload

    if query_type == "Direct championship comparison":
        segment = st.selectbox(
            _field_label(locale, "Segment"),
            SEGMENTS,
            index=list(SEGMENTS).index("Total"),
            format_func=lambda value: _segment_label(locale, value),
        )
        st.caption(
            "Direct empirical comparison against the selected championship; no event-difficulty adjustment is applied."
            if locale == "en"
            else "Comparaci\u00f3n emp\u00edrica directa contra el campeonato seleccionado; no se aplica ajuste por dificultad del evento."
        )
        mode = st.radio(
            "Mode" if locale == "en" else "Modo",
            ("Time to event position", "Event percentile to time")
            if locale == "en"
            else ("Tiempo a posici\u00f3n en campeonato", "Percentil del campeonato a tiempo"),
            horizontal=True,
        )
        min_n = st.number_input("Minimum n" if locale == "en" else "n m\u00ednimo", min_value=1, max_value=100, value=20, step=1)
        options = list_event_options(modality, sex_category, age_group, segment, min_n=int(min_n))
        st.caption(_event_coverage_text(options, locale))
        labels = [f"{row['year']} - {row['event_name']} (n={row['n']})" for row in options]
        selected = st.multiselect(
            "Championships" if locale == "en" else "Campeonatos",
            labels,
            default=labels[-min(3, len(labels)) :],
        )
        selected_years = [row["year"] for row, label in zip(options, labels) if label in selected]
        if mode in ("Time to event position", "Tiempo a posici\u00f3n en campeonato"):
            time_value = _time_or_sport_unit("Time", segment, modality, key="event_cmp_time", locale=locale)
            return {
                **base,
                "intent": "event_time_to_position",
                "segment": segment,
                "time_value": time_value,
                "event_years": selected_years,
                "min_n": int(min_n),
            }
        percentile = _percentile_input("Percentile", key="event_cmp_percentile", locale=locale)
        return {
            **base,
            "intent": "event_time_by_percentile",
            "segment": segment,
            "percentile": percentile,
            "event_years": selected_years,
            "min_n": int(min_n),
        }

    if query_type == "Conditional segment percentile":
        target_segment = st.selectbox(
            _field_label(locale, "Target segment"),
            MAIN_SEGMENTS,
            index=2,
            format_func=lambda value: _segment_label(locale, value),
        )
        target_time = _time_or_sport_unit("Target time", target_segment, modality, key="cond_target", locale=locale)
        payload = {
            **base,
            "intent": "conditional_segment_percentile",
            "target_segment": target_segment,
            "target_time": target_time,
        }
        _condition_controls(payload, 1, target_segment, modality, locale)
        use_second = st.checkbox(_field_label(locale, "Add second condition"))
        if use_second:
            _condition_controls(payload, 2, target_segment, modality, locale)
        return payload

    if query_type == "Explain percentile":
        percentile = _percentile_input("Percentile", key="explain_percentile", locale=locale)
        scope = st.selectbox(
            _field_label(locale, "Scope"),
            ("Total", "Swim", "Bike", "Run", "Segment profile"),
            format_func=lambda value: _segment_label(locale, value),
        )
        return {"intent": "explain_percentile", "percentile": percentile, "scope": scope}

    return None


def _condition_controls(payload: dict[str, Any], index: int, target_segment: str, modality: str, locale: str = "en") -> None:
    available = [segment for segment in MAIN_SEGMENTS if segment != target_segment]
    prefix = f"condition_{index}"
    st.subheader(f"Condition {index}" if locale == "en" else f"Condici\u00f3n {index}")
    segment = st.selectbox(
        f"Condition {index} segment" if locale == "en" else f"Segmento de condici\u00f3n {index}",
        available,
        key=f"{prefix}_segment",
        format_func=lambda value: _segment_label(locale, value),
    )
    operator_label = st.selectbox(
        f"Condition {index} operator" if locale == "en" else f"Operador de condici\u00f3n {index}",
        tuple(CONDITION_OPERATORS),
        key=f"{prefix}_operator",
    )
    operator = CONDITION_OPERATORS[operator_label]
    payload[f"{prefix}_segment"] = segment
    payload[f"{prefix}_operator"] = operator
    if operator == "between":
        col1, col2 = st.columns(2)
        with col1:
            payload[f"{prefix}_lower_time"] = _time_or_sport_unit("Lower time", segment, modality, key=f"{prefix}_lower", locale=locale)
        with col2:
            payload[f"{prefix}_upper_time"] = _time_or_sport_unit("Upper time", segment, modality, key=f"{prefix}_upper", locale=locale)
    else:
        payload[f"{prefix}_time"] = _time_or_sport_unit("Condition time", segment, modality, key=f"{prefix}_time", locale=locale)


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
