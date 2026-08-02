"""Obtención y limpieza de los datos del proyecto desde GBIF.

FUENTE ÚNICA: GBIF — Global Biodiversity Information Facility (api.gbif.org).
Los registros chilenos provienen mayoritariamente de iNaturalist
(Research-grade Observations, DOI 10.15468/ab3s5x) y de colecciones
museológicas. Licencias CC0 / CC-BY / CC-BY-NC según el registro.

El módulo trabaja sobre las tres especies que el modelo YOLO11 (core/best.pt)
sabe reconocer, y solo sobre esas tres. Cada una se consulta por su speciesKey
de GBIF, un identificador numérico estable: buscar por nombre científico
obligaría a resolver sinónimos taxonómicos a mano.

QUÉ HACE ESTE MÓDULO
--------------------
1. Baja *todos* los registros chilenos con coordenada de las tres especies
   (~49.000). Al ser solo tres especies podemos permitirnos los registros
   individuales en vez de conteos agregados, y eso es lo que habilita el
   analisis territorial: latitud, entorno urbano/rural y evolucion temporal.
2. Los limpia: duplicados, coordenadas invalidas, territorio insular, fechas.
3. Les asigna comuna, region y zona urbana a partir de la coordenada.
4. Deja los CSV listos en data/procesado/.

Uso desde el notebook:

    from core.ingesta import ejecutar_ingesta
    ejecutar_ingesta()          # descarga (con cache) y escribe data/procesado/
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ / "data"
DIR_CRUDO = DIR_DATOS / "crudo"
DIR_PROC = DIR_DATOS / "procesado"

API = "https://api.gbif.org/v1"
PAGINA = 300  # tope que acepta occurrence/search por peticion

CSV_ZONAS = DIR_DATOS / "zonas_urbanas.csv"


# --------------------------------------------------------------------------
# Las tres especies del proyecto
# --------------------------------------------------------------------------
# 'clase' es la etiqueta que devuelve el modelo YOLO11; el resto es la ficha
# que muestra la app. speciesKey es el identificador de GBIF.
ESPECIES_OBJETIVO: dict[str, dict] = {
    "jabali": {
        "id": 1,
        "speciesKey": 7705930,
        "nombre_comun": "Jabali",
        "nombre_cientifico": "Sus scrofa",
        "tipo": "Animal",
        "impacto_ambiental": "Alto",
        "autoridad": "SAG",
        "portador_enfermedades": "Si",
        "descripcion": ("Suido silvestre que remueve el suelo del bosque nativo y "
                        "transmite enfermedades al ganado y a las personas."),
    },
    "liebre": {
        "id": 2,
        "speciesKey": 7952072,
        "nombre_comun": "Liebre europea",
        "nombre_cientifico": "Lepus europaeus",
        "tipo": "Animal",
        "impacto_ambiental": "Medio",
        "autoridad": "SAG",
        "portador_enfermedades": "No",
        "descripcion": ("Mamifero herbivoro de orejas largas introducido desde Europa. "
                        "Compite por alimento con la fauna nativa y dana cultivos."),
    },
    "rata gris": {
        "id": 3,
        "speciesKey": 2439261,
        "nombre_comun": "Rata gris",
        "nombre_cientifico": "Rattus norvegicus",
        "tipo": "Animal",
        "impacto_ambiental": "Alto",
        "autoridad": "SAG",
        "portador_enfermedades": "Si",
        "descripcion": ("Roedor invasor urbano y rural que depreda nidos de aves nativas "
                        "y transmite enfermedades graves como hantavirus y leptospirosis."),
    },
}

# Nombre de archivo seguro para cada especie (la etiqueta del modelo trae espacios).
SLUG = {"jabali": "jabali", "liebre": "liebre", "rata gris": "rata_gris"}

# Campos que pedimos a GBIF. Todo lo demas del registro se descarta en origen.
CAMPOS = [
    "key", "speciesKey", "species", "scientificName",
    "decimalLatitude", "decimalLongitude", "coordinateUncertaintyInMeters",
    "eventDate", "year", "month", "day",
    "stateProvince", "locality", "basisOfRecord", "occurrenceStatus",
    "institutionCode", "collectionCode", "datasetName", "datasetKey",
    "license", "recordedBy", "individualCount", "lifeStage",
]

# Un registro cuenta como 'Confirmado' cuando su evidencia es verificable por
# un tercero: un especimen en coleccion, una muestra de material, o una foto.
# El resto queda 'En revision'. Es una regla nuestra y la declaramos explicita
# porque GBIF no trae un campo de validacion equivalente.
BASIS_CON_EVIDENCIA = {
    "PRESERVED_SPECIMEN", "MATERIAL_SAMPLE", "MATERIAL_CITATION",
    "MACHINE_OBSERVATION", "LIVING_SPECIMEN", "FOSSIL_SPECIMEN",
}

# Chile continental. Separamos el territorio insular (Juan Fernandez en
# lon -78,8 e Isla de Pascua en lon -109,3) porque un analisis por latitud se
# distorsiona si mezclamos puntos a 3.700 km de la costa.
LON_MIN_CONTINENTAL = -76.0
BBOX_CHILE = {"lat_min": -56.5, "lat_max": -17.4, "lon_min": -110.0, "lon_max": -66.0}

# El dato mas importante de este conjunto: NO todos los registros se generaron
# de la misma manera, y eso condiciona por completo donde aparecen.
#
#   Camara trampa (CONAF)  48.303 registros (98%), 2017-2023. Monitoreo en áreas
#       silvestres protegidas. Explica por si solo que el 96% del total sea
#       rural: no hay camaras trampa en ciudades. No tiene NI UN registro de
#       rata gris.
#   Ciencia ciudadana        336 registros. Fotos que sube la gente a
#       iNaturalist. Sesgada a donde vive y camina la gente.
#   Coleccion museologica    ~250 registros, desde 1907. Especimenes de museo.
#   Otros estudios           el resto.
#
# Mezclar las cuatro y leer el resultado como 'distribucion de la especie' es
# el error que hay que evitar: se estaria midiendo donde se instalaron camaras.
# Por eso 'fuente' es una columna de primera clase y el analisis la separa.
FUENTES = ["Camara trampa (CONAF)", "Ciencia ciudadana (iNaturalist)",
           "Coleccion museologica", "Otros estudios"]

BASIS_COLECCION = {"PRESERVED_SPECIMEN", "MATERIAL_SAMPLE", "MATERIAL_CITATION",
                   "FOSSIL_SPECIMEN", "LIVING_SPECIMEN"}


def clasificar_fuente(df: pd.DataFrame) -> pd.Series:
    """Etiqueta cada registro segun COMO se genero, no quien lo publica."""
    inst = df["institutionCode"].fillna("").astype(str)
    dsname = df["datasetName"].fillna("").astype(str)
    basis = df["basisOfRecord"].fillna("").astype(str)

    es_conaf = inst.str.contains("CONAF", case=False)
    es_inat = inst.str.contains("iNaturalist", case=False) | dsname.str.contains("iNaturalist", case=False)
    es_col = basis.isin(BASIS_COLECCION)

    return pd.Series(
        np.select([es_conaf, es_inat, es_col], FUENTES[:3], default=FUENTES[3]),
        index=df.index, name="fuente",
    )


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def _get(url: str, intentos: int = 5) -> dict:
    """GET con reintentos y espera creciente. GBIF corta la conexion a ratos."""
    for i in range(intentos):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if i == intentos - 1:
                raise
            time.sleep(2 * (i + 1))
    return {}


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia en km entre coordenadas. Acepta escalares o arrays de numpy."""
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


