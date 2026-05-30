from __future__ import annotations

import re
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
from scripts.ai_query.explain import explain_result  # noqa: E402
from scripts.ai_query.normalization import format_seconds, parse_time_to_seconds  # noqa: E402
from scripts.ai_query.query_agent import run_query_agent  # noqa: E402
from scripts import ai_query_streamlit as shared_ui  # noqa: E402


def _noop(*_args: Any, **_kwargs: Any) -> None:
    return None


def _empty_table(_result: dict[str, Any]) -> list[dict[str, Any]]:
    return []


_apply_theme = getattr(shared_ui, "_apply_theme", _noop)
_brand_header = getattr(shared_ui, "_brand_header", _noop)
_context_controls = shared_ui._context_controls
_event_comparison_table = getattr(shared_ui, "_event_comparison_table", _empty_table)
_guided_payload = shared_ui._guided_payload
_language_control = shared_ui._language_control
_result_card = getattr(shared_ui, "_result_card", _noop)
_run_payload = shared_ui._run_payload
_ui = shared_ui._ui


def _init_session_state() -> None:
    st.session_state.setdefault("dialog_history", [])
    st.session_state.setdefault("short_context", {})


def _openai_api_key() -> str | None:
    try:
        key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        key = None
    return str(key) if key else None


def _answer_text(response: dict[str, Any], locale: str = "en") -> str:
    result = response.get("result")
    if locale == "es" and isinstance(result, dict):
        try:
            return explain_result(result, locale="es")
        except Exception:
            pass
    return str(
        response.get("message")
        or response.get("explanation")
        or ("No pude producir una respuesta para esa consulta." if locale == "es" else "I could not produce an answer for that query.")
    )


def _show_clean_response(response: dict[str, Any], locale: str = "en") -> None:
    text = _answer_text(response, locale)
    if response.get("needs_clarification"):
        st.warning(text)
    elif response.get("valid", False):
        st.success(text)
    else:
        st.error(text)
    result = response.get("result")
    if isinstance(result, dict):
        if response.get("valid", False):
            _result_card(result)
        if result.get("entity") == "event_curve_comparison" and result.get("comparisons"):
            st.dataframe(_event_comparison_table(result), hide_index=True, use_container_width=True)


def _show_clean_response_inline(response: dict[str, Any], locale: str = "en") -> None:
    text = _answer_text(response, locale)
    if response.get("needs_clarification"):
        st.warning(text)
    elif response.get("valid", False):
        st.success(text)
    else:
        st.error(text)
    result = response.get("result")
    if isinstance(result, dict):
        if response.get("valid", False):
            _result_card(result)
        if result.get("entity") == "event_curve_comparison" and result.get("comparisons"):
            st.dataframe(_event_comparison_table(result), hide_index=True, use_container_width=True)


def _guided_query(modality: str, sex_category: str, age_group: str, locale: str) -> None:
    payload = _guided_payload(modality, sex_category, age_group, locale)
    if not payload:
        return
    if st.button(_ui(locale, "get_answer"), type="primary"):
        try:
            _show_clean_response(_run_payload(payload), locale)
        except Exception:
            st.error("No pude completar la consulta. Revisa los datos e intenta de nuevo." if locale == "es" else "I could not complete the query. Please check the inputs and try again.")


