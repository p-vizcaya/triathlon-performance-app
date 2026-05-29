from __future__ import annotations

from typing import Any


def round_percentile(value: Any) -> str:
    number = float(value)
    rounded = round(number, 1)
    if rounded.is_integer():
        return f"P{int(rounded)}"
    return f"P{rounded:.1f}"


def _context(result: dict[str, Any]) -> str:
    return f"{result.get('modality')} {result.get('sex_label')} {result.get('age_group')}"


def _range_note(result: dict[str, Any]) -> str:
    status = result.get("range_status")
    if status == "below_range":
        return " The input is faster than the available reference range, so the result is capped at the top of the curve."
    if status == "above_range":
        return " The input is slower than the available reference range, so the result is capped at the bottom of the curve."
    return ""


def _range_note_es(result: dict[str, Any]) -> str:
    status = result.get("range_status")
    if status == "below_range":
        return " El tiempo ingresado es más rápido que el rango de referencia disponible, así que el resultado queda limitado al extremo superior de la curva."
    if status == "above_range":
        return " El tiempo ingresado es más lento que el rango de referencia disponible, así que el resultado queda limitado al extremo inferior de la curva."
    return ""


def _uncertainty_note(result: dict[str, Any]) -> str:
    # Difficulty-adjusted ranges remain in the payload for internal analysis.
    # Athlete-facing answers report the direct reference-table value.
    return ""


def _uncertainty_note_es(result: dict[str, Any]) -> str:
    return ""
    uncertainty = result.get("uncertainty")
    if not isinstance(uncertainty, dict):
        return ""
    if "recommended_time_fast" in uncertainty and "recommended_time_slow" in uncertainty:
        return (
            f" En campeonatos típicamente fáciles o difíciles, el tiempo equivalente queda aproximadamente entre "
            f"{uncertainty['recommended_time_fast']} y {uncertainty['recommended_time_slow']}."
        )
    if "difficulty_percentile_q25" in uncertainty and "difficulty_percentile_q75" in uncertainty:
        return (
            f" Como no sabemos si el tiempo del atleta viene de un evento facil o dificil respecto a los campeonatos, "
            f"su valor equivalente queda aproximadamente entre P{uncertainty['difficulty_percentile_q25']:.1f} y "
            f"P{uncertainty['difficulty_percentile_q75']:.1f}, usando el rango intercuartilico de dificultad de eventos."
        )
    return ""


def _invalid_message(result: dict[str, Any]) -> str:
    message = result.get("message")
    if message:
        return str(message)
    entity = result.get("entity", "query")
    return f"The {entity} query is not available for {_context(result)}."


def _total_time_explanation(result: dict[str, Any]) -> str:
    if "performance_percentile" in result:
        return (
            f"For {_context(result)}, a total time of {result['input_total_time']} "
            f"corresponds to approximately {round_percentile(result['performance_percentile'])}."
            f"{_uncertainty_note(result)}"
            f"{_range_note(result)}"
        )
    return (
        f"For {_context(result)}, {round_percentile(result['percentile'])} "
        f"corresponds to a total time of approximately {result['total_time']}."
        f"{_uncertainty_note(result)}"
        f"{_range_note(result)}"
    )


def _total_time_explanation_es(result: dict[str, Any]) -> str:
    if "performance_percentile" in result:
        return (
            f"Para {_context(result)}, un tiempo total de {result['input_total_time']} "
            f"corresponde aproximadamente a {round_percentile(result['performance_percentile'])}."
            f"{_range_note_es(result)}"
        )
    return (
        f"Para {_context(result)}, {round_percentile(result['percentile'])} "
        f"corresponde a un tiempo total aproximado de {result['total_time']}."
        f"{_range_note_es(result)}"
    )


def _segment_explanation(result: dict[str, Any]) -> str:
    segment = result.get("segment")
    if "performance_percentile" in result:
        return (
            f"For {_context(result)}, a {segment} time of {result['input_time']} "
            f"corresponds to approximately {round_percentile(result['performance_percentile'])}."
            f"{_uncertainty_note(result)}"
            f"{_range_note(result)}"
        )
    return (
        f"For {_context(result)}, {round_percentile(result['percentile'])} "
        f"corresponds to a {segment} time of approximately {result['time']}."
        f"{_uncertainty_note(result)}"
        f"{_range_note(result)}"
    )


