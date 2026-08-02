"""Identidad visual de Flora&Fauna Alerta: paleta y estilos compartidos.

La paleta sale del logo: fondo hueso, tipografía ciruela, línea de arco en
oliva y tres acentos saturados (bermellon, teal y dorado). El logo tambien
define la forma: arcos y rectangulos de esquina muy redondeada, trazo fino,
mucho aire y sombras casi inexistentes.
"""

import streamlit as st

# --- Superficies -----------------------------------------------------------
HUESO = "#F2F1ED"          # fondo de la app
BLANCO = "#FFFFFF"         # tarjetas
ARENA = "#E6E3D8"          # superficie secundaria, calida
ARENA_SUAVE = "#EDEBE1"    # separadores y rellenos tenues

# --- Tipografia ------------------------------------------------------------
CIRUELA = "#4A2C3F"        # titulos: el color del lettering del logo
CIRUELA_OSCURA = "#38212F"
TEXTO = "#33272E"          # cuerpo, negro calido con matiz ciruela
OLIVA_OSCURO = "#6F6A4E"   # texto secundario (4.83:1 sobre hueso)
OLIVA_TEXTO = "#4F4B35"    # oliva oscurecido, para texto sobre fondo oliva claro.

# --- Linea y decoracion ----------------------------------------------------
OLIVA = "#A8A181"          # arcos, bordes y hojas del logo. SOLO decorativo:
                           # da 2.30:1 sobre hueso, no sirve para texto.
DORADO = "#E9C34A"         # la pina del logo. Decorativo, nunca datos: bajo
                           # protanopia se confunde con el bermellon.

# --- Acentos ---------------------------------------------------------------
BERMELLON = "#D9452B"      # el pajaro rojo. Accion principal y acento.
TEAL = "#2E6B7C"           # la cabeza del pajaro chico.
TEAL_TEXTO = "#1F4E5B"     # teal oscurecido, para texto sobre fondo teal claro.
CARBON = "#3E3345"         # las alas: purpura muy oscuro.

# Variantes oscurecidas para etiquetas con texto blanco encima. El bermellon
# del logo da 4.34:1 con blanco, apenas bajo el 4.5:1 que pide AA en texto
# pequeño, así que las pastillas usan estas y el resto de la interfaz usa el
# color de marca.
BERMELLON_TAG = "#CE3F26"  # 4.81:1 con blanco
DORADO_TAG = "#96660F"     # 4.99:1 con blanco

# Colores por nivel de impacto ambiental. Es una escala ordenada (bajo -> alto),
# no categorias, y todas cumplen AA con texto blanco.
IMPACTO_COLOR = {
    "Alto": BERMELLON_TAG,
    "Medio": DORADO_TAG,
    "Bajo": OLIVA_OSCURO,
}

# La etiqueta sanitaria usa el ciruela de la marca para no competir con la
# escala de impacto: distinto eje, distinto color.
ENFERMEDAD_COLOR = CIRUELA

# Identidad de especie para el mapa y los graficos.
#
# Aqui la marca SI viste los datos, pero solo despues de verificarlo. Los tres
# colores superan 3:1 sobre el fondo claro (WCAG 1.4.11 para objetos graficos)
# y mantienen separacion en protanopia, deuteranopia y tritanopia:
#
#   jabalí vs liebre   peor caso CVD  133.6
#   jabalí vs rata     peor caso CVD   71.3
#   liebre vs rata     peor caso CVD   62.4
#
# El dorado del logo quedo fuera a propósito: bajo protanopia cae a distancia
# 1.7 del bermellon, o sea, el mismo color. Vive en la interfaz, no en los datos.
ESPECIE_COLOR = {
    "Jabali": BERMELLON,           # 3.84:1 sobre hueso
    "Liebre europea": TEAL,        # 5.29:1
    "Rata gris": OLIVA_OSCURO,     # 4.83:1
}

ESPECIE_RGB = {
    "Jabali": [217, 69, 43],
    "Liebre europea": [46, 107, 124],
    "Rata gris": [111, 106, 78],
}

GRIS_NEUTRO = "#8A8A82"

