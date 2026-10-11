"""Grafo multiagente: supervisor ↔ especialistas + HITL.

Flujo:
  START → supervisor ──┬── tarifas_zonas ──────┐
                       ├── tiempos_TMB ────────┼──► supervisor → …
                       ├── recorridos ─────────┤
                       └── sintetizar ─────────┘
                                  │
                     FINISH → aplicar (interrupt_before) → END

Stack: LangChain (ChatGoogleGenerativeAI + @tool) + LangGraph (MemorySaver).
"""

from typing import Annotated, Any, Literal, TypedDict
from common.config import MAX_STEPS_DEFAULT

def _acumular(actual: list, nuevo: list) -> list:
    """Reducer de LangGraph: concatena listas (no pisa el valor anterior)."""
    return (actual or []) + (nuevo or [])

class EstadoGrafo(TypedDict):
    pedido: str  # mensaje del usuario
    notas_tarifas_zonas: str  # las escribe el especialista tarifas y zonas
    notas_tiempos_TMB: str  # las escribe el especialista de tiempos de espera de metro de TMB
    notas_recorridos: str  # las escribe el especialista recorridos que usará plano_ATM.jpg (equivalente a notas_vision)
    respuesta: str  # texto del plan (sintetizar / aplicar)
    plan: list  # viñetas del plan (≥2 para HITL)
    siguiente: str  # lo elige el supervisor: tarifas_zonas|tiempos_TMB|recorridos|sintetizar|FINISH
    iteracion: int  # contador del supervisor (tope MAX_ITER)
    log: Annotated[list, _acumular]  # traza legible del orquestador
    traza_tools: Annotated[list, _acumular]  # tools usadas en los especialistas
    max_steps: int  # tope modelo↔tools dentro de un especialista
    plan_aprobado: bool  # lo escribe el humano vía update_state (HITL)
    done: bool  # True solo tras aprobar en aplicar
    pendiente_hitl: bool  # True mientras el grafo está pausado antes de aplicar


OPCIONES = ("tarifas_zonas", "tiempos_TMB", "recorridos", "sintetizar", "FINISH")

def build_graph():
    """Monta el grafo: especialistas vuelven al supervisor; HITL ante aplicar."""
    print("="*20 + " [TODO]"*5 + " Implementar build_graph " + "[TODO] "*5 + "="*20)
    return None

_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = build_graph()
    return _APP

def config_hilo(thread_id: str) -> dict:
    """Config de LangGraph: identifica el hilo del checkpointer."""
    return {"configurable": {"thread_id": thread_id}}

def estado_inicial_grafo(pedido: str, max_steps: int | None = None) -> EstadoGrafo:
    return {
        "pedido": pedido,
        "notas_tarifas_zonas": "",
        "notas_tiempos_TMB": "",
        "notas_recorridos": "",
        "respuesta": "",
        "plan": [],
        "siguiente": "",
        "iteracion": 0,
        "log": [],
        "traza_tools": [],
        "max_steps": max_steps if max_steps is not None else MAX_STEPS_DEFAULT,
        "plan_aprobado": False,
        "done": False,
        "pendiente_hitl": False,
    }

def hay_interrupt(thread_id: str) -> bool:
    """True si el hilo está pausado antes de aplicar (HITL pendiente).

    get_state(...).next incluye el nombre del siguiente nodo bloqueado.
    """
    snap = get_app().get_state(config_hilo(thread_id))
    nxt = snap.next or ()
    return "aplicar" in nxt
