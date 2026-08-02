"""Pestaña: el hallazgo del análisis, explicado sin tecnicismos.

Responde la pregunta del proyecto con tres gráficos. El texto está escrito para
alguien que no sabe de datos: nada de 'sesgo de muestreo' ni 'n=43'.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.theme import ESPECIE_COLOR

RAIZ = Path(__file__).resolve().parent.parent
DIR_PROC = RAIZ / "data" / "procesado"

# El orden fija el color de cada serie en los gráficos: Streamlit asigna la
# lista de colores a las columnas en orden, así que columnas y colores tienen
# que ir sincronizados o el jabalí termina pintado de color liebre.
ESPECIES = ["Jabali", "Liebre europea", "Rata gris"]
COLORES = [ESPECIE_COLOR[e] for e in ESPECIES]

COL_A_ESPECIE = {
    "reg_jabali": "Jabali",
    "reg_liebre": "Liebre europea",
    "reg_rata_gris": "Rata gris",
}

# Los nombres completos de fuente no caben en el eje x y se cortan a la mitad.
# OJO: las CLAVES son valores literales de data/procesado/resumen_fuente.csv y van
# sin tilde porque así están escritos en el dato. Las tildes van en el valor, que
# es lo único que se muestra. Ponérsela a la clave no rompe nada visible: el .get()
# cae al nombre largo y las etiquetas del eje vuelven a cortarse, sin ningún error.
FUENTE_CORTA = {
    "Camara trampa (CONAF)": "Cámaras trampa",
    "Ciencia ciudadana (iNaturalist)": "Ciencia ciudadana",
    "Coleccion museologica": "Museos",
    "Otros estudios": "Estudios",
}


@st.cache_data(show_spinner=False)
def _tabla(nombre: str) -> pd.DataFrame:
    ruta = DIR_PROC / f"{nombre}.csv"
    return pd.read_csv(ruta) if ruta.exists() else pd.DataFrame()


def render() -> None:
    st.subheader("Qué encontramos")

    st.markdown("""
Nos preguntamos **dónde vive en Chile cada una de las tres especies invasoras que
la aplicación reconoce**, y si sus territorios se parecen entre sí.

La respuesta corta: **no se parecen en nada**. Y al buscarla apareció algo que
no esperábamos.
""")

    _kpis()
    st.divider()
    _grafico_urbano()
    st.divider()
    _grafico_regiones()
    st.divider()
    _grafico_tiempo()
    st.divider()
    _conclusion()


# --------------------------------------------------------------------------
def _kpis() -> None:
    esp = _tabla("resumen_especie")
    if esp.empty:
        return

    c = st.columns(4)
    c[0].metric("Avistamientos analizados", f"{int(esp['registros'].sum()):,}")

    rata = esp[esp["nombre_comun"] == "Rata gris"]
    liebre = esp[esp["nombre_comun"] == "Liebre europea"]
    if not rata.empty:
        c[1].metric("Rata gris en ciudad", f"{rata['pct_urbano'].iloc[0]:.0f}%")
    if not liebre.empty:
        c[2].metric("Liebre europea en ciudad", f"{liebre['pct_urbano'].iloc[0]:.0f}%")

    fuente = _tabla("resumen_fuente")
    if not fuente.empty:
        # "Camara" sin tilde: busca dentro del valor del CSV, no es texto visible.
        camaras = fuente[fuente["fuente"].str.contains("Camara", case=False, na=False)]
        pct = camaras["registros"].sum() / fuente["registros"].sum() * 100
        c[3].metric("Vienen de cámaras trampa", f"{pct:.0f}%")


# --------------------------------------------------------------------------
def _grafico_urbano() -> None:
    st.markdown("#### 1. Solo una de las tres vive en la ciudad")

    fuente = _tabla("resumen_fuente")
    if fuente.empty:
        st.info("Faltan los datos procesados. Ejecuta `python -m core.ingesta`.")
        return

    tabla = (fuente.assign(fuente=fuente["fuente"].map(
                        lambda f: FUENTE_CORTA.get(f, f)))
                   .pivot_table(index="fuente", columns="nombre_comun",
                                values="pct_urbano", aggfunc="mean")
                   .reindex(columns=ESPECIES))

    # stack=False es obligatorio aquí: son porcentajes de especies distintas y
    # apilarlos daría una barra de "120% urbano", que no significa nada.
    st.bar_chart(tabla, color=COLORES, height=320, stack=False,
                 y_label="% de avistamientos en zona urbana")

    st.markdown("""