# --------------------------------------------------------------------------
# Paso 1 — descarga de ocurrencias
# --------------------------------------------------------------------------
def contar_ocurrencias(species_key: int) -> int:
    """Cuantos registros con coordenada tiene la especie en Chile."""
    u = f"{API}/occurrence/search?country=CL&speciesKey={species_key}&hasCoordinate=true&limit=0"
    return _get(u)["count"]


def _pagina(species_key: int, offset: int) -> list[dict]:
    u = (f"{API}/occurrence/search?country=CL&speciesKey={species_key}"
         f"&hasCoordinate=true&limit={PAGINA}&offset={offset}")
    filas = []
    for r in _get(u).get("results", []):
        fila = {c: r.get(c) for c in CAMPOS}
        medios = r.get("media") or []
        urls = [m.get("identifier") for m in medios if m.get("identifier")]
        fila["foto_url"] = urls[0] if urls else None
        fila["n_fotos"] = len(urls)
        filas.append(fila)
    return filas


def descargar_ocurrencias(clase: str, refrescar: bool = False,
                          hilos: int = 8) -> pd.DataFrame:
    """Descarga los registros de una especie, con cache en data/crudo/.

    La cache importa: son ~165 peticiones para la liebre, y el notebook se
    re-ejecuta muchas veces mientras se trabaja en el analisis.
    """
    DIR_CRUDO.mkdir(parents=True, exist_ok=True)
    destino = DIR_CRUDO / f"gbif_{SLUG[clase]}.csv"

    if destino.exists() and not refrescar:
        return pd.read_csv(destino, low_memory=False)

    key = ESPECIES_OBJETIVO[clase]["speciesKey"]
    total = contar_ocurrencias(key)
    offsets = list(range(0, total, PAGINA))
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        lotes = list(ex.map(lambda o: _pagina(key, o), offsets))

    df = pd.DataFrame([f for lote in lotes for f in lote])
    df["clase_modelo"] = clase
    df.to_csv(destino, index=False)
    return df


