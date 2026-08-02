"""Pestaña: catálogo de las tres especies que reconoce el modelo."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core import datos
from core.theme import ESPECIE_COLOR, OLIVA_OSCURO, tag_enfermedad, tag_impacto

RAIZ = Path(__file__).resolve().parent.parent
CSV_RESUMEN = RAIZ / "data" / "procesado" / "resumen_especie.csv"
CSV_FOTOS = RAIZ / "data" / "procesado" / "fotos_muestra.csv"


@st.cache_data
def _resumen() -> pd.DataFrame:
    """Métricas por especie que dejó el pipeline de ingesta."""
    if not CSV_RESUMEN.exists():
        return pd.DataFrame()
    return pd.read_csv(CSV_RESUMEN)


@st.cache_data
def _fotos() -> pd.DataFrame:
    if not CSV_FOTOS.exists():
        return pd.DataFrame()
    return pd.read_csv(CSV_FOTOS)


def render() -> None:
    st.subheader("Catálogo de especies")
    st.write("Las tres especies que el modelo sabe reconocer. El catálogo, el mapa "
             "y el análisis se limitan a estas tres.")

    especies = datos.cargar_especies()
    resumen = _resumen()
    fotos = _fotos()

    # Con tres fichas no hace falta buscador ni filtro por tipo: se ven todas de
    # una vez, y las tres son mamíferos.
    for _, f in especies.iterrows():
        _ficha(f, resumen, fotos)

    st.divider()
    _seccion_modelo()


def _ficha(f: pd.Series, resumen: pd.DataFrame, fotos: pd.DataFrame) -> None:
    color = ESPECIE_COLOR.get(f["nombre_comun"], OLIVA_OSCURO)

    with st.container(border=True):
        col_img, col_txt = st.columns([1, 2], gap="large")

        with col_img:
            # Cadena de prioridad: foto propia del equipo, luego la de GBIF del
            # catalogo, luego Wikipedia. La resuelve core.datos.
            url = datos.imagen_especie(
                f["nombre_comun"], f.get("nombre_cientifico", ""), f.get("imagen_url"))
            if url:
                st.image(str(url), width="stretch")
                if datos.imagen_especie_local(f["nombre_comun"]):
                    st.caption("Foto propia del equipo.")
                else:
                    st.caption("Foto real de GBIF, tomada en Chile.")
            else:
                st.info("Sin foto disponible.")

        with col_txt:
            es_vector = str(f.get("portador_enfermedades", "")).strip().lower() in ["si", "sí", "true", "1"]
            tag_vect = f" &nbsp;{tag_enfermedad()}" if es_vector else ""

            st.markdown(
                f'<h4 style="margin:0"><span style="color:{color}">●</span> '
                f'{f["nombre_comun"]}</h4>', unsafe_allow_html=True)
            st.markdown(f'*{f["nombre_cientifico"]}* &nbsp;|&nbsp; '
                        f'{tag_impacto(f["impacto_ambiental"])}{tag_vect}',
                        unsafe_allow_html=True)
            st.write(f["descripcion"])
            st.caption(f"🏛️ Avisar a **{f['autoridad']}**")

            fila = resumen[resumen["nombre_comun"] == f["nombre_comun"]]
            if not fila.empty:
                r = fila.iloc[0]
                m = st.columns(4)
                m[0].metric("Registros", f"{int(r['registros']):,}")
                m[1].metric("En zona urbana", f"{r['pct_urbano']:.1f}%")
                m[2].metric("Regiones", int(r["regiones"]))
                m[3].metric("Periodo", f"{int(r['anio_primero'])}–{int(r['anio_ultimo'])}")

            n_fotos = len(fotos[fotos["nombre_comun"] == f["nombre_comun"]]) if "nombre_comun" in fotos.columns else 0
            if n_fotos:
                with st.expander(f"Ver {n_fotos} fotos de referencia"):
                    _galeria(fotos[fotos["nombre_comun"] == f["nombre_comun"]])


def _galeria(sub: pd.DataFrame) -> None:
    cols = st.columns(4)
    for i, (_, r) in enumerate(sub.iterrows()):
        with cols[i % 4]:
            st.image(str(r["foto_url"]), width="stretch")
            lugar = r.get("comuna") or r.get("region") or ""
            anio = f" · {int(r['anio'])}" if pd.notna(r.get("anio")) else ""
            st.caption(f"{lugar}{anio}")


def _seccion_modelo() -> None:
    from core import modelo

    st.markdown("##### El modelo de reconocimiento")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
- Arquitectura: **YOLO11s** (detección de objetos)
- Entrenamiento: 554 imágenes anotadas, en Kaggle (GPU T4)
- Clases: `jabali`, `liebre`, `rata gris`
- Devuelve la especie con mayor confianza de la foto
""")
    with c2:
        st.markdown("**Umbral de confirmación por especie**")
        for etiqueta, umbral in modelo.UMBRALES_POR_ESPECIE.items():
            nombre = modelo.MAPA_ETIQUETAS.get(etiqueta, etiqueta)
            st.markdown(f"- {nombre}: **{umbral:.0%}**")
        st.caption("Bajo ese umbral la detección se informa como coincidencia "
                   "parcial y no habilita el envío de una alerta.")

    st.caption("El modelo solo puede reconocer estas tres clases: cualquier otra "
               "especie fotografiada quedará sin identificar.")
