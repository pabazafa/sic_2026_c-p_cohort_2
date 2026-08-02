"""Carga y consulta de datos: catalogo de especies, avistamientos y reportes.

Los CSV de data/ son DATOS REALES descargados de GBIF por core/ingesta.py, y
cubren únicamente las tres especies que el modelo sabe reconocer:
jabalí, liebre europea y rata gris.

  - especies.csv       las tres fichas del catalogo
  - avistamientos.csv  registros historicos de GBIF + los que envia la app
  - reportes.csv       lo que reporta la persona desde la app (solo local)

Para regenerarlos:  python -m core.ingesta
"""

from __future__ import annotations

import base64
import math
import mimetypes
import re
import unicodedata
import urllib.parse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ / "data"
DIR_SUBIDAS = DIR_DATOS / "subidas"
DIR_IMAGENES = DIR_DATOS / "imagenes"

CSV_ESPECIES = DIR_DATOS / "especies.csv"
CSV_AVISTAMIENTOS = DIR_DATOS / "avistamientos.csv"
CSV_REPORTES = DIR_DATOS / "reportes.csv"
CSV_ZONAS = DIR_DATOS / "zonas_urbanas.csv"

# Si es False, nunca se consulta Wikipedia: solo se muestran fotos propias de
# data/imagenes/<especie>/ o la del catalogo (GBIF).
USAR_WIKIPEDIA_COMO_RESPALDO = True

EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".webp")

# Las tres especies del proyecto son mamíferos, así que 'tipo' ya no discrimina
# nada y dejamos de ofrecerlo como filtro. Lo que si distingue a estas tres es
# donde aparecen: la rata gris es urbana, el jabalí y la liebre son rurales.
TIPOS = ["Animal"]
NIVELES_IMPACTO = ["Alto", "Medio", "Bajo"]
ENTORNOS = ["Urbano", "Rural"]
ESTADOS = ["Confirmado", "En revision"]

# Punto de referencia por region, para centrar el mapa mientras no tengamos
# geolocalizacion del navegador.
REGIONES = {
    "Arica y Parinacota": (-18.478, -70.321),
    "Tarapaca": (-20.214, -70.152),
    "Antofagasta": (-23.650, -70.400),
    "Atacama": (-27.366, -70.332),
    "Coquimbo": (-29.903, -71.251),
    "Valparaiso": (-33.046, -71.620),
    "Metropolitana": (-33.447, -70.660),
    "O'Higgins": (-34.171, -70.740),
    "Maule": (-35.426, -71.655),
    "Nuble": (-36.606, -72.103),
    "Biobio": (-36.827, -73.050),
    "Araucania": (-38.739, -72.598),
    "Los Rios": (-39.814, -73.245),
    "Los Lagos": (-41.471, -72.936),
    "Chiloe": (-42.482, -73.763),
    "Aysen": (-45.572, -72.068),
    "Magallanes": (-53.163, -70.917),
}


# --------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------
@st.cache_data
def cargar_especies() -> pd.DataFrame:
    """Catalogo de especies invasoras."""
    return pd.read_csv(CSV_ESPECIES)


@st.cache_data
def cargar_avistamientos() -> pd.DataFrame:
    """Avistamientos con los datos de la especie ya unidos."""
    av = pd.read_csv(CSV_AVISTAMIENTOS, parse_dates=["fecha"])
    esp = cargar_especies()
    return av.merge(esp, left_on="especie_id", right_on="id", suffixes=("", "_esp"))


def cargar_reportes() -> pd.DataFrame:
    """Reportes enviados desde la app. Vacio si aun no hay ninguno."""
    columnas = ["ticket", "fecha_hora", "especie", "confianza", "tipo",
                "impacto_ambiental", "region", "comuna", "lat", "lon",
                "autoridad", "estado", "contacto", "comentario", "imagen"]
    if not CSV_REPORTES.exists():
        return pd.DataFrame(columns=columnas)

    df = pd.read_csv(CSV_REPORTES)

    # Los reportes guardados antes del renombre traen la columna 'riesgo'. Se
    # migran al leer para que un CSV viejo —el de cualquier integrante del
    # equipo— no rompa la pestana de reportes.
    if "riesgo" in df.columns and "impacto_ambiental" not in df.columns:
        df = df.rename(columns={"riesgo": "impacto_ambiental"})

    # Si falta alguna columna esperada, se agrega vacia en vez de explotar.
    for col in columnas:
        if col not in df.columns:
            df[col] = pd.NA

    return df