_CSS = f"""
<style>
  /* ---- Lienzo general ---- */
  .stApp {{ background: {HUESO}; }}

  /* ---- Encabezado: el arco del logo, en CSS ---- */
  .inv-hero {{
      background: {BLANCO};
      border: 1.5px solid {OLIVA};
      border-radius: 30px;
      padding: 1.7rem 2.1rem 1.5rem 2.1rem;
      margin-bottom: 0.9rem;
      text-align: center;
  }}
  .inv-hero h1 {{
      margin: 0;
      font-size: 1.9rem;
      font-weight: 800;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: {CIRUELA};
  }}
  .inv-hero .inv-regla {{
      width: 62px;
      height: 2px;
      background: {OLIVA};
      margin: 0.7rem auto 0.6rem auto;
      border-radius: 2px;
  }}
  .inv-hero p {{
      margin: 0;
      font-size: 0.97rem;
      color: {OLIVA_OSCURO};
  }}

  /* ---- Fichas / tarjetas ---- */
  .inv-card {{
      background: {BLANCO};
      border: 1.5px solid {OLIVA};
      border-left: 5px solid {OLIVA};
      border-radius: 22px;
      padding: 0.9rem 1.1rem;
      margin-bottom: 0.7rem;
      overflow: hidden;
      height: 480px;
      display: flex;
      flex-direction: column;
  }}
  .inv-card h4 {{
      margin: 0 0 0.2rem 0;
      color: {CIRUELA};
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
  }}
  .inv-card .sci {{
      font-style: italic;
      color: {OLIVA_OSCURO};
      font-size: 0.88rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
  }}
  .inv-card p {{
      margin: 0.4rem 0 0 0;
      font-size: 0.9rem;
      color: {TEXTO};
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      flex: 1;
  }}
  .inv-card .tags {{ display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.3rem; flex-shrink: 0; }}

  /* ---- Foto de la especie ---- */
  .inv-foto {{
      width: 100%;
      height: 260px;
      object-fit: cover;
      border-radius: 16px;
      margin-bottom: 0.6rem;
      display: block;
      flex-shrink: 0;
  }}
  .inv-foto-placeholder {{
      width: 100%;
      height: 260px;
      border-radius: 16px;
      margin-bottom: 0.6rem;
      flex-shrink: 0;
      background: {ARENA};
      color: {OLIVA_OSCURO};
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.85rem;
  }}

  /* ---- Etiquetas (impacto ambiental / portadora de enfermedades) ---- */
  .inv-tag {{
      display: inline-block;
      padding: 0.14rem 0.65rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
      color: {BLANCO};
  }}

  /* ---- Contenedores con borde de Streamlit (st.container(border=True)) ---- */
  .stApp [data-testid="stVerticalBlockBorderWrapper"] {{
      border-radius: 22px;
  }}

  /* ---- Pestanas ---- */
  .stTabs [data-baseweb="tab-list"] {{
      gap: 0.4rem;
      border-bottom: 1.5px solid {OLIVA};
  }}
  .stTabs [data-baseweb="tab"] {{
      font-weight: 600;
      color: {OLIVA_OSCURO};
  }}
  .stTabs [aria-selected="true"] {{
      color: {CIRUELA} !important;
  }}

  /* ---- Titulos de seccion ---- */
  .stApp h2, .stApp h3, .stApp h4, .stApp h5 {{ color: {CIRUELA}; }}

  /* ---- Metricas ---- */
  .stApp [data-testid="stMetricValue"] {{ color: {CIRUELA}; }}
  .stApp [data-testid="stMetricLabel"] {{ color: {OLIVA_OSCURO}; }}

  /* ---- Pastillas de los multiselect ----
     Por defecto heredan el primaryColor y una fila de filtros queda como un
     bloque macizo de bermellon, que le come el protagonismo a los acentos de
     verdad. En arena con texto ciruela leen como control, no como alerta. */
  .stApp [data-baseweb="tag"] {{
      background-color: {ARENA} !important;
      color: {CIRUELA} !important;
  }}
  .stApp [data-baseweb="tag"] span,
  .stApp [data-baseweb="tag"] svg {{
      color: {CIRUELA} !important;
      fill: {CIRUELA} !important;
  }}

  /* ---- Avisos ----
     Streamlit trae azul para 'info' y verde para 'success'; ninguno de los dos
     existe en la marca. Los pasamos a teal y oliva.
     Ojo con el detalle: teal al 10% y oliva al 20% dan fondos casi identicos
     (#dee4e2 vs #d8d6cd), asi que el fondo solo no alcanza para distinguirlos.
     El filete lateral es el que hace de verdad la diferencia.
     El rojo de error y el ambar de warning se dejan: ya armonizan con la paleta
     y su significado es convencional. */
  .stApp [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {{
      background-color: rgba(46, 107, 124, 0.10);
      border-left: 3px solid {TEAL};
  }}
  .stApp [data-testid="stAlertContentInfo"] {{
      color: {TEAL_TEXTO} !important;   /* 7.09:1 sobre el fondo del aviso */
  }}

  .stApp [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {{
      background-color: rgba(111, 106, 78, 0.20);
      border-left: 3px solid {OLIVA_OSCURO};
  }}
  .stApp [data-testid="stAlertContentSuccess"] {{
      color: {OLIVA_TEXTO} !important;  /* 6.03:1 sobre el fondo del aviso */
  }}

  /* ---- Codigo en linea ----
     Streamlit lo pinta verde por defecto, el unico verde que quedaba en la
     interfaz despues del cambio de paleta. */
  .stApp .stMarkdown code {{
      color: {CIRUELA};
      background-color: {ARENA_SUAVE};
  }}

  /* ---- Bloque de pendientes ---- */
  .inv-todo {{
      border: 1.5px dashed {OLIVA};
      border-radius: 22px;
      padding: 1rem 1.2rem;
      background: {ARENA_SUAVE};
      color: {OLIVA_OSCURO};
      font-size: 0.9rem;
  }}

  /* ---- Estado vacio ----
     Parecido al de pendientes, pero NO es lo mismo y no debe confundirse: este
     dice "todavia no hay nada que mostrar aqui", no "esto falta construirlo".
     Sin borde punteado, que es lo que lee como obra en curso. */
  .inv-vacio {{
      border: 1.5px solid {OLIVA};
      border-radius: 22px;
      padding: 1.4rem 1.2rem;
      background: {BLANCO};
      color: {OLIVA_OSCURO};
      font-size: 0.9rem;
      text-align: center;
  }}
</style>
"""


