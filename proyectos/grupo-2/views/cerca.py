"""Pestaña: donde se ha registrado cada una de las tres especies del proyecto."""

from __future__ import annotations

import pandas as pd
import pydeck as pdk
import streamlit as st

from core import datos, ubicacion
from core.theme import ESPECIE_COLOR, ESPECIE_RGB, ficha_especie

# Con ~49.000 registros reales el círculo de 8 km por avistamiento que usaba el
# prototipo tapaba el mapa entero. Cada registro es una observación puntual, no
# un area de afectación, así que va como punto pequeño y la densidad se lee por
# acumulación. El radio se mantiene en metros para que escale con el zoom.
RADIO_PUNTO_M = 900
RADIO_MIN_PX = 2

# Basemap claro (Carto Positron). Sin esto pydeck cae en su estilo oscuro por
# defecto, que rompe la identidad clara de la marca y además invalida el
# contraste de los colores de especie: están verificados contra fondo claro.
# Carto no exige token, así que funciona igual en local y en Streamlit Cloud.
MAPA_ESTILO = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"


def render() -> None:
    ubi = ubicacion.actual()
    st.subheader("Registros de las tres especies en tu área")
    st.write(f"Avistamientos a menos de **{ubi['radio_km']} km** de "
             f"**{ubi['region']}**. Cambia la zona en la barra lateral.")

    cerca = datos.avistamientos_cerca(ubi["lat"], ubi["lon"], ubi["radio_km"])

    if cerca.empty:
        st.info("Sin registros en tu zona. Prueba ampliando el radio en la barra lateral.")
        return

    cerca = _filtros(cerca)

    if cerca.empty:
        st.info("Sin registros para esos filtros. Prueba ampliando el radio o "
                "quitando algún filtro.")
        return

    _resumen(cerca)
    st.divider()

    col_mapa, col_lista = st.columns([1.35, 1], gap="large")
    with col_mapa:
        _mapa(cerca, ubi["lat"], ubi["lon"])
    with col_lista:
        _lista(cerca)

    with st.expander(f"Ver los {len(cerca):,} registros en tabla"):
        _tabla(cerca)


# --------------------------------------------------------------------------
# Filtros
# --------------------------------------------------------------------------
def _filtros(cerca: pd.DataFrame) -> pd.DataFrame:
    """Una fila de filtros sobre los ejes que de verdad discriminan.

    Ya no filtramos por 'tipo': las tres especies son mamíferos y el filtro no
    separaba nada. Lo que sí separa a estas tres es la especie, el entorno
    urbano/rural y —sobre todo— la fuente que generó el registro.
    """
    f = st.columns([1.1, 1, 1.4])

    especies = sorted(cerca["nombre_comun"].unique())
    sel_esp = f[0].multiselect("Especie", especies, default=especies)

    entornos = [e for e in datos.ENTORNOS if e in set(cerca["entorno"])]
    sel_ent = f[1].multiselect("Entorno", entornos, default=entornos)

    fuentes = sorted(cerca["fuente"].dropna().unique())
    sel_fue = f[2].multiselect("Fuente del registro", fuentes, default=fuentes,
                               help="El 98% de los registros viene del monitoreo con "
                                    "cámaras trampa de CONAF en áreas silvestres. "
                                    "Filtra por fuente para no confundir dónde está "
                                    "la especie con donde se instalaron cámaras.")

    out = cerca[cerca["nombre_comun"].isin(sel_esp)
                & cerca["entorno"].isin(sel_ent)
                & cerca["fuente"].isin(sel_fue)]

    # La advertencia más importante de esta vista.
    if len(sel_fue) > 1:
        st.caption("⚠️ Estás viendo varias fuentes juntas. El patrón que se ve en el "
                   "mapa mezcla donde están los animales con donde se observó: "
                   "las cámaras trampa no cubren ciudades y la ciencia ciudadana "
                   "casi no cubre áreas remotas.")

    return out