def descargar_todas(refrescar: bool = False) -> pd.DataFrame:
    """Los registros de las tres especies en una sola tabla."""
    partes = []
    for clase in ESPECIES_OBJETIVO:
        df = descargar_ocurrencias(clase, refrescar=refrescar)
        df["clase_modelo"] = clase
        partes.append(df)
    return pd.concat(partes, ignore_index=True)


# --------------------------------------------------------------------------
# Paso 2 — limpieza
# --------------------------------------------------------------------------
def limpiar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Limpia los registros y devuelve (limpios, bitacora de descartes).

    La bitacora se reporta en el notebook: cuantas filas se cayeron y por que,
    para que la limpieza sea auditable en vez de una caja negra.
    """
    bitacora = []
    n0 = len(df)

    def registrar(motivo: str, antes: int, despues: int) -> None:
        bitacora.append({"paso": motivo, "descartados": antes - despues,
                         "quedan": despues})

    df = df.rename(columns={"decimalLatitude": "lat", "decimalLongitude": "lon",
                            "key": "gbif_id", "year": "anio"})

    # 1. El mismo registro puede venir repetido si dos datasets lo publican.
    n = len(df)
    df = df.drop_duplicates("gbif_id")
    registrar("duplicados por gbif_id", n, len(df))

    # 2. Coordenadas presentes y numericas.
    n = len(df)
    df = df[df["lat"].notna() & df["lon"].notna()]
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df[df["lat"].notna() & df["lon"].notna()]
    registrar("sin coordenada valida", n, len(df))

    # 3. Dentro del rectangulo de Chile (incluye territorio insular).
    n = len(df)
    b = BBOX_CHILE
    df = df[df["lat"].between(b["lat_min"], b["lat_max"])
            & df["lon"].between(b["lon_min"], b["lon_max"])]
    registrar("fuera del bounding box de Chile", n, len(df))

    # 4. Coordenada exactamente en (0,0): error clasico de digitacion.
    n = len(df)
    df = df[~((df["lat"] == 0) & (df["lon"] == 0))]
    registrar("coordenada en (0,0)", n, len(df))

    # 5. Ausencias. GBIF marca con occurrenceStatus si la especie NO estaba.
    n = len(df)
    df = df[df["occurrenceStatus"].fillna("PRESENT").str.upper() != "ABSENT"]
    registrar("registros de ausencia", n, len(df))

    # 6. Año utilizable para la serie temporal. No descartamos: marcamos.
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["tiene_anio"] = df["anio"].notna() & df["anio"].between(1800, 2026)

    # Territorio: continental vs insular.
    df["territorio"] = np.where(df["lon"] >= LON_MIN_CONTINENTAL,
                                "Continental", "Insular")

    # Como se genero el registro. Determina donde puede aparecer, así que se
    # calcula antes de cualquier agregacion territorial.
    df["fuente"] = clasificar_fuente(df)

    # Estado segun la regla de evidencia verificable declarada arriba.
    tiene_foto = df["n_fotos"].fillna(0).astype(float) > 0
    basis_ok = df["basisOfRecord"].fillna("").isin(BASIS_CON_EVIDENCIA)
    df["estado"] = np.where(basis_ok | tiene_foto, "Confirmado", "En revision")

    # eventDate llega en formatos mezclados: '2026-01-28', '2026-01-28T07:03',
    # '2026-03-23T11:57:51', y a veces solo '2026' o '2026-01'. Si se deja que
    # pandas infiera el formato, lo deduce del primer valor y descarta en
    # silencio todo lo que no calce. Nos quedamos con los primeros 10
    # caracteres, que son la parte ISO comun a todas las variantes completas.
    iso = df["eventDate"].astype("string").str.slice(0, 10)
    df["fecha"] = pd.to_datetime(iso, format="%Y-%m-%d", errors="coerce")

    # Los que traen solo año o año-mes no tienen dia y quedan sin fecha exacta;
    # su 'anio' si sirve para la serie temporal, así que se conservan marcados.
    df["tiene_fecha"] = df["fecha"].notna()
    bitacora.append({"paso": "sin fecha exacta (se marcan, no se descartan)",
                     "descartados": int((~df["tiene_fecha"]).sum()),
                     "quedan": len(df)})

    bitacora.append({"paso": "TOTAL", "descartados": n0 - len(df), "quedan": len(df)})
    return df.reset_index(drop=True), pd.DataFrame(bitacora)


# --------------------------------------------------------------------------
# Paso 3 — geografia: comuna, region y zona urbana
# --------------------------------------------------------------------------
def asignar_comuna(df: pd.DataFrame) -> pd.DataFrame:
    """Asigna comuna y region por cercania al centro comunal mas proximo.

    GBIF trae stateProvince, pero viene sucio y en formatos mezclados
    ('Region Metropolitana', 'RM', 'Santiago', vacio). Preferimos derivarlo de
    la coordenada, que es el dato duro del registro.

    Limitacion declarada: usamos el centro de cada comuna, no su polionio real,
    así que un punto cerca del limite comunal puede caer en la vecina. Para el
    nivel de agregacion del analisis (region y zona urbana) el efecto es menor.
    """
    from core.comunas import COMUNAS_POR_REGION

    filas = [(reg, com, lat, lon)
             for reg, comunas in COMUNAS_POR_REGION.items()
             for com, (lat, lon) in comunas.items()]
    ref = pd.DataFrame(filas, columns=["region", "comuna", "clat", "clon"])

    # Matriz registros x comunas. Con ~49k x ~346 numpy lo resuelve de una vez.
    d = haversine_km(df["lat"].to_numpy()[:, None], df["lon"].to_numpy()[:, None],
                     ref["clat"].to_numpy()[None, :], ref["clon"].to_numpy()[None, :])
    idx = d.argmin(axis=1)

    df = df.copy()
    df["region"] = ref["region"].to_numpy()[idx]
    df["comuna"] = ref["comuna"].to_numpy()[idx]
    df["dist_centro_comunal_km"] = d[np.arange(len(df)), idx].round(1)

    # La mediana de esta distancia es ~34 km: la mayoria de los registros son
    # rurales y caen lejos de cualquier centro comunal del diccionario. Sobre
    # ese umbral la comuna asignada es una etiqueta debil, así que la marcamos
    # y el analisis se queda a nivel de region, que si es robusto.
    df["comuna_confiable"] = df["dist_centro_comunal_km"] <= 25
    return df


def asignar_zona_urbana(df: pd.DataFrame, zonas: pd.DataFrame) -> pd.DataFrame:
    """Marca si el registro cae dentro del radio de una zona urbana.

    Mantenemos la definicion del proyecto: cada zona urbana es un centro y un
    radio en km, no un poligono administrativo. Un registro fuera de todos los
    radios se considera entorno rural.
    """
    d = haversine_km(df["lat"].to_numpy()[:, None], df["lon"].to_numpy()[:, None],
                     zonas["lat"].to_numpy()[None, :], zonas["lon"].to_numpy()[None, :])
    dentro = d <= zonas["radio_km"].to_numpy()[None, :]

    idx = np.where(dentro.any(axis=1), np.argmax(dentro, axis=1), -1)
    df = df.copy()
    df["zona_urbana"] = np.where(idx >= 0, zonas["zona"].to_numpy()[np.clip(idx, 0, None)], None)
    df["entorno"] = np.where(idx >= 0, "Urbano", "Rural")
    df["dist_zona_km"] = np.where(idx >= 0, d[np.arange(len(df)), np.clip(idx, 0, None)].round(1), np.nan)
    return df


# --------------------------------------------------------------------------
# Paso 4 — tablas de salida
# --------------------------------------------------------------------------
def tabla_especies() -> pd.DataFrame:
    """Las tres fichas del catalogo, en el orden de id."""
    filas = []
    for clase, info in ESPECIES_OBJETIVO.items():
        filas.append({"clase_modelo": clase, **info})
    return pd.DataFrame(filas).sort_values("id").reset_index(drop=True)


def resumen_por_especie(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por especie con las metricas que usa el analisis."""
    filas = []
    for clase, g in df.groupby("clase_modelo"):
        info = ESPECIES_OBJETIVO[clase]
        cont = g[g["territorio"] == "Continental"]
        filas.append({
            "clase_modelo": clase,
            "nombre_comun": info["nombre_comun"],
            "nombre_cientifico": info["nombre_cientifico"],
            "registros": len(g),
            "registros_continentales": len(cont),
            "con_foto": int((g["n_fotos"].fillna(0) > 0).sum()),
            "confirmados": int((g["estado"] == "Confirmado").sum()),
            "urbanos": int((g["entorno"] == "Urbano").sum()),
            "rurales": int((g["entorno"] == "Rural").sum()),
            "pct_urbano": round(100 * (g["entorno"] == "Urbano").mean(), 1),
            "regiones": g["region"].nunique(),
            "zonas_urbanas": g["zona_urbana"].nunique(),
            "lat_min": round(cont["lat"].min(), 3) if len(cont) else None,
            "lat_max": round(cont["lat"].max(), 3) if len(cont) else None,
            "lat_mediana": round(cont["lat"].median(), 3) if len(cont) else None,
            "anio_primero": int(g.loc[g["tiene_anio"], "anio"].min()) if g["tiene_anio"].any() else None,
            "anio_ultimo": int(g.loc[g["tiene_anio"], "anio"].max()) if g["tiene_anio"].any() else None,
        })
    return pd.DataFrame(filas).sort_values("registros", ascending=False).reset_index(drop=True)