def aplicar_tema() -> None:
    """Inyecta el CSS de la app. Llamar una vez, al inicio de app.py."""
    st.markdown(_CSS, unsafe_allow_html=True)


def encabezado(titulo: str = "Flora&Fauna Alerta",
               bajada: str = "Detecta especies invasoras desde una foto y alerta a las autoridades.") -> None:
    st.markdown(
        f"""<div class="inv-hero">
              <h1>{titulo}</h1>
              <div class="inv-regla"></div>
              <p>{bajada}</p>
            </div>""",
        unsafe_allow_html=True,
    )


def tag_impacto(nivel: str) -> str:
    """Devuelve el HTML de una etiqueta de impacto ambiental."""
    color = IMPACTO_COLOR.get(nivel, OLIVA_OSCURO)
    return f'<span class="inv-tag" style="background:{color}">Impacto {nivel.lower()}</span>'


def tag_enfermedad() -> str:
    """Devuelve el HTML de la etiqueta de especie portadora de enfermedades."""
    return f'<span class="inv-tag" style="background:{ENFERMEDAD_COLOR}">🦠 Portadora de enfermedades</span>'


def ficha_especie(nombre: str, cientifico: str, impacto_ambiental: str, detalle: str = "",
                  imagen_url: str | None = None, portador_enfermedades: bool = False) -> str:
    """Devuelve el HTML de una ficha de especie, con foto y etiquetas.

    El filo izquierdo lleva el color de la ESPECIE, no el del impacto: es el
    mismo código que usa el mapa, y así la ficha y el punto se leen juntos.
    """
    color = ESPECIE_COLOR.get(nombre, IMPACTO_COLOR.get(impacto_ambiental, OLIVA_OSCURO))

    if imagen_url:
        foto_html = f'<img class="inv-foto" src="{imagen_url}" alt="{nombre}">'
    else:
        foto_html = '<div class="inv-foto-placeholder">📷 Sin foto disponible</div>'

    tags = tag_impacto(impacto_ambiental)
    if portador_enfermedades:
        tags += tag_enfermedad()

    return f"""<div class="inv-card" style="border-left-color:{color}">
                 {foto_html}
                 <h4>{nombre}</h4>
                 <div class="sci">{cientifico}</div>
                 <div class="tags">{tags}</div>
                 <p>{detalle}</p>
               </div>"""


def pendiente(texto: str) -> None:
    """Bloque visual para marcar lo que falta CONSTRUIR.

    No usar para estados vacios de una funcion que si esta terminada: para eso
    esta vacio(). Confundirlos hace que la app se presente como inacabada donde
    en realidad solo esta esperando que la persona haga algo.
    """
    st.markdown(f'<div class="inv-todo">🚧 <b>Por completar:</b> {texto}</div>',
                unsafe_allow_html=True)


def vacio(texto: str, icono: str = "📷") -> None:
    """Bloque para cuando todavia no hay nada que mostrar, pero la funcion existe."""
    st.markdown(f'<div class="inv-vacio">{icono}<br>{texto}</div>',
                unsafe_allow_html=True)