# --------------------------------------------------------------------------
# Resumen
# --------------------------------------------------------------------------
def _resumen(cerca: pd.DataFrame) -> None:
    c = st.columns(4)
    c[0].metric("Registros", f"{len(cerca):,}")
    c[1].metric("Especies presentes", cerca["nombre_comun"].nunique())
    urb = (cerca["entorno"] == "Urbano").mean() * 100
    c[2].metric("En zona urbana", f"{urb:.0f}%")
    c[3].metric("Más cercano", f"{cerca['distancia_km'].min():.0f} km")

    # Desglose por especie con su color de identidad, para que la leyenda del
    # mapa quede establecida antes de mirarlo.
    conteo = cerca["nombre_comun"].value_counts()
    chips = " &nbsp; ".join(
        f'<span style="display:inline-block;width:11px;height:11px;border-radius:3px;'
        f'background:{ESPECIE_COLOR.get(n, "#8A8A82")};margin-right:5px;'
        f'vertical-align:middle"></span>{n}: <b>{v:,}</b>'
        for n, v in conteo.items()
    )
    st.markdown(chips, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Mapa
# --------------------------------------------------------------------------
def _mapa(cerca: pd.DataFrame, lat_centro: float, lon_centro: float) -> None:
    st.markdown("##### Mapa de registros")

    df = cerca[["lat", "lon", "nombre_comun", "nombre_cientifico", "comuna",
                "region", "estado", "entorno", "fuente"]].copy()
    df["fecha_txt"] = cerca["fecha"].dt.strftime("%d-%m-%Y")

    # El color codifica la especie, no el impacto ambiental: con solo tres
    # especies la identidad es la pregunta interesante, y el impacto ya sale
    # etiquetado en las fichas.
    df["color"] = df["nombre_comun"].map(
        lambda n: ESPECIE_RGB.get(n, [138, 138, 130]) + [170])

    capa = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius=RADIO_PUNTO_M,
        radius_min_pixels=RADIO_MIN_PX,
        stroked=False,
        filled=True,
        pickable=True,
    )

    # Punto de referencia de la persona, para ubicarse en el mapa.
    centro = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lat": lat_centro, "lon": lon_centro}]),
        get_position=["lon", "lat"],
        get_fill_color=[43, 43, 38, 0],
        get_line_color=[43, 43, 38, 220],
        get_radius=2500,
        radius_min_pixels=6,
        stroked=True,
        filled=False,
        line_width_min_pixels=2,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[capa, centro],
        map_style=MAPA_ESTILO,
        initial_view_state=pdk.ViewState(latitude=lat_centro, longitude=lon_centro,
                                         zoom=6, pitch=0),
        tooltip={"html": "<b>{nombre_comun}</b> (<i>{nombre_cientifico}</i>)<br/>"
                         "📍 {comuna}, {region}<br/>"
                         "📅 {fecha_txt} &nbsp;·&nbsp; {entorno}<br/>"
                         "🔍 {fuente}"},
    ))

    leyenda = " &nbsp;&nbsp; ".join(
        f'<span style="color:{ESPECIE_COLOR[n]};font-size:1.2rem;'
        f'vertical-align:middle">●</span> {n}'
        for n in sorted(df["nombre_comun"].unique()) if n in ESPECIE_COLOR
    )
    st.markdown(f"<div style='font-size:0.85rem'>{leyenda}</div>", unsafe_allow_html=True)
    st.caption("Cada punto es una observación registrada, no un área de afectación. "
               "Las zonas más saturadas concentran más observaciones.")


# --------------------------------------------------------------------------
# Lista y tabla
# --------------------------------------------------------------------------
def _lista(cerca: pd.DataFrame) -> None:
    st.markdown("##### Las más cercanas")
    resumen = (cerca.sort_values("distancia_km")
                    .drop_duplicates("nombre_comun")
                    .head(3))
    for _, f in resumen.iterrows():
        detalle = (f"A {f['distancia_km']:.0f} km · {f['comuna']}, {f['region']} · "
                   f"visto el {f['fecha']:%d-%m-%Y} · {f['entorno'].lower()}")
        es_vector = str(f.get("portador_enfermedades", "")).strip().lower() in ["si", "sí", "true", "1"]
        # La ficha muestra un placeholder si no recibe foto, así que le pasamos la
        # misma que usa el catalogo (esta cacheada: son solo tres especies).
        foto = datos.imagen_especie(f["nombre_comun"], f.get("nombre_cientifico", ""),
                                    f.get("imagen_url"))
        st.markdown(
            ficha_especie(f["nombre_comun"], f["nombre_cientifico"], f["impacto_ambiental"],
                          detalle, imagen_url=foto, portador_enfermedades=es_vector),
            unsafe_allow_html=True,
        )

    # Cuenta por especie sobre el total filtrado, no solo las tres mostradas.
    st.caption("Registros por especie en el radio seleccionado: " + " · ".join(
        f"{n} {v:,}" for n, v in cerca["nombre_comun"].value_counts().items()))


def _tabla(cerca: pd.DataFrame) -> None:
    """Vista de datos: el respaldo accesible de todo lo que muestra el mapa."""
    cols = ["nombre_comun", "nombre_cientifico", "comuna", "region", "fecha",
            "entorno", "fuente", "estado", "distancia_km"]
    st.dataframe(
        cerca[cols].rename(columns={
            "nombre_comun": "Especie", "nombre_cientifico": "Nombre cientifico",
            "comuna": "Comuna", "region": "Región", "fecha": "Fecha",
            "entorno": "Entorno", "fuente": "Fuente", "estado": "Estado",
            "distancia_km": "Distancia (km)"}),
        hide_index=True, width="stretch",
        column_config={"Fecha": st.column_config.DateColumn(format="DD-MM-YYYY")},
    )
