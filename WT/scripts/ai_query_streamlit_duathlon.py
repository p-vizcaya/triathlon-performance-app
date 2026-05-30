from __future__ import annotations

import streamlit as st

from scripts.duathlon_query import cube_query, curve_query, load_index, pair_query


def render_duathlon_page(locale: str = "es") -> None:
    index = load_index()
    st.subheader("Duatlon" if locale == "es" else "Duathlon")
    st.caption("Run1 - T1 - Bike - T2 - Run2")
    modality = st.sidebar.selectbox("Modalidad" if locale == "es" else "Modality", ("Sprint", "Standard"), key="du_modality")
    sex = st.sidebar.selectbox("Sexo", ("O", "F"), key="du_sex")
    ages = sorted({key.split("|")[2] for key in index["total_curves"] if key.startswith(f"{modality}|{sex}|")}, key=lambda x: int(x.split("-")[0]))
    age_group = st.sidebar.selectbox("Grupo por edad" if locale == "es" else "Age group", ages, key="du_age")
    tabs = st.tabs(["Total", "Segmentos", "Bivariados", "Cubo Run1-Bike-Run2"])
    with tabs[0]:
        mode = st.radio("Consulta", ("Tiempo -> percentil", "Percentil -> tiempo"), horizontal=True)
        if mode.startswith("Tiempo"):
            value = st.text_input("Tiempo total", "2:18:00")
            if st.button("Consultar", key="du_total_time"):
                st.json(curve_query(modality, sex, age_group, "Total", value))
        else:
            value = st.slider("Percentil", 1, 99, 50)
            if st.button("Consultar", key="du_total_pct"):
                st.json(curve_query(modality, sex, age_group, "Total", value, by_percentile=True))
    with tabs[1]:
        segment = st.selectbox("Segmento", ("Run1", "T1", "Bike", "T2", "Run2"))
        value = st.text_input("Tiempo", "40:00", key="du_segment_time")
        if st.button("Consultar", key="du_segment"):
            st.json(curve_query(modality, sex, age_group, segment, value))
    with tabs[2]:
        available = sorted({key.split("|")[3] for key in index["pair_planes"] if key.startswith(f"{modality}|{sex}|{age_group}|")})
        pair = st.selectbox("Par", available)
        x = st.slider("Percentil eje X", 5, 95, 50, step=5)
        y = st.slider("Percentil eje Y", 5, 95, 50, step=5)
        if st.button("Consultar", key="du_pair"):
            st.json(pair_query(modality, sex, age_group, pair, x, y))
    with tabs[3]:
        r1 = st.slider("Run1", 5, 95, 50, step=5)
        bike = st.slider("Bike", 5, 95, 50, step=5)
        r2 = st.slider("Run2", 5, 95, 50, step=5)
        if st.button("Consultar", key="du_cube"):
            st.json(cube_query(modality, sex, age_group, r1, bike, r2))