def resumen_por_region(df: pd.DataFrame) -> pd.DataFrame:
    """Registros por region y especie, en formato ancho para leerlo de un vistazo."""
    t = (df.pivot_table(index="region", columns="clase_modelo", values="gbif_id",
                        aggfunc="count", fill_value=0)
           .rename(columns={c: f"reg_{SLUG[c]}" for c in ESPECIES_OBJETIVO}))
    t["total"] = t.sum(axis=1)
    lat = df.groupby("region")["lat"].median().round(3).rename("lat_mediana")
    return t.join(lat).sort_values("lat_mediana", ascending=False).reset_index()


def resumen_por_zona(df: pd.DataFrame, zonas: pd.DataFrame) -> pd.DataFrame:
    """Registros por zona urbana y especie, solo de los registros urbanos."""
    urb = df[df["entorno"] == "Urbano"]
    t = (urb.pivot_table(index="zona_urbana", columns="clase_modelo", values="gbif_id",
                         aggfunc="count", fill_value=0)
            .rename(columns={c: f"reg_{SLUG[c]}" for c in ESPECIES_OBJETIVO}))
    for c in ESPECIES_OBJETIVO:
        col = f"reg_{SLUG[c]}"
        if col not in t.columns:
            t[col] = 0
    t["total"] = t[[f"reg_{SLUG[c]}" for c in ESPECIES_OBJETIVO]].sum(axis=1)
    out = zonas.merge(t.reset_index().rename(columns={"zona_urbana": "zona"}),
                      on="zona", how="left")
    cols = [f"reg_{SLUG[c]}" for c in ESPECIES_OBJETIVO] + ["total"]
    out[cols] = out[cols].fillna(0).astype(int)
    return out.sort_values("total", ascending=False).reset_index(drop=True)


