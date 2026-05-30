from __future__ import annotations

import html

import streamlit as st

from scripts.ironman_query import (
    cube_times_query,
    curve_query,
    event_percentile_query,
    event_time_query,
    evaluate_profile,
    gap_query,
    load_index,
    list_event_options,
    pair_times_query,
    required_segment_query,
)


SEGMENTS = ("Swim", "T1", "Bike", "T2", "Run")
MAIN_SEGMENTS = ("Swim", "Bike", "Run")
PAIR_SEGMENTS = {
    "swim_bike": ("Swim", "Bike"),
    "swim_run": ("Swim", "Run"),
    "bike_run": ("Bike", "Run"),
}
ROUTES = {
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
        "Explain percentile",
    ),
}


def _text(locale: str, en: str, es: str) -> str:
    return es if locale == "es" else en


def _segment(locale: str, value: str) -> str:
    if locale == "es":
        return {"Swim": "Natación", "Bike": "Bicicleta", "Run": "Carrera", "Total": "Total"}.get(value, value)
    return value


def _modality(locale: str, value: str) -> str:
    if locale == "es":
        return {"Ironman 70.3": "Media Distancia", "Ironman": "Larga Distancia"}.get(value, value)
    return value


def _internal_sex(value: str) -> str:
    return "O" if value == "M" else value


def _context(locale: str, modality: str, sex: str, age_group: str) -> str:
    return f"{_modality(locale, modality)} {sex} {age_group}"


def _interpret(locale: str, percentile: float) -> str:
    return _text(
        locale,
        f"This performance is better than approximately {percentile:.1f}% of comparable athletes.",
        f"Este desempeño supera aproximadamente al {percentile:.1f}% de los deportistas comparables.",
    )


