from multiagent.agent import aprobar_plan, nuevo_thread_id, procesar_turno
from multiagent.state import crear_estado

from typing import Any

def service_aprobar_plan(thread_id, aprobado, agent_state):
    """Servicio que aprueba o rechaza un plan del multiagente."""
    return aprobar_plan(thread_id, aprobado, agent_state)

def service_nuevo_thread_id():
    """Servicio que genera un nuevo ID de conversación para el multiagente."""
    return nuevo_thread_id()

def service_ejecutar_plan(
    estado: dict[str, Any],
    mensaje: str,
    thread_id: str,
    max_steps: int | None = None,
) -> dict[str, Any]:
    """Servicio que ejecuta el workflow del multiagente."""
    return procesar_turno(estado, mensaje, thread_id, max_steps=max_steps)

def service_crear_estado(param):
    """Servicio que crea un nuevo estado para el multiagente."""
    return crear_estado(param)