def resumen_por_fuente(df: pd.DataFrame) -> pd.DataFrame:
    """Como se comporta cada especie SEGUN el tipo de vigilancia que la registro.

    Es la tabla central del analisis: muestra que el porcentaje urbano de una
    misma especie cambia de forma drastica segun quien la observo, y por lo
    tanto que no se puede leer un unico numero de 'que tan urbana es'.
    """
    filas = []
    for (fuente, clase), g in df.groupby(["fuente", "clase_modelo"]):
        filas.append({
            "fuente": fuente,
            "clase_modelo": clase,
            "nombre_comun": ESPECIES_OBJETIVO[clase]["nombre_comun"],
            "registros": len(g),
            "pct_urbano": round(100 * (g["entorno"] == "Urbano").mean(), 1),
            "lat_mediana": round(g["lat"].median(), 2),
            "regiones": g["region"].nunique(),
            "anio_min": int(g.loc[g["tiene_anio"], "anio"].min()) if g["tiene_anio"].any() else None,
            "anio_max": int(g.loc[g["tiene_anio"], "anio"].max()) if g["tiene_anio"].any() else None,
        })
    return (pd.DataFrame(filas)
            .sort_values(["fuente", "registros"], ascending=[True, False])
            .reset_index(drop=True))


def serie_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """Registros por año y especie, desde 1990 (antes los datos son anecdoticos)."""
    d = df[df["tiene_anio"] & (df["anio"] >= 1990)]
    t = (d.pivot_table(index="anio", columns="clase_modelo", values="gbif_id",
                       aggfunc="count", fill_value=0)
          .rename(columns={c: f"reg_{SLUG[c]}" for c in ESPECIES_OBJETIVO}))
    t["total"] = t.sum(axis=1)
    return t.reset_index()


