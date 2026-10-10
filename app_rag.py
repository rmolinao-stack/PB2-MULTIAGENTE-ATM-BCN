"""Interfaz Streamlit 
  streamlit run app.py
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import streamlit as st

import pandas as pd

from common.config import TOP_K
from services.rag_service import responder


def stream_palabras(texto: str, delay: float = 0.02) -> Iterator[str]:
    """Genera el texto palabra a palabra (efecto 'máquina de escribir')."""
    for palabra in texto.split():
        yield palabra + " "
        time.sleep(delay)


def mensaje_bienvenida(nombre: str) -> dict:
    """Primer mensaje del asistente al abrir (o al limpiar) el chat."""
    return {
        "role": "assistant",
        "content": (
            f"Hola — soy **{nombre}**. "
            "Pregúntame sobre las tarifas y abonos de la red ATM de Barcelona. "
            "No mantengo el contexto entre preguntas."
        ),
        "fuentes": [],
        "contexto": "",
        "modelo": "",
        "tiempo_ms": 0,
        "top_k": None,
        "num_chunks": 0,
        "error": False,
    }


def render_mensaje(message: dict) -> None:
    """Pinta un mensaje del historial en la UI (usuario o asistente)."""
    with st.chat_message(message["role"]):
        if message.get("error"):
            st.error(message["content"])
        else:
            st.markdown(message["content"])

            # Tabla simple de métricas solicitada en el enunciado
            if message.get("modelo") or message.get("tiempo_ms"):
                tabla_metricas = [{
                    "Modelo": message.get("modelo") or "N/A",
                    "Tiempo (ms)": str(message.get("tiempo_ms", 0)),
                    "Top-K": str(message.get("top_k") or "N/A"),
                    "Chunks recuperados": str(message.get("num_chunks", 0)),
                }]
                st.table(pd.DataFrame(tabla_metricas)) 

        if message.get("fuentes"):
            st.markdown("**Fuentes**")
            for fuente in message["fuentes"]:
                st.write(f"- `{fuente}`")

        if message.get("contexto"):
            with st.expander("Contexto recuperado (debug)"):
                st.text(message["contexto"])


# --- Configuración de la página ---
st.set_page_config(
    page_title="Asistente de tarifas y abonos ATM",
    page_icon="🚆",
    layout="centered",
)

# Estilo CSS para centrar todas las cabeceras (th) y celdas (td) de las tablas en Streamlit
st.markdown(
    """
    <style>
    div[data-testid="stTable"] th, div[data-testid="stTable"] td {
        text-align: center !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar ---
with st.sidebar:
    st.header("Configuración")
    nombre_bot = st.text_input("Nombre del bot", value="Asistente de tarifas y abonos ATM")
    top_k = st.slider("Top-K (chunks)", min_value=1, max_value=5, value=TOP_K)
    st.caption("Índice: `output/chroma_db/` (ejecuta `python main.py --prepare --index`).")
    if st.button("Limpiar chat", use_container_width=True):
        st.session_state.messages = [mensaje_bienvenida(nombre_bot)]
        st.rerun()

st.title(nombre_bot)
st.caption("Asistente de tarifas y abonos ATM")

# --- Historial ---
if "messages" not in st.session_state:
    st.session_state.messages = [mensaje_bienvenida(nombre_bot)]

for message in st.session_state.messages:
    render_mensaje(message)

# --- Nuevo mensaje del usuario ---
if prompt := st.chat_input("Tu pregunta sobre las tarifas y abonos de la red ATM de Barcelona…"):
    st.session_state.messages.append(
        {"role": "user", "content": prompt, "fuentes": [], "contexto": "", "error": False}
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Consultando el corpus…", expanded=False) as status:
            resultado = responder(prompt, top_k=top_k)
            status.update(label="Listo", state="complete")

        if resultado.get("error"):
            st.error(resultado["error"])
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": resultado["error"],
                    "fuentes": resultado.get("fuentes") or [],
                    "contexto": resultado.get("contexto") or "",
                    "modelo": resultado.get("modelo") or "",
                    "tiempo_ms": resultado.get("tiempo_ms") or 0,
                    "top_k": top_k,
                    "num_chunks": 0,
                    "error": True,
                }
            )
        else:
            # 1) Streaming de texto
            escrito = st.write_stream(stream_palabras(resultado["respuesta"]))
            contenido = escrito if isinstance(escrito, str) else resultado["respuesta"]

            # Extracción de métricas
            modelo = resultado.get("modelo") or ""
            tiempo_ms = resultado.get("tiempo_ms") or 0
            # Extrae la cantidad real de chunks devueltos por el retriever
            chunks_recuperados = len(resultado.get("chunks") or resultado.get("fuentes") or [])

            # 2) Renderizado inmediato de la Tabla Simple de Métricas
            tabla_metricas = [{
                    "Modelo": modelo or "N/A",
                    "Tiempo (ms)": str(tiempo_ms),
                    "Top-K": str(top_k) or "N/A",
                    "Chunks recuperados": str(chunks_recuperados),
                }]
            st.table(pd.DataFrame(tabla_metricas))

            # 3) Fuentes y contexto
            if resultado.get("fuentes"):
                st.markdown("**Fuentes**")
                for fuente in resultado["fuentes"]:
                    st.write(f"- `{fuente}`")

            if resultado.get("contexto"):
                with st.expander("Contexto recuperado (debug)"):
                    st.text(resultado["contexto"])

            # 4) Guardar en historial con las métricas tabulares incorporadas
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": contenido,
                    "fuentes": resultado.get("fuentes") or [],
                    "contexto": resultado.get("contexto") or "",
                    "modelo": modelo,
                    "tiempo_ms": tiempo_ms,
                    "top_k": top_k,
                    "num_chunks": chunks_recuperados,
                    "error": False,
                }
            )