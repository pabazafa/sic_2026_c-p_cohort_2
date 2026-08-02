"""Envio de alertas a las autoridades competentes.

Estado actual: SIMULADO. El reporte se guarda en data/reportes.csv y se genera
un numero de ticket, pero todavia no sale nada de la app.

TODO (equipo): implementar el envio real. Opciones a evaluar:
  - Correo con smtplib / SendGrid a la casilla oficial de cada servicio.
  - Formulario o API del servicio, si existe.
  - Webhook intermedio (Zapier / n8n) mientras conseguimos el canal oficial.
Importante: confirmar el canal de contacto oficial antes de enviar nada real.
"""

from __future__ import annotations

from datetime import datetime

from core.datos import cargar_reportes, guardar_reporte

# TODO (equipo): reemplazar los contactos por los canales oficiales verificados.
AUTORIDADES = {
    "SAG": {
        "nombre": "Servicio Agricola y Ganadero",
        "ambito": "Fauna terrestre, plagas agricolas y sanidad animal",
        "contacto": "PENDIENTE",
    },
    "CONAF": {
        "nombre": "Corporacion Nacional Forestal",
        "ambito": "Flora invasora, bosque nativo y áreas protegidas",
        "contacto": "PENDIENTE",
    },
    "SERNAPESCA": {
        "nombre": "Servicio Nacional de Pesca y Acuicultura",
        "ambito": "Especies acuaticas, rios, lagos y borde costero",
        "contacto": "PENDIENTE",
    },
    "MMA": {
        "nombre": "Ministerio del Medio Ambiente",
        "ambito": "Coordinacion nacional de especies exóticas invasoras",
        "contacto": "PENDIENTE",
    },
}


def _nuevo_ticket() -> str:
    n = len(cargar_reportes()) + 1
    return f"INV-{datetime.now():%Y%m%d}-{n:04d}"


def enviar_alerta(prediccion, ubicacion: dict, contacto: str = "",
                  comentario: str = "", imagen: str = "") -> dict:
    """Registra la alerta y devuelve el reporte con su numero de ticket.

    Hoy solo persiste en local. Cuando exista el canal real, este es el unico
    lugar que hay que cambiar.
    """
    reporte = {
        "ticket": _nuevo_ticket(),
        "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "especie": prediccion.especie,
        "confianza": prediccion.confianza,
        "tipo": prediccion.tipo,
        "impacto_ambiental": prediccion.impacto_ambiental,
        "region": ubicacion.get("region", ""),
        "comuna": ubicacion.get("comuna", ""),
        "lat": ubicacion.get("lat", ""),
        "lon": ubicacion.get("lon", ""),
        "autoridad": prediccion.autoridad,
        "estado": "Enviado (simulado)",
        "contacto": contacto,
        "comentario": comentario,
        "imagen": imagen,
    }
    guardar_reporte(reporte)
    return reporte


def info_autoridad(sigla: str) -> dict:
    return AUTORIDADES.get(sigla, {"nombre": sigla, "ambito": "", "contacto": "PENDIENTE"})