def _segment_explanation_es(result: dict[str, Any]) -> str:
    segment = result.get("segment")
    if "performance_percentile" in result:
        return (
            f"Para {_context(result)}, un tiempo de {segment} de {result['input_time']} "
            f"corresponde aproximadamente a {round_percentile(result['performance_percentile'])}."
            f"{_range_note_es(result)}"
        )
    return (
        f"Para {_context(result)}, {round_percentile(result['percentile'])} "
        f"corresponde a un tiempo aproximado de {segment} de {result['time']}."
        f"{_range_note_es(result)}"
    )


def _derived_total_explanation(result: dict[str, Any]) -> str:
    return (
        f"For {_context(result)}, swim {result['swim_time']}, bike {result['bike_time']}, "
        f"and run {result['run_time']} estimate to a total time of {result['estimated_total_time']} "
        f"after adding average T1 ({result['avg_t1_time']}) and average T2 ({result['avg_t2_time']})."
    )


def _derived_total_explanation_es(result: dict[str, Any]) -> str:
    return (
        f"Para {_context(result)}, swim {result['swim_time']}, bike {result['bike_time']} "
        f"y run {result['run_time']} estiman un tiempo total de {result['estimated_total_time']} "
        f"después de sumar T1 promedio ({result['avg_t1_time']}) y T2 promedio ({result['avg_t2_time']})."
    )


def _estimated_total_percentile_explanation(result: dict[str, Any]) -> str:
    return (
        f"For {_context(result)}, the estimated total time is {result['estimated_total_time']}, "
        f"which corresponds to approximately {round_percentile(result['performance_percentile'])}. "
        f"The estimate adds average T1 ({result['avg_t1_time']}) and average T2 ({result['avg_t2_time']}) "
        f"to the provided swim, bike, and run times."
        f"{_range_note(result)}"
    )


def _estimated_total_percentile_explanation_es(result: dict[str, Any]) -> str:
    return (
        f"Para {_context(result)}, el tiempo total estimado es {result['estimated_total_time']}, "
        f"lo que corresponde aproximadamente a {round_percentile(result['performance_percentile'])}. "
        f"La estimación suma T1 promedio ({result['avg_t1_time']}) y T2 promedio ({result['avg_t2_time']}) "
        f"a los tiempos ingresados de swim, bike y run."
        f"{_range_note_es(result)}"
    )


def _required_run_explanation(result: dict[str, Any]) -> str:
    target = (
        f"{round_percentile(result['target_total_percentile'])} total time"
        if result.get("entity") == "run_time_for_total_percentile"
        else f"a total time of {result['target_total_time']}"
    )
    return (
        f"For {_context(result)}, with swim {result['swim_time']} and bike {result['bike_time']}, "
        f"the required run is approximately {result['required_run_time']} to reach {target}. "
        f"This subtracts average T1 ({result['avg_t1_time']}) and average T2 ({result['avg_t2_time']}) "
        f"from the target total."
    )


def _required_run_explanation_es(result: dict[str, Any]) -> str:
    target = (
        f"un tiempo total {round_percentile(result['target_total_percentile'])}"
        if result.get("entity") == "run_time_for_total_percentile"
        else f"un tiempo total de {result['target_total_time']}"
    )
    return (
        f"Para {_context(result)}, con swim {result['swim_time']} y bike {result['bike_time']}, "
        f"el run requerido es aproximadamente {result['required_run_time']} para alcanzar {target}. "
        f"Esto descuenta T1 promedio ({result['avg_t1_time']}) y T2 promedio ({result['avg_t2_time']}) "
        f"del total objetivo."
    )


def _required_missing_segment_explanation(result: dict[str, Any]) -> str:
    target = (
        f"{round_percentile(result['target_total_percentile'])} total time"
        if result.get("entity") == "required_missing_segment_for_target_percentile"
        else f"a total time of {result['target_total_time']}"
    )
    return (
        f"For {_context(result)}, the required {result['missing_segment']} is approximately "
        f"{result['required_time']} to reach {target}. This uses average T1 "
        f"({result['avg_t1_time']}) and average T2 ({result['avg_t2_time']})."
    )


def _required_missing_segment_explanation_es(result: dict[str, Any]) -> str:
    target = (
        f"un tiempo total {round_percentile(result['target_total_percentile'])}"
        if result.get("entity") == "required_missing_segment_for_target_percentile"
        else f"un tiempo total de {result['target_total_time']}"
    )
    return (
        f"Para {_context(result)}, el {result['missing_segment']} requerido es aproximadamente "
        f"{result['required_time']} para alcanzar {target}. Esto usa T1 promedio "
        f"({result['avg_t1_time']}) y T2 promedio ({result['avg_t2_time']})."
    )