# --------------------------------------------------------------------------
# Escritura
# --------------------------------------------------------------------------
def guardar_reporte(reporte: dict) -> None:
    """Agrega un reporte al CSV local de reportes y sincroniza con avistamientos.csv."""
    df = pd.DataFrame([reporte])
    existe = CSV_REPORTES.exists()
    df.to_csv(CSV_REPORTES, mode="a", header=not existe, index=False)

    # Sincronizar automáticamente el nuevo reporte en avistamientos.csv
    try:
        guardar_avistamiento(
            especie_nombre_o_id=reporte.get("especie", ""),
            region=reporte.get("region", ""),
            comuna=reporte.get("comuna", ""),
            lat=float(reporte.get("lat", 0) or 0),
            lon=float(reporte.get("lon", 0) or 0),
            fecha=datetime.now().strftime("%Y-%m-%d"),
            estado="En revision",
        )
    except Exception:
        pass


@st.cache_data(show_spinner=False)
def cargar_zonas_urbanas() -> pd.DataFrame:
    """Las 30 zonas urbanas del proyecto: centro, radio y region."""
    if not CSV_ZONAS.exists():
        return pd.DataFrame(columns=["zona", "region", "lat", "lon", "radio_km"])
    return pd.read_csv(CSV_ZONAS)


def clasificar_entorno(lat: float, lon: float) -> tuple[str, str]:
    """Devuelve (entorno, zona_urbana) para una coordenada.

    Usa la misma definicion que core.ingesta.asignar_zona_urbana: cada zona
    urbana es un centro con un radio en km, no un poligono administrativo, y
    lo que cae fuera de todos los radios es rural. Si un punto queda dentro de
    mas de una zona, gana la mas cercana.
    """
    zonas = cargar_zonas_urbanas()
    if zonas.empty:
        return "Rural", ""

    d = distancias_km(lat, lon, zonas["lat"].to_numpy(), zonas["lon"].to_numpy())
    dentro = d <= zonas["radio_km"].to_numpy()
    if not dentro.any():
        return "Rural", ""

    i = int(np.argmin(np.where(dentro, d, np.inf)))
    return "Urbano", str(zonas["zona"].iloc[i])


def guardar_avistamiento(especie_nombre_o_id: str | int, region: str, comuna: str,
                         lat: float, lon: float, fecha: str = "",
                         estado: str = "En revision") -> dict:
    """Agrega un nuevo registro a data/avistamientos.csv y refresca la cache."""
    especie_id = None
    if isinstance(especie_nombre_o_id, int) or (
            isinstance(especie_nombre_o_id, str) and especie_nombre_o_id.isdigit()):
        especie_id = int(especie_nombre_o_id)
    else:
        info = especie_por_nombre(str(especie_nombre_o_id))
        especie_id = info["id"] if info else None

    # Si la especie no se encuentra en el catalogo, se asigna 1 por defecto
    if especie_id is None:
        especie_id = 1

    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")

    if CSV_AVISTAMIENTOS.exists():
        df_existente = pd.read_csv(CSV_AVISTAMIENTOS)
        nuevo_id = int(df_existente["id"].max() + 1) if not df_existente.empty else 1
    else:
        nuevo_id = 1

    # El entorno se calcula, no se asume. Dejarlo fijo en "Rural" marcaba como
    # rural un avistamiento en pleno centro de Santiago, y ademas contradecia el
    # punto del proyecto: los reportes ciudadanos existen justamente para cubrir
    # el vacio urbano que las camaras trampa no alcanzan.
    entorno, zona = clasificar_entorno(lat, lon)

    # Las columnas deben calzar con las que escribe core.ingesta.publicar_para_app,
    # o el CSV queda desalineado al concatenar en modo 'append'.
    nuevo_avistamiento = {
        "id": nuevo_id,
        "especie_id": especie_id,
        "region": region,
        "comuna": comuna,
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "fecha": fecha,
        "estado": estado,
        "entorno": entorno,
        "zona_urbana": zona,
        "fuente": "Reporte ciudadano (app)",
        "gbif_id": "",
        "origen": "App",
    }

    df = pd.DataFrame([nuevo_avistamiento])
    existe = CSV_AVISTAMIENTOS.exists()
    df.to_csv(CSV_AVISTAMIENTOS, mode="a", header=not existe, index=False)

    # Invalida el cache para que el mapa muestre el nuevo registro de inmediato
    cargar_avistamientos.clear()

    return nuevo_avistamiento


def guardar_imagen(archivo, prefijo: str = "obs") -> str:
    """Guarda la foto subida en data/subidas/ y devuelve la ruta relativa."""
    DIR_SUBIDAS.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    nombre = f"{prefijo}-{marca}-{archivo.name}".replace(" ", "_")
    destino = DIR_SUBIDAS / nombre
    destino.write_bytes(archivo.getvalue())
    return str(destino.relative_to(RAIZ))


