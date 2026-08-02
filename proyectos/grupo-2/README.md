<a href="https://proyecto-samsung-innovacien-hl2shwgvd8d6kold6yzbtb.streamlit.app"><img src="https://github.com/martindroguett/Proyecto-Samsung-Innovacien/blob/main/imagesREADME/banner.png?raw=true" align="center" alt="Flora&Fauna" ></a>

<h1 align="center"> Proyecto Innovacien - Flora&Fauna Alerta </h1>

<p align = center>
<a><img alt="Static Badge" src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python"></a>
<a href = "https://innovacien.com"> <img alt="Static Badge" src="https://img.shields.io/badge/Samsung-%231428A0.svg?style=for-the-badge&logo=samsung&logoColor=white"></a>
<a> <img alt="Static Badge" src="https://img.shields.io/badge/UI-Streamlit-red?logo=streamlit"></a>

## Descripción
La aplicación permite la identificación de una especie invasora a partir de una fotografía subida por el usuario. Una vez confirmado el avistamiento, se extraen las coordenadas para comunicarlo a las autoridades correspondientes. Además, sirve como guía informativa para concientizar a las personas sobre el impacto que pueden tener estas especies en su ecosistema.

En su fase inicial, la aplicación es capaz de diferenciar las especies de jabalí, liebre europea y rata gris. Se espera poder escalarla a identificar todos los animales catalogados como invasores.

