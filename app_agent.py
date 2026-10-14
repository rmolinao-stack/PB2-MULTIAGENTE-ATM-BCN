"""App Streamlit — cliente del grafo multiagente (ATM).

  streamlit run app_agent.py
"""

import streamlit as st

from common.config import MAX_TURNS_DEFAULT, MAX_STEPS_DEFAULT
from multiagent.agent import aprobar_plan, nuevo_thread_id
from multiagent.state import crear_estado
#from src.agent import aprobar_plan, nuevo_thread_id, procesar_turno
#from src.state import crear_estado

st.set_page_config(
    page_title="ATeMto - Tu agente de ATM",
    page_icon="🚆",
    layout="centered",
)

SALUDO = (
    "Hola — soy ATeMto, tu agente planificador de la red de transporte de ATM de Barcelona."
    "Soy capaz de darte una ruta eficiente entre dos estaciones de la red ATM,"
    "darte el mejor abono de transporte según tus necesidades e incluso "
    "decirte cuando va llegar el siguiente tren (solo estaciones de TMB)."
    "Preguntame y te daré un plan listo para que lo apruebes en la barra lateral."
)


def _reset() -> None:
    st.session_state.messages = [{"role": "assistant", "content": SALUDO}]
    st.session_state.agent_state = crear_estado("")
    st.session_state.thread_id = nuevo_thread_id()

with st.sidebar:
    st.header("Configuración")
    max_turns = st.slider(
        "max_turns",
        min_value=1,
        max_value=12,
        value=MAX_TURNS_DEFAULT,
    )
    max_steps = st.slider(
        "max_steps (tools por especialista)",
        min_value=1,
        max_value=8,
        value=MAX_STEPS_DEFAULT,
    )
    st.caption(f"thread_id: `{st.session_state.get('thread_id', '—')}`")

    estado_side = st.session_state.get("agent_state") or {}
    if estado_side.get("pendiente_hitl"):
        st.divider()
        st.subheader("HITL — aprobar plan")
        for item in estado_side.get("plan") or []:
            st.markdown(f"- {item}")
        c1, c2 = st.columns(2)
        if c1.button("Aprobar", use_container_width=True, type="primary"):
            st.session_state.agent_state = aprobar_plan(
                st.session_state.thread_id, True, st.session_state.agent_state
            )
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": st.session_state.agent_state.get("respuesta")
                    or "Plan aprobado.",
                }
            )
            st.rerun()
        if c2.button("Rechazar", use_container_width=True):
            st.session_state.agent_state = aprobar_plan(
                st.session_state.thread_id, False, st.session_state.agent_state
            )
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": st.session_state.agent_state.get("respuesta")
                    or "Plan rechazado.",
                }
            )
            st.rerun()

    if st.button("Nueva conversación", use_container_width=True):
        #_reset()
        st.rerun()

st.title("ATeMto - Tu agente de ATM")
#st.caption("Multiagente · ATM")