def _gap_explanation(result: dict[str, Any]) -> str:
    if result["direction"] == "already_at_or_above_target":
        return (
            f"For {_context(result)}, current {result['scope']} performance is "
            f"{round_percentile(result['current_percentile'])}, already at or above "
            f"{round_percentile(result['target_percentile'])}."
        )
    return (
        f"For {_context(result)}, current {result['scope']} performance is "
        f"{round_percentile(result['current_percentile'])}. To reach "
        f"{round_percentile(result['target_percentile'])}, the target time is approximately "
        f"{result['target_time']}, requiring an improvement of about {result['improvement_time']}."
    )


def _gap_explanation_es(result: dict[str, Any]) -> str:
    if result["direction"] == "already_at_or_above_target":
        return (
            f"Para {_context(result)}, el desempeño actual en {result['scope']} es "
            f"{round_percentile(result['current_percentile'])}, ya igual o superior a "
            f"{round_percentile(result['target_percentile'])}."
        )
    return (
        f"Para {_context(result)}, el desempeño actual en {result['scope']} es "
        f"{round_percentile(result['current_percentile'])}. Para alcanzar "
        f"{round_percentile(result['target_percentile'])}, el tiempo objetivo es aproximadamente "
        f"{result['target_time']}, lo que requiere mejorar cerca de {result['improvement_time']}."
    )


def _explain_percentile(result: dict[str, Any]) -> str:
    scope = result.get("scope") or "the selected reference group"
    percentile = float(result["percentile"])
    return (
        f"{round_percentile(percentile)} means the performance is better than approximately "
        f"{percentile:.1f}% of {scope}, using the relevant reference curve or joint table."
    )


def _explain_percentile_es(result: dict[str, Any]) -> str:
    scope = result.get("scope") or "el grupo de referencia seleccionado"
    scope_text = "Total" if str(scope).lower() == "total" else str(scope)
    percentile = float(result["percentile"])
    return (
        f"{round_percentile(percentile)} significa que el desempeño es mejor que aproximadamente "
        f"el {percentile:.1f}% de {scope_text}, usando la curva de referencia o tabla conjunta correspondiente."
    )


def _conditional_explanation_es(result: dict[str, Any]) -> str:
    conditions = result.get("conditions") or []
    if conditions:
        text = " y ".join(_condition_text_es(condition) for condition in conditions)
    else:
        text = "las condiciones indicadas"
    return (
        f"Para {_context(result)}, {result.get('target_segment')} corresponde aproximadamente a "
        f"{round_percentile(result['conditional_percentile'])} dentro del grupo definido por {text}."
    )


def _condition_text_es(condition: dict[str, Any]) -> str:
    segment = condition.get("segment")
    operator = condition.get("operator")
    if operator == "between":
        return (
            f"{segment} entre los percentiles "
            f"{condition['lower_performance_percentile']:.1f} y "
            f"{condition['upper_performance_percentile']:.1f}"
        )
    if operator == "slower_than":
        return f"{segment} más lento que el umbral {condition['performance_percentile']:.1f}"
    return f"{segment} al menos tan bueno como el umbral {condition['performance_percentile']:.1f}"


def _event_curve_explanation(result: dict[str, Any]) -> str:
    comparisons = result.get("comparisons") or []
    if not comparisons:
        return str(result.get("message", "No matching championship event curves are available."))
    first = comparisons[0]
    if result.get("query_type") == "time_to_position":
        return (
            f"For {_context(result)}, {result['segment']} {result['input_time']} would rank about "
            f"position {first['estimated_position']} of {first['n']} in {first['event_name']} "
            f"({first['year']}), equivalent to {round_percentile(first['performance_percentile'])}. "
            f"This is a direct empirical comparison with no event-difficulty adjustment."
        )
    return (
        f"For {_context(result)}, {round_percentile(result['percentile'])} in {result['segment']} "
        f"corresponds to about {first['estimated_time']} in {first['event_name']} "
        f"({first['year']}), with n={first['n']}. "
        f"This is a direct empirical championship percentile, not a global-reference equivalent."
    )


