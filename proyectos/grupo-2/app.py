"""Proyecto Innovacien — detección de especies invasoras a partir de fotos.

El proyecto trabaja sobre las TRES especies que el modelo YOLO11 sabe reconocer
—jabalí, liebre europea y rata gris— y solo sobre esas tres. Catálogo, mapa y
análisis comparten ese mismo alcance.

Ejecutar con:  streamlit run app.py
Regenerar los datos:  python -m core.ingesta

Cada pestaña vive en su propio archivo dentro de views/, para que podamos
trabajar en paralelo sin pisarnos.
"""

import streamlit as st

from core import ubicacion
from core.theme import aplicar_tema, encabezado
from views import acerca, alertar, catalogo, cerca, hallazgo, reportes

st.set_page_config(
    page_title="Flora&Fauna Alerta",
    page_icon="🌿",
    layout="wide",
)

aplicar_tema()
encabezado()

# Zona del usuario: la eligen una vez en la barra lateral y la usan todas las pestañas.
ubicacion.selector_sidebar()

# El orden define el orden de las pestañas. La primera es la principal.
PESTANAS = [
    ("🚨 Alertar animal", alertar),
    ("📍 Registros en tu área", cerca),
    ("📊 Qué encontramos", hallazgo),
    ("📖 Catálogo de especies", catalogo),
    ("🗂️ Mis reportes", reportes),
    ("ℹ️ Acerca del proyecto", acerca),
]

for pestana, (_, vista) in zip(st.tabs([t for t, _ in PESTANAS]), PESTANAS):
    with pestana:
        vista.render()

st.divider()
st.caption("Flora&Fauna Alerta · Proyecto Innovacien · modelo YOLO11 entrenado · "
           "avistamientos reales de GBIF (jabalí, liebre europea y rata gris)")