def fotos_libres(df: pd.DataFrame, por_especie: int = 12) -> pd.DataFrame:
    """Fotos reales tomadas en Chile para ilustrar el catalogo de la app.

    Priorizamos CC0 y CC-BY, que permiten reutilizacion sin restriccion de uso
    comercial; dejamos CC-BY-NC al final como respaldo.
    """
    # GBIF entrega la licencia como URL completa, no como sigla, así que la
    # prioridad se decide por subcadena: CC0 antes que CC-BY, y CC-BY-NC al final.
    con_foto = df[df["foto_url"].notna()].copy()
    lic = con_foto["license"].fillna("").astype(str)
    con_foto["lic_orden"] = np.select(
        [lic.str.contains("publicdomain/zero"),
         lic.str.contains("licenses/by/"),
         lic.str.contains("licenses/by-nc")],
        [0, 1, 2], default=3)
    sel = (con_foto.sort_values(["clase_modelo", "lic_orden", "anio"],
                                ascending=[True, True, False])
                   .groupby("clase_modelo").head(por_especie)).copy()
    sel["nombre_comun"] = sel["clase_modelo"].map(
        {c: i["nombre_comun"] for c, i in ESPECIES_OBJETIVO.items()})
    cols = ["clase_modelo", "nombre_comun", "gbif_id", "species", "lat", "lon",
            "anio", "region", "comuna", "zona_urbana", "entorno", "fuente",
            "license", "foto_url", "recordedBy"]
    return sel[cols].reset_index(drop=True)


# --------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------
def ejecutar_ingesta(verbose: bool = True, refrescar: bool = False) -> dict[str, pd.DataFrame]:
    """Pipeline completo. Deja los CSV en data/procesado/ y los devuelve."""
    log = print if verbose else (lambda *a, **k: None)
    DIR_PROC.mkdir(parents=True, exist_ok=True)

    log("1/5 Descargando ocurrencias de GBIF (con cache en data/crudo/)…")
    crudo = descargar_todas(refrescar=refrescar)
    log(f"     {len(crudo):,} registros crudos de {crudo['clase_modelo'].nunique()} especies")

    log("2/5 Limpiando…")
    df, bitacora = limpiar(crudo)
    log(f"     {len(df):,} registros limpios "
        f"({bitacora.iloc[-1]['descartados']:,} descartados)")

    log("3/5 Asignando comuna, region y zona urbana…")
    zonas = pd.read_csv(CSV_ZONAS)
    df = asignar_comuna(df)
    df = asignar_zona_urbana(df, zonas)
    log(f"     {(df['entorno'] == 'Urbano').sum():,} urbanos / "
        f"{(df['entorno'] == 'Rural').sum():,} rurales")

    log("4/5 Construyendo tablas de analisis…")
    salidas = {
        "ocurrencias": df,
        "limpieza_bitacora": bitacora,
        "especies_objetivo": tabla_especies(),
        "resumen_especie": resumen_por_especie(df),
        "resumen_fuente": resumen_por_fuente(df),
        "resumen_region": resumen_por_region(df),
        "resumen_zona": resumen_por_zona(df, zonas),
        "serie_temporal": serie_temporal(df),
        "fotos_muestra": fotos_libres(df),
    }

    log("5/5 Guardando en data/procesado/…")
    for nombre, tabla in salidas.items():
        tabla.to_csv(DIR_PROC / f"{nombre}.csv", index=False)
        log(f"     {nombre}.csv  ({len(tabla):,} filas)")

    return salidas