# --------------------------------------------------------------------------
# Fotos de las especies
# --------------------------------------------------------------------------
def _normalizar(texto: str) -> str:
    """'Rata gris' -> 'ratagris', para comparar nombres de carpeta sin
    preocuparse de tildes, mayusculas, espacios o guiones."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sin_tildes.lower())


def _archivo_a_data_uri(ruta: Path) -> str:
    """Convierte un archivo local a data URI, para usarlo en un <img src=...>."""
    mime = mimetypes.guess_type(ruta.name)[0] or "image/jpeg"
    b64 = base64.b64encode(ruta.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


@st.cache_data(show_spinner=False)
def imagen_especie_local(nombre_comun: str) -> str | None:
    """Busca la primera foto en data/imagenes/<nombre_comun>/ como data URI.

    El nombre de la carpeta no necesita coincidir exactamente: 'Rata gris',
    'rata_gris' y 'rata-gris' apuntan a la misma carpeta.
    """
    if not DIR_IMAGENES.exists():
        return None

    objetivo = _normalizar(nombre_comun)
    for carpeta in sorted(DIR_IMAGENES.iterdir()):
        if carpeta.is_dir() and _normalizar(carpeta.name) == objetivo:
            for archivo in sorted(carpeta.iterdir()):
                if archivo.suffix.lower() in EXTENSIONES_IMAGEN:
                    return _archivo_a_data_uri(archivo)
    return None


@st.cache_data(show_spinner=False)
def imagen_especie_wikipedia(nombre_cientifico: str) -> str | None:
    """Busca una foto de la especie por su nombre cientifico en Wikipedia.

    Ultimo respaldo, cuando no hay foto propia ni foto del catalogo.
    """
    try:
        url = ("https://es.wikipedia.org/api/rest_v1/page/summary/"
               + urllib.parse.quote(nombre_cientifico))
        r = requests.get(url, timeout=5, headers={"accept": "application/json"})
        if r.ok:
            data = r.json()
            imagen = data.get("originalimage") or data.get("thumbnail") or {}
            return imagen.get("source")
    except Exception:
        pass
    return None


def imagen_especie(nombre_comun: str, nombre_cientifico: str = "",
                   imagen_url: str | None = None) -> str | None:
    """Foto para mostrar en la ficha de una especie.

    Prioridad:
      1. data/imagenes/<nombre_comun>/  fotos propias del equipo, mandan siempre.
      2. imagen_url del catalogo        foto real de GBIF tomada en Chile, con la
                                        licencia ya verificada por el pipeline.
      3. Wikipedia                     respaldo, si esta habilitado.
      4. None                          la ficha muestra un placeholder.
    """
    local = imagen_especie_local(nombre_comun)
    if local:
        return local

    if imagen_url is not None and pd.notna(imagen_url) and str(imagen_url).strip():
        return str(imagen_url)

    if USAR_WIKIPEDIA_COMO_RESPALDO and nombre_cientifico:
        return imagen_especie_wikipedia(nombre_cientifico)

    return None


# --------------------------------------------------------------------------
# Consultas geograficas
# --------------------------------------------------------------------------
def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en km entre dos coordenadas (formula de haversine)."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def distancias_km(lat: float, lon: float, lats, lons):
    """Haversine vectorizado: distancia de un punto a un array de coordenadas.

    Con ~49.000 avistamientos, calcular esto fila por fila con df.apply tomaba
    segundos en cada interaccion de la app. En numpy es una sola operacion.
    """
    r = 6371.0
    lat1, lon1 = math.radians(lat), math.radians(lon)
    lat2 = np.radians(np.asarray(lats, dtype=float))
    lon2 = np.radians(np.asarray(lons, dtype=float))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = (np.sin(dlat / 2) ** 2
         + math.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2)
    return 2 * r * np.arcsin(np.sqrt(a))


def avistamientos_cerca(lat: float, lon: float, radio_km: float = 150.0) -> pd.DataFrame:
    """Avistamientos dentro de un radio, ordenados del mas cercano al mas lejano."""
    df = cargar_avistamientos()
    d = distancias_km(lat, lon, df["lat"].to_numpy(), df["lon"].to_numpy())
    cerca = df.loc[d <= radio_km].copy()
    cerca["distancia_km"] = d[d <= radio_km].round(1)
    return cerca.sort_values("distancia_km").reset_index(drop=True)


def especie_por_nombre(nombre: str) -> dict | None:
    """Busca una especie del catalogo por su nombre comun."""
    esp = cargar_especies()
    fila = esp[esp["nombre_comun"].str.lower() == nombre.lower()]
    return None if fila.empty else fila.iloc[0].to_dict()
