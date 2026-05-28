from __future__ import annotations

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
from scripts.ai_query_streamlit import (  # noqa: E402
    _context_controls,
    _guided_payload,
    _language_control,
    _run_payload,
    _ui,
)


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


def _guided_query(modality: str, sex_category: str, age_group: str, locale: str) -> None:
    payload = _guided_payload(modality, sex_category, age_group, locale)
    if not payload:
        return
    if st.button(_ui(locale, "get_answer"), type="primary"):
        try:
            _show_clean_response(_run_payload(payload), locale)
        except Exception:
            st.error("No pude completar la consulta. Revisa los datos e intenta de nuevo." if locale == "es" else "I could not complete the query. Please check the inputs and try again.")


def _dialog_query(modality: str, sex_category: str, age_group: str, locale: str) -> None:
    st.caption(
        "Usa el contexto seleccionado a la izquierda, o incluye modalidad, sexo y grupo por edad en la pregunta."
        if locale == "es"
        else "Use the same context selected on the left, or include modality, sex, and age group in the question."
    )
    question = st.text_area(
        "Pregunta" if locale == "es" else "Question",
        placeholder="Que percentil es un Run de 45:00?" if locale == "es" else "What percentile is a 45:00 run?",
        height=120,
    )
    if st.button(_ui(locale, "ask"), type="primary", disabled=not question.strip()):
        try:
            response = answer_natural_language_query(
                question.strip(),
                context={
                    "modality": modality,
                    "sex_category": sex_category,
                    "age_group": age_group,
                    "response_language": "Spanish" if locale == "es" else "English",
                },
                api_key=_openai_api_key(),
                timeout=45,
            )
        except LLMClientError:
            st.error("El asistente de IA no esta disponible ahora. Intenta una consulta guiada." if locale == "es" else "The AI assistant is not available right now. Please try a guided query.")
        except ValueError:
            st.error("No pude entender la pregunta. Intenta una consulta guiada." if locale == "es" else "I could not understand the question. Please try a guided query.")
        else:
            _show_clean_response(response, locale)


def _attribution(locale: str) -> None:
    st.divider()
    if locale == "es":
        st.caption(
            "Tablas de desempeno y percentiles elaboradas por P. Vizcaya a partir de resultados "
            "publicados por World Triathlon."
        )
    else:
        st.caption(
            "Performance and percentile tables developed by P. Vizcaya using results published "
            "by World Triathlon."
        )


def main() -> None:
    st.set_page_config(page_title="Triathlon Performance", layout="wide")
    st.title("Triathlon Performance")

    locale = _language_control()
    modality, sex_category, age_group = _context_controls(locale)
    guided, dialog = st.tabs([_ui(locale, "guided_query"), "Hacer una pregunta" if locale == "es" else "Ask a question"])

    with guided:
        _guided_query(modality, sex_category, age_group, locale)

    with dialog:
        _dialog_query(modality, sex_category, age_group, locale)

    _attribution(locale)


if __name__ == "__main__":
    main()
