"""Orquestación: procesar_turno + HITL (interrupt_before aplicar)."""

import uuid
from typing import Any

def procesar_turno(
    estado: dict[str, Any],
    mensaje: str,
    thread_id: str,
    max_steps: int | None = None,
) -> dict[str, Any]:
    """Un mensaje de usuario → un invoke del grafo multiagente.

    Puede terminar en pausa HITL (antes de aplicar). El mismo thread_id
    reutiliza el checkpointer MemorySaver.
    """
    print("[TODO] Implementar procesar_turno")
    return estado

def aprobar_plan(thread_id: str, aprobado: bool, estado: dict[str, Any]) -> dict[str, Any]:
    """HITL: guarda la decisión en el checkpoint y reanuda el nodo aplicar.

    1) update_state(plan_aprobado=...)
    2) invoke(None) → continúa desde interrupt_before sin input nuevo
    """
    print("[TODO] Implementar aprobar_plan")
    return estado

def nuevo_thread_id() -> str:
    return f"cultural-{uuid.uuid4().hex[:8]}"