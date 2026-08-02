"""Ubicación del usuario, compartida por todas las pestañas.

Hoy la región se elige a mano en la barra lateral.
"""

from __future__ import annotations

import streamlit as st

from core.datos import REGIONES

REGION_POR_DEFECTO = "Metropolitana"


def _al_cambiar_region():
    """Callback que actualiza automáticamente las coordenadas al cambiar de región."""
    reg = st.session_state.get("ubi_region")
    if reg and reg in REGIONES:
        lat_ref, lon_ref = REGIONES[reg]
        st.session_state["ubi_lat"] = float(lat_ref)
        st.session_state["ubi_lon"] = float(lon_ref)


def selector_sidebar() -> dict:
    """Dibuja el selector de zona en la barra lateral y devuelve la ubicación."""
    with st.sidebar:
        st.markdown("### 📍 Tu zona")

        if "ubi_region" not in st.session_state:
            st.session_state["ubi_region"] = REGION_POR_DEFECTO

        reg_actual = st.session_state.get("ubi_region", REGION_POR_DEFECTO)
        lat_ref, lon_ref = REGIONES.get(reg_actual, REGIONES[REGION_POR_DEFECTO])

        if "ubi_lat" not in st.session_state:
            st.session_state["ubi_lat"] = float(lat_ref)
        if "ubi_lon" not in st.session_state:
            st.session_state["ubi_lon"] = float(lon_ref)

        # Sin 'index': el valor vive en session_state bajo la key 'ubi_region',
        # y pasar ambos hace que Streamlit avise que el default se ignora.
        region = st.selectbox(
            "Región",
            list(REGIONES),
            key="ubi_region",
            on_change=_al_cambiar_region,
        )

        radio = st.slider("Radio de búsqueda (km)", 25, 500, 150, step=25, key="ubi_radio")

        with st.expander("Ajustar coordenadas"):
            lat = st.number_input("Latitud", format="%.4f", key="ubi_lat")
            lon = st.number_input("Longitud", format="%.4f", key="ubi_lon")

        st.caption("Registros reales de GBIF para las tres especies del proyecto.")

    return {"region": region, "lat": lat, "lon": lon, "radio_km": radio}


def actual() -> dict:
    """Ubicación vigente, para usar desde cualquier vista."""
    region = st.session_state.get("ubi_region", REGION_POR_DEFECTO)
    lat_ref, lon_ref = REGIONES.get(region, REGIONES[REGION_POR_DEFECTO])
    return {
        "region": region,
        "lat": st.session_state.get("ubi_lat", lat_ref),
        "lon": st.session_state.get("ubi_lon", lon_ref),
        "radio_km": st.session_state.get("ubi_radio", 150),
    }