def _event_curve_explanation_es(result: dict[str, Any]) -> str:
    comparisons = result.get("comparisons") or []
    if not comparisons:
        return str(result.get("message", "No hay curvas de campeonatos disponibles para esta consulta."))
    first = comparisons[0]
    if result.get("query_type") == "time_to_position":
        return (
            f"Para {_context(result)}, un {result['segment']} de {result['input_time']} habria quedado "
            f"aproximadamente en la posición {first['estimated_position']} de {first['n']} en "
            f"{first['event_name']} ({first['year']}), equivalente a "
            f"{round_percentile(first['performance_percentile'])}. "
            f"Es una comparacion empirica directa, sin ajuste por dificultad del evento."
        )
    return (
        f"Para {_context(result)}, {round_percentile(result['percentile'])} en {result['segment']} "
        f"corresponde aproximadamente a {first['estimated_time']} en {first['event_name']} "
        f"({first['year']}), con n={first['n']}. "
        f"Es un percentil empirico directo del campeonato, no una equivalencia de la referencia global."
    )


def _pair_explanation(result: dict[str, Any]) -> str:
    return (
        f"For {_context(result)}, the {result['pair']} combination "
        f"({result['x_segment']} {round_percentile(result['x_performance_percentile'])}, "
        f"{result['y_segment']} {round_percentile(result['y_performance_percentile'])}) "
        f"corresponds to approximately {round_percentile(result['joint_pair_percentile'])} jointly."
        f"{_range_note(result)}"
    )


def _sbr_explanation(result: dict[str, Any]) -> str:
    return (
        f"For {_context(result)}, the swim-bike-run combination "
        f"(Swim {round_percentile(result['swim_performance_percentile'])}, "
        f"Bike {round_percentile(result['bike_performance_percentile'])}, "
        f"Run {round_percentile(result['run_performance_percentile'])}) "
        f"corresponds to approximately {round_percentile(result['joint_sbr_percentile'])} jointly."
        f"{_range_note(result)}"
    )


def explain_result(result: dict[str, Any], locale: str = "en") -> str:
    if not result.get("valid", True):
        return _invalid_message(result)

    entity = result.get("entity")
    if locale == "es":
        if entity == "total_time_curve":
            return _total_time_explanation_es(result)
        if entity == "segment_curve":
            return _segment_explanation_es(result)
        if entity == "derived_total":
            return _derived_total_explanation_es(result)
        if entity == "estimated_total_percentile":
            return _estimated_total_percentile_explanation_es(result)
        if entity in ("run_time_for_target_total", "run_time_for_total_percentile"):
            return _required_run_explanation_es(result)
        if entity in ("required_missing_segment_for_target_total", "required_missing_segment_for_target_percentile"):
            return _required_missing_segment_explanation_es(result)
        if entity == "gap_to_target_percentile":
            return _gap_explanation_es(result)
        if entity == "compare_segments":
            return str(result.get("summary", "Comparación de segmentos completada."))
        if entity == "explain_percentile":
            return _explain_percentile_es(result)
        if entity == "conditional_segment_percentile":
            return _conditional_explanation_es(result)
        if entity == "event_curve_comparison":
            return _event_curve_explanation_es(result)
        return "La consulta se completo, pero no hay una plantilla de explicacion para este tipo de resultado."
    if locale != "en":
        raise ValueError("Only English and Spanish explanations are currently supported")

    if entity == "total_time_curve":
        return _total_time_explanation(result)
    if entity == "segment_curve":
        return _segment_explanation(result)
    if entity == "derived_total":
        return _derived_total_explanation(result)
    if entity == "estimated_total_percentile":
        return _estimated_total_percentile_explanation(result)
    if entity in ("run_time_for_target_total", "run_time_for_total_percentile"):
        return _required_run_explanation(result)
    if entity in ("required_missing_segment_for_target_total", "required_missing_segment_for_target_percentile"):
        return _required_missing_segment_explanation(result)
    if entity == "gap_to_target_percentile":
        return _gap_explanation(result)
    if entity == "compare_segments":
        return str(result.get("summary", "Segment comparison completed."))
    if entity == "explain_percentile":
        return _explain_percentile(result)
    if entity == "conditional_segment_percentile":
        return str(result.get("summary", "Conditional percentile completed."))
    if entity == "event_curve_comparison":
        return _event_curve_explanation(result)
    if entity == "segment_pair_plane":
        return _pair_explanation(result)
    if entity == "sbr_cube":
        return _sbr_explanation(result)
    return "The query completed, but no explanation template is available for this result type."
