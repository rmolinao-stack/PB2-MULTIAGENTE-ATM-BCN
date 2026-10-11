"""Grafo multiagente: supervisor ↔ especialistas + HITL.

Flujo:
  START → supervisor ──┬── tarifas_y_zonas ────┐
                       ├── tiempos_TMB ────────┼──► supervisor → …
                       ├── recorridos ─────────┤
                       └── sintetizar ─────────┘
                                  │
                     FINISH → aplicar (interrupt_before) → END

Stack: LangChain (ChatGoogleGenerativeAI + @tool) + LangGraph (MemorySaver).
"""



from typing import Annotated, Any, Literal, TypedDict

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
    siguiente: str  # lo elige el supervisor: tarifas_y_zonas|tiempos_TMB|recorridos|sintetizar|FINISH
    iteracion: int  # contador del supervisor (tope MAX_ITER)
    log: Annotated[list, _acumular]  # traza legible del orquestador
    traza_tools: Annotated[list, _acumular]  # tools usadas en los especialistas
    max_steps: int  # tope modelo↔tools dentro de un especialista
    plan_aprobado: bool  # lo escribe el humano vía update_state (HITL)
    done: bool  # True solo tras aprobar en aplicar
    pendiente_hitl: bool  # True mientras el grafo está pausado antes de aplicar


OPCIONES = ("tarifas_y_zonas", "tiempos_TMB", "recorridos", "sintetizar", "FINISH")