def _split_questions(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        return lines
    parts = [part.strip() for part in re.split(r"(?<=[?])\s+", text.strip()) if part.strip()]
    return parts or [text.strip()]


def _base_context(modality: str, sex_category: str, age_group: str, locale: str) -> dict[str, Any]:
    return {
        "modality": modality,
        "sex_category": sex_category,
        "age_group": age_group,
        "response_language": "Spanish" if locale == "es" else "English",
        "previous": st.session_state.get("short_context", {}),
    }


def _update_short_context(question: str, response: dict[str, Any], locale: str) -> None:
    parsed = response.get("parsed")
    payload = parsed.get("payload") if isinstance(parsed, dict) else None
    result = response.get("result")
    context: dict[str, Any] = {
        "last_question": question,
        "last_answer": _answer_text(response, locale),
    }
    if isinstance(payload, dict):
        context["last_payload"] = payload
        context["intent"] = payload.get("intent")
    if isinstance(result, dict):
        context["last_result"] = {
            key: value
            for key, value in result.items()
            if key
            in {
                "entity",
                "modality",
                "sex_label",
                "age_group",
                "segment",
                "scope",
                "input_total_time",
                "input_time",
                "total_time",
                "time",
                "performance_percentile",
                "percentile",
            }
        }
    st.session_state["short_context"] = context


def _active_context_text(locale: str) -> str:
    context = st.session_state.get("short_context") or {}
    if not context:
        return "Sin contexto previo." if locale == "es" else "No previous context."
    pieces = []
    if context.get("intent"):
        pieces.append(f"intent: {context['intent']}")
    result = context.get("last_result") or {}
    if result.get("segment"):
        pieces.append(f"segment: {result['segment']}")
    if result.get("input_total_time"):
        pieces.append(f"total: {result['input_total_time']}")
    if result.get("input_time"):
        pieces.append(f"time: {result['input_time']}")
    if result.get("performance_percentile") is not None:
        pieces.append(f"percentile: P{float(result['performance_percentile']):.1f}")
    return " | ".join(pieces) if pieces else str(context.get("last_question", ""))


def _local_follow_up(question: str, modality: str, sex_category: str, age_group: str, locale: str) -> dict[str, Any] | None:
    text = question.lower()
    faster = re.search(
        r"(?:bajo|baja|reduzco|mejoro|lower|drop|improve|faster|mas\s+rapido|más\s+rápido).*?"
        r"(\d{1,2}:\d{2}(?::\d{2})?|\d+(?:\.\d+)?)\s*(?:min|minutos?|minutes?)?",
        text,
    )
    if not faster:
        return None

    previous = st.session_state.get("short_context") or {}
    result = previous.get("last_result") or {}

    current_time = result.get("input_total_time") or result.get("input_time")
    if not current_time:
        return None

    try:
        raw_delta = faster.group(1)
        delta_seconds = parse_time_to_seconds(raw_delta) if ":" in raw_delta else float(raw_delta) * 60
        next_time = format_seconds(max(0, parse_time_to_seconds(current_time) - delta_seconds))
    except Exception:
        return None

    if result.get("entity") == "total_time_curve":
        payload = {
            "intent": "total_percentile_by_time",
            "modality": modality,
            "sex_category": sex_category,
            "age_group": age_group,
            "total_time": next_time,
        }
    elif result.get("entity") == "segment_curve" and result.get("segment"):
        payload = {
            "intent": "segment_percentile_by_time",
            "modality": modality,
            "sex_category": sex_category,
            "age_group": age_group,
            "segment": result["segment"],
            "segment_time": next_time,
        }
    else:
        return None
    response = run_query_agent(payload)
    return {**response, "parsed": {"type": "tool_payload", "payload": payload}}


def _dialog_query(modality: str, sex_category: str, age_group: str, locale: str) -> None:
    st.caption(
        "Usa el contexto seleccionado a la izquierda, o incluye modalidad, sexo y grupo por edad en la pregunta."
        if locale == "es"
        else "Use the same context selected on the left, or include modality, sex, and age group in the question."
    )
    with st.expander("Contexto activo" if locale == "es" else "Active context", expanded=True):
        st.caption(_active_context_text(locale))
        if st.button("Borrar contexto" if locale == "es" else "Reset context"):
            st.session_state["dialog_history"] = []
            st.session_state["short_context"] = {}
            st.rerun()
    question = st.text_area(
        "Pregunta" if locale == "es" else "Question",
        placeholder="Que percentil es un Run de 45:00?" if locale == "es" else "What percentile is a 45:00 run?",
        height=140,
    )
    if st.button(_ui(locale, "ask"), type="primary", disabled=not question.strip()):
        for step in _split_questions(question):
            try:
                response = _local_follow_up(step, modality, sex_category, age_group, locale)
                if response is None:
                    response = answer_natural_language_query(
                        step,
                        context=_base_context(modality, sex_category, age_group, locale),
                        api_key=_openai_api_key(),
                        timeout=45,
                    )
            except LLMClientError:
                response = {
                    "valid": False,
                    "needs_clarification": False,
                    "message": "El asistente de IA no esta disponible ahora. Intenta una consulta guiada."
                    if locale == "es"
                    else "The AI assistant is not available right now. Please try a guided query.",
                }
            except ValueError:
                response = {
                    "valid": False,
                    "needs_clarification": False,
                    "message": "No pude entender la pregunta. Intenta una consulta guiada."
                    if locale == "es"
                    else "I could not understand the question. Please try a guided query.",
                }
            st.session_state["dialog_history"].append({"question": step, "response": response})
            _update_short_context(step, response, locale)
        st.rerun()

    history = st.session_state.get("dialog_history", [])
    if history:
        st.subheader("Historial" if locale == "es" else "History")
    for item in history[-6:]:
        st.markdown(f"**{'Pregunta' if locale == 'es' else 'Question'}:** {item['question']}")
        _show_clean_response_inline(item["response"], locale)


def _attribution(locale: str, source: str = "World Triathlon") -> None:
    st.divider()
    if locale == "es":
        st.caption(
            "Tablas de desempeño y percentiles elaboradas por P. Vizcaya a partir de resultados "
            f"publicados por {source}."
        )
        st.caption("Reportes y comentarios: WhatsApp +57 320 453 5652.")
    else:
        st.caption(
            "Performance and percentile tables developed by P. Vizcaya using results published "
            f"by {source}."
        )
        st.caption("Reports and feedback: WhatsApp +57 320 453 5652.")


def _mobile_sidebar_note(locale: str) -> None:
    st.info(
        "En celular, abre la ventana lateral con `>>` para fijar disciplina, modalidad, sexo y grupo de edad antes del análisis."
        if locale == "es"
        else "On mobile, open the sidebar with `>>` to set discipline, modality, sex, and age group before the analysis."
    )


def main() -> None:
    st.set_page_config(page_title="Triathlon Performance", layout="wide")
    _init_session_state()

    locale = _language_control()
    _apply_theme()
    _brand_header(locale)
    _mobile_sidebar_note(locale)
    discipline = st.sidebar.selectbox("Disciplina" if locale == "es" else "Discipline", ("Triathlon", "Duathlon"))
    if discipline == "Duathlon":
        from scripts.ai_query_streamlit_duathlon import render_duathlon_page

        render_duathlon_page(locale)
        _attribution(locale)
        return
    triathlon_family = st.sidebar.selectbox(
        "Tipo de triatlón" if locale == "es" else "Triathlon type",
        ("Short distance", "Long distance"),
        format_func=lambda value: {
            "Short distance": "Sprint / Distancia Estándar" if locale == "es" else "Sprint / Standard Distance",
            "Long distance": "Media / Larga Distancia" if locale == "es" else "Middle / Long Distance",
        }[value],
    )
    if triathlon_family == "Long distance":
        from scripts.ai_query_streamlit_ironman import render_ironman_page

        render_ironman_page(locale)
        _attribution(locale, "IRONMAN and CoachCox")
        return
    modality, sex_category, age_group = _context_controls(locale)
    guided, dialog = st.tabs([_ui(locale, "guided_query"), "Hacer una pregunta" if locale == "es" else "Ask a question"])

    with guided:
        _guided_query(modality, sex_category, age_group, locale)

    with dialog:
        _dialog_query(modality, sex_category, age_group, locale)

    _attribution(locale)


if __name__ == "__main__":
    main()
