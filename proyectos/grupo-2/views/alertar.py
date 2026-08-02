"""Pestaña principal: subir una foto, identificar la especie y alertar."""

from __future__ import annotations

import streamlit as st

from core import autoridades, datos, modelo, ubicacion
from core.comunas import obtener_comunas, obtener_coordenadas
from core.theme import tag_impacto, vacio


def render() -> None:
    st.subheader("Alertar especie invasora")
    st.write("Sube o toma una foto. La identificamos y, si es una especie invasora, "
             "preparamos el aviso para la autoridad correspondiente.")
    st.caption("El modelo reconoce jabalí, liebre europea y rata gris. "
               "Cualquier otra especie quedará sin identificar.")

    col_foto, col_resultado = st.columns([1, 1], gap="large")

    with col_foto:
        _seccion_foto()

    with col_resultado:
        _seccion_resultado()


# --------------------------------------------------------------------------
# Paso 1: la foto
# --------------------------------------------------------------------------
def _seccion_foto() -> None:
    st.markdown("#### 1. La foto")

    origen = st.radio("Origen de la imagen", ["Subir archivo", "Usar cámara"],
                      horizontal=True, label_visibility="collapsed")

    archivo = None
    if origen == "Subir archivo":
        archivo = st.file_uploader("Foto de la especie", type=["jpg", "jpeg", "png", "webp"],
                                   label_visibility="collapsed")
    else:
        archivo = st.camera_input("Tomar foto", label_visibility="collapsed")

    if archivo is None:
        st.info("Formatos aceptados: JPG, PNG o WEBP. Mientras más cerca y nitida la foto, mejor.")
        return

    st.image(archivo, caption="Imagen a analizar", width="stretch")
    st.session_state["alerta_archivo"] = archivo

    if st.button("🔍 Identificar especie", type="primary", width="stretch"):
        with st.spinner("Analizando la imagen…"):
            st.session_state["alerta_prediccion"] = modelo.clasificar(archivo.getvalue())
        st.session_state.pop("alerta_ticket", None)


# --------------------------------------------------------------------------
# Paso 2: el resultado y el envio
# --------------------------------------------------------------------------
def _seccion_resultado() -> None:
    st.markdown("#### 2. Resultado")

    pred = st.session_state.get("alerta_prediccion")
    if pred is None:
        vacio("Sube una foto y presiona «Identificar especie».<br>"
              "Aquí aparecerán la especie detectada, su impacto ambiental "
              "y el formulario de aviso.")
        return

    if pred.simulado:
        st.caption("⚠️ Resultado simulado: el modelo real todavia no esta conectado.")

    if pred.es_invasora:
        st.error(f"**{pred.especie}** — Especie invasora confirmada", icon="🚨")
    else:
        st.info(f"**{pred.especie}** — No confirmada como especie invasora", icon="❓")

    c1, c2, c3 = st.columns(3)
    c1.metric("Confianza", f"{pred.confianza * 100:.1f}%")
    c2.metric("Tipo", pred.tipo)
    c3.metric("Impacto ambiental", pred.impacto_ambiental)

    if not pred.es_invasora and pred.confianza > 0:
        st.caption("ℹ️ El modelo requiere fotos cercanas para validar la detección con certeza.")

    if pred.descripcion:
        if pred.es_invasora:
            st.markdown(tag_impacto(pred.impacto_ambiental), unsafe_allow_html=True)
        st.write(pred.descripcion)

    if pred.alternativas:
        with st.expander("Coincidencias o alternativas registradas"):
            for nombre, score in pred.alternativas:
                st.write(f"- {nombre} — {score * 100:.1f}%")

    if pred.es_invasora:
        st.divider()
        _formulario_alerta(pred)


def _formulario_alerta(pred) -> None:
    ticket = st.session_state.get("alerta_ticket")
    if ticket:
        st.success(f"Alerta registrada. Ticket **{ticket['ticket']}** "
                   f"dirigido a **{ticket['autoridad']}**.", icon="📨")
        st.caption("Envío simulado: por ahora queda guardado en la pestaña «Mis reportes».")
        if st.button("Reportar otra observación"):
            for k in ("alerta_prediccion", "alerta_ticket"):
                st.session_state.pop(k, None)
            st.rerun()
        return

    st.markdown("#### 3. Enviar aviso")
    org = autoridades.info_autoridad(pred.autoridad)
    st.caption(f"Destinatario: **{pred.autoridad}** — {org['nombre']} ({org['ambito']})")

    ubi = ubicacion.actual()

    # Desplegables interactivos de Region y Comuna
    c1, c2 = st.columns(2)
    regiones_lista = list(datos.REGIONES)
    index_reg = regiones_lista.index(ubi["region"]) if ubi["region"] in regiones_lista else 0

    region = c1.selectbox(
        "Región",
        regiones_lista,
        index=index_reg,
        key="form_alerta_region"
    )

    lista_comunas = obtener_comunas(region)
    comuna = c2.selectbox(
        "Comuna",
        lista_comunas,
        key="form_alerta_comuna"
    )

    # Coordenadas predeterminadas segun la comuna seleccionada
    lat_def, lon_def = obtener_coordenadas(region, comuna)

    with st.form("form_alerta"):
        c3, c4 = st.columns(2)
        lat = c3.number_input("Latitud", value=float(lat_def), format="%.4f")
        lon = c4.number_input("Longitud", value=float(lon_def), format="%.4f")

        contacto = st.text_input("Tu correo o teléfono (opcional)")
        comentario = st.text_area("Comentario para la autoridad",
                                  placeholder="Cantidad de ejemplares, si estaba vivo, "
                                              "referencias del lugar…")
        enviado = st.form_submit_button("📨 Enviar alerta a la autoridad",
                                        type="primary", width="stretch")

    if enviado:
        archivo = st.session_state.get("alerta_archivo")
        ruta = datos.guardar_imagen(archivo) if archivo is not None else ""
        st.session_state["alerta_ticket"] = autoridades.enviar_alerta(
            pred,
            {"region": region, "comuna": comuna, "lat": lat, "lon": lon},
            contacto=contacto,
            comentario=comentario,
            imagen=ruta,
        )
        st.rerun()