Puedes probar la aplicación directamente en el siguiente enlace: [Flora&Fauna Alerta](https://proyecto-samsung-innovacien-hl2shwgvd8d6kold6yzbtb.streamlit.app)

## Integrantes
<table>
  <tr>
    <td align="center">
      <a href="https://github.com/martindroguett">
        <img src="https://github.com/martindroguett.png" width="100px;" alt="Martín Droguett" style="border-radius:50%"/>
        <br />
        <sub><b>Martín Droguett</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/Paulo-Gutierrez-cloud">
        <img src="https://github.com/Paulo-Gutierrez-cloud.png" width="100px;" alt="Paulo Gutierrez" style="border-radius:50%"/>
        <br />
        <sub><b>Paulo Gutiérrez</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/Koteprog">
        <img src="https://github.com/Koteprog.png" width="100px;" alt="María José Parra" style="border-radius:50%"/>
        <br />
        <sub><b>María José Parra</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/pabazafa">
        <img src="https://github.com/pabazafa.png" width="100px;" alt="Pablo Zamorano" style="border-radius:50%"/>
        <br />
        <sub><b>Pablo Zamorano</b></sub>
      </a>
    </td>
  </tr>
</table>

## Pregunta de investigación

> ¿Cómo se distribuyen en Chile los registros de las tres especies invasoras que el
> modelo identifica —jabalí, liebre europea y rata gris— y en qué se diferencian sus
> patrones territoriales? 

## Hallazgo principal

**Las tres especies dibujan tres patrones territoriales completamente distintos.**

| Especie | Registros | Región principal | Mediana latitudinal | Urbano |
|---|---:|---|---:|---:|
| Jabalí | 3.156 | Los Lagos (90%) | -41,1 | 0,2% |
| Liebre europea | 45.778 | Aysén (39%) | -46,0 | 3,5% |
| Rata gris | 231 | Metropolitana (23%) | -35,8 | 36,4% |

El **jabalí** es el más concentrado: nueve de cada diez registros están en Los
Lagos, el 97% se reparte entre esa región y Aysén, y no aparece al norte de
Atacama. Es, además, prácticamente invisible en zonas urbanas.

La **liebre europea** ocupa el país entero —desde Arica hasta Magallanes, las 15
regiones con registro— pero su masa está en el sur austral: Aysén y Araucanía
reúnen más de la mitad de sus avistamientos.

La **rata gris** invierte el patrón. Es la más dispersa —ninguna región concentra
más de un cuarto de sus registros—, la que alcanza latitudes más septentrionales
en promedio, y la única con presencia urbana real: el 36,4% de sus avistamientos
ocurre en ciudad, contra 3,5% de la liebre y 0,2% del jabalí.

Esa diferencia tiene una explicación que conviene declarar: cada especie fue
observada por un método distinto. Jabalí y liebre provienen casi por completo de
cámaras trampa instaladas en áreas silvestres protegidas —de ahí su perfil rural y
austral—, mientras que la rata gris se registró sobre todo mediante colecciones
museológicas y observaciones de ciencia ciudadana, que sí llegan a la ciudad. Los
patrones reflejan tanto a las especies como a quién las estuvo mirando.

**Ese es el vacío que la aplicación busca llenar:** la especie más urbana de las
tres, y la única que transmite hantavirus y leptospirosis, es también la peor
cubierta, con 231 registros en más de un siglo.

## Dataset

Los avistamientos iniciales provienen de **GBIF** (*Global Biodiversity Information Facility*),
consultado por su API pública con filtro de país Chile y coordenada obligatoria. El
resultado es la base de `data/avistamientos.csv`: **49.133 registros georreferenciados**
entre 1907 y 2026, en 15 regiones y 161 comunas. A esa base la aplicación le va sumando
los reportes que envía la gente.

| Especie | Registros | Rango |
|---|---:|---|
| Liebre europea | 45.778 | 1960 – 2026 |
| Jabalí | 3.156 | 1970 – 2026 |
| Rata gris | 231 | 1907 – 2026 |

El 98% son detecciones de cámaras trampa de CONAF; el resto se reparte entre ciencia
ciudadana de iNaturalist (336), estudios científicos (296) y colecciones museológicas
(198). Antes de llegar a la tabla final, los datos pasan por seis filtros —duplicados,
coordenadas inválidas o fuera de Chile, registros de ausencia y fecha imprecisa—
documentados en `data/procesado/limpieza_bitacora.csv`.

## Estructura

```
Proyecto-Samsung-Innovacien
├── app.py                        # Punto de entrada: arma las pestañas de Streamlit
├── requirements.txt              # Dependencias de la app (lo que instala Streamlit Cloud)
├── requirements-dev.txt          # Herramientas solo para los notebooks
├── packages.txt                  # Librerías del sistema (libGL y libglib, que necesita OpenCV)
├── .streamlit/
│   └── config.toml               # Tema visual y limite de subida
│
├── core/                         # Lógica del proyecto
│   ├── modelo.py                 # Clasificador YOLO11 y umbrales por especie
│   ├── best.pt                   # Modelo entrenado (YOLO11s, 18 MB)
│   ├── ingesta.py                # Descarga y limpieza de datos desde GBIF
│   ├── datos.py                  # Carga de especies, avistamientos y reportes
│   ├── comunas.py                # Comunas de Chile con sus coordenadas
│   ├── ubicacion.py              # Región del usuario, compartida por las pestañas
│   ├── autoridades.py            # Envío del reporte a la autoridad (simulado)
│   └── theme.py                  # Estilos y componentes visuales
│
├── views/                        # Una pestaña por archivo
│   ├── alertar.py                # Subir foto, identificar especie y alertar
│   ├── cerca.py                  # Mapa de registros por región y comuna
│   ├── catalogo.py               # Fichas de las tres especies
│   ├── reportes.py               # Historial de alertas enviadas
│   └── acerca.py                 # Metodología y estado del proyecto
│
├── data/
│   ├── avistamientos.csv         # Dataset principal: 49.133 registros de GBIF
│   ├── especies.csv              # Fichas del catálogo
│   ├── zonas_urbanas.csv         # 30 zonas urbanas (clasificación urbano/rural)
│   ├── crudo/                    # Descarga en bruto de GBIF, una tabla por especie
│   ├── procesado/                # Tablas derivadas del análisis
│   ├── imagenes/                 # Fotos de portada por especie
│   └── ...                       # subidas/ y legacy/
│
└── notebooks/
    ├── 01_obtencion_y_limpieza.ipynb
    ├── 02_analisis_territorial.ipynb
    └── html/                     # Los notebooks exportados
```

## Instalación y ejecución Local

1. Clonar el repositorio:
```bash
git clone https://github.com/martindroguett/Proyecto-Samsung-Innovacien
```
2. Instalar las dependencias (requiere Python 3.10 o superior):
```bash
pip install -r requirements.txt
```
3. Levantar la aplicación:
```bash
streamlit run app.py
```

Para regenerar los datos desde GBIF:
```bash
python -m core.ingesta
```