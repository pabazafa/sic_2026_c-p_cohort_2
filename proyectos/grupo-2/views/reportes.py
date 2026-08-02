"""Pestaña: historial de reportes enviados desde la app."""

from __future__ import annotations

import streamlit as st

from core import datos
from core.theme import pendiente


def render() -> None:
    st.subheader("Mis reportes")
    st.write("Alertas generadas desde esta plataforma y su estado.")

    reportes = datos.cargar_reportes()

    if reportes.empty:
        st.info("Todavia no hay reportes. Genera el primero en la pestaña «Alertar animal».")
        pendiente("cuentas de usuario, para que cada persona vea solo sus reportes, "
                  "y estado real devuelto por la autoridad.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Reportes enviados", len(reportes))
    c2.metric("Especies distintas", reportes["especie"].nunique())
    c3.metric("Impacto alto", int((reportes["impacto_ambiental"] == "Alto").sum()))

    st.dataframe(
        reportes[["ticket", "fecha_hora", "especie", "impacto_ambiental", "comuna",
                  "region", "autoridad", "estado"]]
        .rename(columns={"ticket": "Ticket", "fecha_hora": "Fecha", "especie": "Especie",
                         "impacto_ambiental": "Impacto ambiental", "comuna": "Comuna", "region": "Región",
                         "autoridad": "Autoridad", "estado": "Estado"}),
        hide_index=True, width="stretch",
    )

    st.download_button("⬇️ Descargar reportes (CSV)",
                       reportes.to_csv(index=False).encode("utf-8"),
                       file_name="reportes_innovacien.csv", mime="text/csv")

    pendiente("seguimiento real del ticket con la autoridad (hoy el envío es simulado).")
