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
from scripts.ai_query_streamlit import _context_controls, _guided_payload, _run_payload  # noqa: E402


def _openai_api_key() -> str | None:
    try:
        key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        key = None
    return str(key) if key else None


def _answer_text(response: dict[str, Any]) -> str:
    return str(
        response.get("message")
        or response.get("explanation")
        or "I could not produce an answer for that query."
    )


def _show_clean_response(response: dict[str, Any]) -> None:
    text = _answer_text(response)
    if response.get("needs_clarification"):
        st.warning(text)
    elif response.get("valid", False):
        st.success(text)
    else:
        st.error(text)


def _guided_query(modality: str, sex_category: str, age_group: str) -> None:
    payload = _guided_payload(modality, sex_category, age_group)
    if not payload:
        return
    if st.button("Get answer", type="primary"):
        try:
            _show_clean_response(_run_payload(payload))
        except Exception:
            st.error("I could not complete the query. Please check the inputs and try again.")


def _dialog_query(modality: str, sex_category: str, age_group: str) -> None:
    st.caption("Use the same context selected on the left, or include modality, sex, and age group in the question.")
    question = st.text_area(
        "Question",
        placeholder="What percentile is a 45:00 run?",
        height=120,
    )
    if st.button("Ask", type="primary", disabled=not question.strip()):
        try:
            response = answer_natural_language_query(
                question.strip(),
                context={"modality": modality, "sex_category": sex_category, "age_group": age_group},
                api_key=_openai_api_key(),
                timeout=45,
            )
        except LLMClientError:
            st.error("The AI assistant is not available right now. Please try a guided query.")
        except ValueError:
            st.error("I could not understand the question. Please try a guided query.")
        else:
            _show_clean_response(response)


def main() -> None:
    st.set_page_config(page_title="Triathlon Performance", layout="wide")
    st.title("Triathlon Performance")

    modality, sex_category, age_group = _context_controls()
    guided, dialog = st.tabs(["Guided query", "Ask a question"])

    with guided:
        _guided_query(modality, sex_category, age_group)

    with dialog:
        _dialog_query(modality, sex_category, age_group)


if __name__ == "__main__":
    main()