Cada grupo de barras es una **forma distinta de observar**: cámaras automáticas en
parques nacionales, gente que fotografía con el celular, museos y estudios.

Miralo así: **la rata gris es la única que aparece en las ciudades**, sin importar
quién la observe. El jabalí y la liebre casi no aparecen. Eso tiene sentido: son
animales de campo y de bosque, y la rata vive donde vivimos nosotros.
""")


# --------------------------------------------------------------------------
def _grafico_regiones() -> None:
    st.markdown("#### 2. Cada especie ocupa un pedazo distinto del país")

    reg = _tabla("resumen_region")
    if reg.empty:
        st.info("Faltan los datos procesados. Ejecuta `python -m core.ingesta`.")
        return

    solo = st.multiselect("Especies a mostrar", ESPECIES, default=ESPECIES,
                          key="hallazgo_especies")
    if not solo:
        st.info("Elige al menos una especie.")
        return

    cols = [e for e in ESPECIES if e in solo]
    tabla = reg.rename(columns=COL_A_ESPECIE).set_index("region")[cols]

    # En números absolutos este gráfico no se puede leer: la liebre tiene 45.778
    # registros y la rata gris 231, así que las barras de rata quedan pegadas al
    # eje. Cada especie se lleva a porcentaje SOBRE SU PROPIO total, que ademas
    # es lo que la pregunta necesita: donde se concentra cada una, no cual tiene
    # mas registros.
    tabla = (tabla / tabla.sum()).mul(100).round(1)
    colores = [ESPECIE_COLOR[e] for e in cols]

    st.bar_chart(tabla, color=colores, height=400, stack=False,
                 y_label="% de los avistamientos de esa especie")

    st.markdown("""
Cada barra dice **qué porcentaje de los avistamientos de esa especie** ocurrió en
esa región. Se comparan así porque hay 45.778 liebres registradas y solo 231 ratas
grises: en números crudos la rata gris sería invisible.

La liebre europea aparece en **todo el país**, de Arica a Magallanes, pero se
concentra en el sur. El jabalí vive casi entero en **Los Lagos**. Y la rata gris es
la más repartida: no domina en ninguna región, aparece un poco en todas.
""")


# --------------------------------------------------------------------------
def _grafico_tiempo() -> None:
    st.markdown("#### 3. El detalle que cambia cómo hay que leer todo lo anterior")

    serie = _tabla("serie_temporal")
    if serie.empty:
        st.info("Faltan los datos procesados. Ejecuta `python -m core.ingesta`.")
        return

    # Una sola línea con el total, no una por especie: el punto de este gráfico
    # es el programa de observación, no la diferencia entre especies. Separarlas
    # aquí solo repetiría el problema de escala del grafico anterior.
    # El año va como fecha, no como número: si se deja numérico, el eje lo
    # formatea con separador de miles y muestra "2,017" en vez de 2017.
    tabla = (serie[serie["anio"] >= 1990]
             .assign(anio=lambda d: pd.to_datetime(d["anio"].astype(int), format="%Y"))
             .set_index("anio")[["total"]]
             .rename(columns={"total": "Avistamientos registrados"}))

    st.line_chart(tabla, color=[ESPECIE_COLOR["Jabali"]], height=320,
                  y_label="Avistamientos por año", x_label="Año")

    st.markdown("""
Casi todos los avistamientos se registraron entre **2017 y 2022**, y después el
gráfico se cae a cero. Las especies no desaparecieron en 2023: lo que terminó fue
**un programa de cámaras trampa de CONAF** que aportó 98 de cada 100 registros.

O sea: este no es un mapa de donde están los animales. Es un mapa de **donde
alguien estuvo mirando**.
""")


# --------------------------------------------------------------------------
def _conclusion() -> None:
    st.markdown("#### Por qué esto justifica la aplicación")

    st.markdown("""
Las cámaras trampa están en parques nacionales y áreas protegidas. Funcionan muy
bien ahí, y por eso sabemos tanto del jabalí y de la liebre.

Pero **nadie puso cámaras en las ciudades**. Y resulta que la rata gris —la única
de las tres que vive en la ciudad, y la única que transmite hantavirus y
leptospirosis— es también la que menos registros tiene: **231 en más de un siglo**,
contra 45.778 de la liebre.

Ese es el vacío. Una persona con un teléfono puede fotografiar y reportar
exactamente lo que el monitoreo oficial no alcanza a ver. No compite con las
cámaras trampa: cubre el territorio al que nunca van a llegar.
""")