def _card(label: str, value: str, detail: str) -> None:
    st.markdown(
        f"""
        <div class="gtc-result-card">
            <div class="gtc-result-label">{html.escape(label)}</div>
            <div class="gtc-result-value">{html.escape(value)}</div>
            <div class="gtc-result-detail">{html.escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _time(label: str, key: str, placeholder: str = "40:00") -> str:
    return st.text_input(label, placeholder=placeholder, key=key)


def _default_times(modality: str) -> dict[str, str]:
    if modality == "Ironman":
        return {"Total": "11:00:00", "Swim": "1:10:00", "Bike": "5:30:00", "Run": "4:00:00"}
    return {"Total": "5:30:00", "Swim": "35:00", "Bike": "2:45:00", "Run": "1:45:00"}


def _percentile(label: str, key: str) -> float:
    return float(st.slider(label, min_value=0, max_value=100, value=75, step=1, key=key))


def _show_curve(locale: str, context: str, result: dict) -> None:
    segment = _segment(locale, result["segment"])
    if "performance_percentile" in result:
        percentile = float(result["performance_percentile"])
        _card(f"{context} | {segment}", f"P{percentile:.1f}", f"{segment}: {result['time']}. {_interpret(locale, percentile)}")
    else:
        percentile = float(result["percentile"])
        _card(f"{context} | {segment} P{percentile:.1f}", result["time"], _text(locale, "Estimated reference time.", "Tiempo de referencia estimado."))


def _show_pair(locale: str, context: str, result: dict) -> None:
    percentile = float(result["joint_pair_percentile"])
    x_segment = _segment(locale, result["x_segment"])
    y_segment = _segment(locale, result["y_segment"])
    detail = _text(
        locale,
        f"{x_segment} {result['input_x_time']} and {y_segment} {result['input_y_time']}. This is a joint percentile, not an average of the two marginal percentiles.",
        f"{x_segment} {result['input_x_time']} y {y_segment} {result['input_y_time']}. Es un percentil conjunto, no el promedio de los dos percentiles marginales.",
    )
    _card(f"{context} | {x_segment} + {y_segment}", f"P{percentile:.1f}", f"{detail} {_interpret(locale, percentile)}")


def _show_cube(locale: str, context: str, result: dict) -> None:
    percentile = float(result["joint_sbr_percentile"])
    detail = _text(
        locale,
        f"Swim {result['input_swim_time']}, Bike {result['input_bike_time']}, Run {result['input_run_time']}. This is the joint three-segment percentile.",
        f"Natación {result['input_swim_time']}, Bicicleta {result['input_bike_time']}, Carrera {result['input_run_time']}. Este es el percentil conjunto de los tres segmentos principales.",
    )
    _card(f"{context} | {_segment(locale, 'Swim')} + {_segment(locale, 'Bike')} + {_segment(locale, 'Run')}", f"P{percentile:.1f}", f"{detail} {_interpret(locale, percentile)}")


def _show_profile(locale: str, context: str, result: dict) -> None:
    for row in result["segments"]:
        _show_curve(locale, context, row)
    total = result["estimated_total"]
    percentile = float(total["performance_percentile"])
    note = _text(locale, "Median T1 and T2 were added.", "Se agregaron las medianas de T1 y T2.") if result["used_median_transitions"] else ""
    _card(f"{context} | {_text(locale, 'Estimated total', 'Total estimado')}", result["estimated_total_time"], f"P{percentile:.1f}. {note}")
    _show_cube(locale, context, result["cube"])


def _labels(locale: str) -> dict[str, str]:
    return {
        "Evaluate a time": _text(locale, "Evaluate a time", "Evaluar un tiempo"),
        "Find a target time": _text(locale, "Find a target time", "Buscar un tiempo objetivo"),
        "Analyze segments": _text(locale, "Analyze segments", "Evaluar mis segmentos"),
        "Compare with a championship": _text(locale, "Compare with a championship", "Compararme con un campeonato"),
        "Improve toward a goal": _text(locale, "Improve toward a goal", "Mejorar hacia un objetivo"),
        "Advanced / help": _text(locale, "Advanced / help", "Avanzadas / ayuda"),
        "Total time to percentile": _text(locale, "Total time to percentile", "Percentil por tiempo total"),
        "Segment time to percentile": _text(locale, "Segment time to percentile", "Percentil por segmento"),
        "Joint percentile for two main segments": _text(locale, "Joint percentile for two main segments", "Percentil conjunto de dos segmentos principales"),
        "Joint percentile for Swim/Bike/Run": _text(locale, "Joint percentile for Swim/Bike/Run", "Percentil conjunto de Natación/Bicicleta/Carrera"),
        "Percentile to total time": _text(locale, "Percentile to total time", "Tiempo total por percentil"),
        "Percentile to segment time": _text(locale, "Percentile to segment time", "Tiempo de segmento por percentil"),
        "Direct championship comparison": _text(locale, "Direct championship comparison", "Comparación directa con campeonatos"),
        "Estimated total from Swim/Bike/Run": _text(locale, "Estimated total from Swim/Bike/Run", "Total estimado por Natación/Bicicleta/Carrera"),
        "Full split evaluation": _text(locale, "Full split evaluation", "Evaluación completa de segmentos"),
        "Compare segments": _text(locale, "Compare segments", "Comparar segmentos"),
        "Gap to target percentile": _text(locale, "Gap to target percentile", "Brecha frente a percentil objetivo"),
        "Required missing segment for target percentile": _text(locale, "Required missing segment for target percentile", "Segmento faltante para percentil objetivo"),
        "Explain percentile": _text(locale, "Explain percentile", "Explicar percentil"),
    }


def _guided_query(locale: str, modality: str, sex: str, age_group: str) -> None:
    labels = _labels(locale)
    defaults = _default_times(modality)
    internal_sex = _internal_sex(sex)
    context = _context(locale, modality, sex, age_group)
    route = st.radio(_text(locale, "What do you want to do?", "¿Qué quieres hacer?"), tuple(ROUTES), format_func=lambda value: labels[value], horizontal=True)
    query = st.selectbox(_text(locale, "Choose the specific question", "Elige la pregunta específica"), ROUTES[route], format_func=lambda value: labels[value])

    if query == "Total time to percentile":
        value = _time(_text(locale, "Total time", "Tiempo total"), "im_total_time", defaults["Total"])
        if st.button(_text(locale, "Get answer", "Obtener respuesta"), type="primary"):
            _show_curve(locale, context, curve_query(modality, internal_sex, age_group, "Total", value))
    elif query == "Segment time to percentile":
        segment = st.selectbox(_text(locale, "Segment", "Segmento"), SEGMENTS, format_func=lambda value: _segment(locale, value))
        value = _time(_text(locale, "Segment time", "Tiempo del segmento"), "im_segment_time")
        if st.button(_text(locale, "Get answer", "Obtener respuesta"), type="primary"):
            _show_curve(locale, context, curve_query(modality, internal_sex, age_group, segment, value))
    elif query == "Percentile to total time":
        value = _percentile(_text(locale, "Percentile", "Percentil"), "im_total_pct")
        if st.button(_text(locale, "Get answer", "Obtener respuesta"), type="primary"):
            _show_curve(locale, context, curve_query(modality, internal_sex, age_group, "Total", value, by_percentile=True))
    elif query == "Percentile to segment time":
        segment = st.selectbox(_text(locale, "Segment", "Segmento"), SEGMENTS, format_func=lambda value: _segment(locale, value))
        value = _percentile(_text(locale, "Percentile", "Percentil"), "im_segment_pct")
        if st.button(_text(locale, "Get answer", "Obtener respuesta"), type="primary"):
            _show_curve(locale, context, curve_query(modality, internal_sex, age_group, segment, value, by_percentile=True))
    elif query == "Direct championship comparison":
        segment = st.selectbox(_text(locale, "Segment", "Segmento"), ("Total", *SEGMENTS), format_func=lambda value: _segment(locale, value), key="im_event_segment")
        min_n = st.slider(_text(locale, "Minimum category size", "Tamaño mínimo de la categoría"), 1, 100, 20, key="im_event_min_n")
        options = list_event_options(modality, internal_sex, age_group, segment, min_n=min_n)
        event_labels = [f"{row['year']} - {row['event_name']} (n={row['n']})" for row in options]
        selected = st.multiselect(
            _text(locale, "Championships", "Campeonatos"),
            event_labels,
            default=event_labels[-min(3, len(event_labels)):],
            key="im_event_years",
        )
        years = [row["year"] for row, label in zip(options, event_labels) if label in selected]
        mode = st.radio(
            _text(locale, "Mode", "Modo"),
            ("Time to event position", "Event percentile to time"),
            format_func=lambda value: _text(locale, value, "Tiempo a posición en campeonato" if value == "Time to event position" else "Percentil del campeonato a tiempo"),
            horizontal=True,
            key="im_event_mode",
        )
        if mode == "Time to event position":
            value = _time(_text(locale, "Time", "Tiempo"), "im_event_time", defaults["Total"])
        else:
            value = _percentile(_text(locale, "Percentile", "Percentil"), "im_event_pct")
        if st.button(_text(locale, "Get answer", "Obtener respuesta"), type="primary"):
            result = event_time_query(modality, internal_sex, age_group, segment, value, years, min_n=min_n) if mode == "Time to event position" else event_percentile_query(modality, internal_sex, age_group, segment, value, years, min_n=min_n)
            rows = []
            for row in result["comparisons"]:
                rows.append({
                    _text(locale, "Year", "Año"): row["year"],
                    _text(locale, "Championship", "Campeonato"): row["event_name"],
                    "n": row["n"],
                    _text(locale, "Position", "Posición"): round(float(row["estimated_position"]), 1) if row.get("estimated_position") is not None else None,
                    _text(locale, "Percentile", "Percentil"): round(float(row["performance_percentile"]), 1) if "performance_percentile" in row else row.get("percentile"),
                    _text(locale, "Time", "Tiempo"): row.get("estimated_time", row.get("input_time")),
                    _text(locale, "Status", "Estado"): row.get("status", "ok"),
                })
            if rows:
                first = next((row for row in result["comparisons"] if row.get("valid")), None)
                if first:
                    _card(
                        f"{context} | {_segment(locale, segment)} | {first['event_name']}",
                        f"P{first['performance_percentile']:.1f}" if "performance_percentile" in first else first["estimated_time"],
                        _text(locale, "Direct empirical championship comparison; no event-difficulty adjustment is applied.", "Comparación empírica directa con el campeonato; no se aplica ajuste por dificultad del evento."),
                    )
                st.dataframe(rows, hide_index=True, width="stretch")
            else:
                st.warning(_text(locale, "No championships meet the selected criteria.", "Ningún campeonato cumple los criterios seleccionados."))
    elif query == "Joint percentile for two main segments":
        pair = st.selectbox(_text(locale, "Segment pair", "Par de segmentos"), tuple(PAIR_SEGMENTS), format_func=lambda value: " + ".join(_segment(locale, item) for item in PAIR_SEGMENTS[value]))
        x_segment, y_segment = PAIR_SEGMENTS[pair]
        x_time = _time(_segment(locale, x_segment), "im_pair_x")
        y_time = _time(_segment(locale, y_segment), "im_pair_y")
        if st.button(_text(locale, "Get answer", "Obtener respuesta"), type="primary"):
            _show_pair(locale, context, pair_times_query(modality, internal_sex, age_group, pair, x_time, y_time))
    elif query == "Joint percentile for Swim/Bike/Run":
        swim = _time(_segment(locale, "Swim"), "im_cube_swim", defaults["Swim"])
        bike = _time(_segment(locale, "Bike"), "im_cube_bike", defaults["Bike"])
        run = _time(_segment(locale, "Run"), "im_cube_run", defaults["Run"])
        if st.button(_text(locale, "Get answer", "Obtener respuesta"), type="primary"):
            _show_cube(locale, context, cube_times_query(modality, internal_sex, age_group, swim, bike, run))
    elif query in ("Estimated total from Swim/Bike/Run", "Full split evaluation", "Compare segments"):
        swim = _time(_segment(locale, "Swim"), f"im_profile_swim_{query}", defaults["Swim"])
        bike = _time(_segment(locale, "Bike"), f"im_profile_bike_{query}", defaults["Bike"])
        run = _time(_segment(locale, "Run"), f"im_profile_run_{query}", defaults["Run"])
        t1 = t2 = None
        if query != "Estimated total from Swim/Bike/Run":
            t1 = _time("T1", f"im_profile_t1_{query}", "1:30")
            t2 = _time("T2", f"im_profile_t2_{query}", "1:30")
        if st.button(_text(locale, "Get answer", "Obtener respuesta"), type="primary"):
            _show_profile(locale, context, evaluate_profile(modality, internal_sex, age_group, swim, bike, run, t1_time=t1, t2_time=t2))
    elif query == "Gap to target percentile":
        segment = st.selectbox(_text(locale, "Scope", "Alcance"), ("Total", *SEGMENTS), format_func=lambda value: _segment(locale, value))
        current = _time(_text(locale, "Current time", "Tiempo actual"), "im_gap_current")
        target = _percentile(_text(locale, "Target percentile", "Percentil objetivo"), "im_gap_target")
        if st.button(_text(locale, "Get answer", "Obtener respuesta"), type="primary"):
            result = gap_query(modality, internal_sex, age_group, segment, current, target)
            detail = _text(locale, f"Current: P{result['current_percentile']:.1f}. Improvement required: {result['improvement_time']}.", f"Actual: P{result['current_percentile']:.1f}. Mejora requerida: {result['improvement_time']}.")
            _card(f"{context} | {_segment(locale, segment)}", result["target_time"], detail)
    elif query == "Required missing segment for target percentile":
        missing = st.selectbox(_text(locale, "Missing segment", "Segmento faltante"), MAIN_SEGMENTS, format_func=lambda value: _segment(locale, value))
        target = _percentile(_text(locale, "Target total percentile", "Percentil total objetivo"), "im_missing_target")
        known = {segment: _time(_segment(locale, segment), f"im_missing_{segment}") for segment in MAIN_SEGMENTS if segment != missing}
        if st.button(_text(locale, "Get answer", "Obtener respuesta"), type="primary"):
            result = required_segment_query(modality, internal_sex, age_group, missing, target, known)
            detail = _text(locale, f"Estimated with median T1 and T2. Equivalent marginal performance: P{result['required_segment_percentile']:.1f}.", f"Estimado con las medianas de T1 y T2. Desempeño marginal equivalente: P{result['required_segment_percentile']:.1f}.")
            _card(f"{context} | {_segment(locale, missing)}", result["required_time"], detail)
    elif query == "Explain percentile":
        value = _percentile(_text(locale, "Percentile", "Percentil"), "im_explain_pct")
        _card(_text(locale, "Percentile interpretation", "Interpretación del percentil"), f"P{value:.1f}", _interpret(locale, value))


def render_ironman_page(locale: str = "es") -> None:
    index = load_index()
    st.subheader(_text(locale, "Long-distance Triathlon", "Triatlón de Media y Larga Distancia"))
    st.caption(_text(locale, "Swim - T1 - Bike - T2 - Run", "Natación - T1 - Bicicleta - T2 - Carrera"))
    modality = st.sidebar.selectbox(_text(locale, "Modality", "Modalidad"), ("Ironman 70.3", "Ironman"), format_func=lambda value: _modality(locale, value), key="im_modality")
    sex = st.sidebar.selectbox(_text(locale, "Sex", "Sexo"), ("M", "F"), format_func=lambda value: _text(locale, "Male" if value == "M" else "Female", "Masculino" if value == "M" else "Femenino"), key="im_sex")
    internal_sex = _internal_sex(sex)
    ages = sorted(
        {
            key.split("|")[2]
            for key in index["total_curves"]
            if key.startswith(f"{modality}|{internal_sex}|") and key.split("|")[2] != "All"
        },
        key=lambda value: int(value.split("-")[0]),
    )
    age_group = st.sidebar.selectbox(_text(locale, "Age group", "Grupo por edad"), ages, key="im_age")
    st.info(_text(locale, "Guided long-distance triathlon queries are enabled.", "Las consultas guiadas de triatlón de media y larga distancia están habilitadas."))
    _guided_query(locale, modality, sex, age_group)