# --------------------------------------------------------------------------
# Publicacion de los datos que consume la app
# --------------------------------------------------------------------------
def publicar_para_app(ocurrencias: pd.DataFrame | None = None,
                      verbose: bool = True) -> None:
    """Escribe data/especies.csv y data/avistamientos.csv desde los datos reales.

    Separado de ejecutar_ingesta() a propósito: la ingesta es analisis y no
    deberia sobrescribir en silencio los archivos que lee la aplicacion.
    """
    log = print if verbose else (lambda *a, **k: None)

    if ocurrencias is None:
        ocurrencias = pd.read_csv(DIR_PROC / "ocurrencias.csv", low_memory=False)

    esp = tabla_especies()
    esp_app = esp[["id", "nombre_comun", "nombre_cientifico", "tipo", "impacto_ambiental",
                   "autoridad", "descripcion", "portador_enfermedades"]].copy()

    # Foto de portada: la primera con mejor licencia de cada especie.
    fotos = pd.read_csv(DIR_PROC / "fotos_muestra.csv")
    portada = (fotos.groupby("clase_modelo").first()["foto_url"]
               .rename("imagen_url").reset_index())
    esp_app = (esp.merge(portada, on="clase_modelo", how="left")
               [["id", "nombre_comun", "nombre_cientifico", "tipo", "impacto_ambiental",
                 "autoridad", "descripcion", "imagen_url", "portador_enfermedades"]])
    esp_app.to_csv(DIR_DATOS / "especies.csv", index=False)
    log(f"     especies.csv        ({len(esp_app)} filas)")

    ids = {c: i["id"] for c, i in ESPECIES_OBJETIVO.items()}
    av = ocurrencias.copy()
    av["especie_id"] = av["clase_modelo"].map(ids)
    av["fecha"] = pd.to_datetime(av["fecha"], errors="coerce")

    # Sin fecha exacta no se puede mostrar en la ficha ni ordenar
    # cronologicamente. Son pocos, pero lo reportamos en vez de perderlos callados.
    sin_fecha = int(av["fecha"].isna().sum())
    if sin_fecha:
        log(f"     {sin_fecha} registros sin fecha exacta quedan fuera del mapa "
            f"({100 * sin_fecha / len(av):.2f}% del total)")
    av = av[av["fecha"].notna()]

    av_app = pd.DataFrame({
        "id": range(1, len(av) + 1),
        "especie_id": av["especie_id"].to_numpy(),
        "region": av["region"].to_numpy(),
        "comuna": av["comuna"].to_numpy(),
        "lat": av["lat"].round(5).to_numpy(),
        "lon": av["lon"].round(5).to_numpy(),
        "fecha": av["fecha"].dt.strftime("%Y-%m-%d").to_numpy(),
        "estado": av["estado"].to_numpy(),
        "entorno": av["entorno"].to_numpy(),
        "zona_urbana": av["zona_urbana"].to_numpy(),
        "fuente": av["fuente"].to_numpy(),
        "gbif_id": av["gbif_id"].to_numpy(),
        "origen": "GBIF",
    })
    # Los reportes que envio la gente desde la app NO vienen de GBIF y no se
    # pueden regenerar: si se sobrescribe el CSV a secas, se pierden para
    # siempre. Y el README invita a correr este pipeline para refrescar los
    # datos, así que perderlos era cuestion de tiempo. Se rescatan antes de
    # escribir y se reinsertan con ids que continuan la numeracion de GBIF.
    destino = DIR_DATOS / "avistamientos.csv"
    ciudadanos = pd.DataFrame()
    if destino.exists():
        previo = pd.read_csv(destino, low_memory=False)
        if "origen" in previo.columns:
            ciudadanos = previo[previo["origen"] != "GBIF"].copy()

    if not ciudadanos.empty:
        ciudadanos["id"] = range(len(av_app) + 1, len(av_app) + 1 + len(ciudadanos))
        av_app = pd.concat([av_app, ciudadanos[av_app.columns]], ignore_index=True)
        log(f"     {len(ciudadanos)} reportes ciudadanos conservados")

    av_app.to_csv(destino, index=False)
    log(f"     avistamientos.csv   ({len(av_app):,} filas)")


if __name__ == "__main__":
    salidas = ejecutar_ingesta()
    print("\nPublicando datos para la app…")
    publicar_para_app(salidas["ocurrencias"])
