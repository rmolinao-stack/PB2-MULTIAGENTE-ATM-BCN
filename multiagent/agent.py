"""Orquestación: procesar_turno + HITL (interrupt_before aplicar)."""

import uuid
from typing import Any

from multiagent.graph import config_hilo, estado_inicial_grafo, get_app, hay_interrupt
from multiagent.state import estado_desde_grafo

def _marcar_hitl(estado: dict[str, Any], thread_id: str) -> dict[str, Any]:
    """Si el grafo está pausado ante aplicar, marca pendiente_hitl para la UI."""
    pendiente = hay_interrupt(thread_id)
    estado = dict(estado)
    estado["pendiente_hitl"] = pendiente
    if pendiente:
        estado["done"] = False
        resp = (estado.get("respuesta") or "").rstrip()
        aviso = "\n\n_(Plan listo: aprueba o rechaza antes de cerrar.)_"
        if "aprueba o rechaza" not in resp.lower():
            estado["respuesta"] = resp + aviso
    return estado

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
    mensaje = (mensaje or "").strip()
    if not mensaje:
        nuevo = dict(estado)
        nuevo["respuesta"] = "Escribe un mensaje (tarifas, condiciones, recorridos entre estaciones, zona de una población …)."
        return nuevo

    app = get_app()
    cfg = config_hilo(thread_id)
    n = len(estado.get("traza") or []) + 1

    try:
        inicial = estado_inicial_grafo(mensaje, max_steps=max_steps)
        resultado = app.invoke(inicial, cfg)
        nuevo = estado_desde_grafo(resultado, estado)
        if not nuevo.get("pedido_original"):
            nuevo["pedido_original"] = mensaje
        nuevo = _marcar_hitl(nuevo, thread_id)
        nuevo.setdefault("traza", []).append(
            {
                "turno": n,
                "mensaje": mensaje,
                "status": "ok",
                "done": nuevo.get("done"),
                "pendiente_hitl": nuevo.get("pendiente_hitl"),
                "log": list(resultado.get("log") or []),
                "tools": list(resultado.get("traza_tools") or []),
            }
        )
        return nuevo
    except Exception as e:  # noqa: BLE001
        nuevo = dict(estado)
        nuevo["error"] = str(e)
        nuevo["respuesta"] = (
            "No he podido continuar por un error técnico. "
            "Revisa la API key o la respuesta del modelo."
        )
        nuevo.setdefault("traza", []).append(
            {
                "turno": n,
                "mensaje": mensaje,
                "status": "error",
                "detail": str(e),
                "tools": [],
            }
        )
        return nuevo

def aprobar_plan(thread_id: str, aprobado: bool, estado: dict[str, Any]) -> dict[str, Any]:
    """HITL: guarda la decisión en el checkpoint y reanuda el nodo aplicar.

    1) update_state(plan_aprobado=...)
    2) invoke(None) → continúa desde interrupt_before sin input nuevo
    """
    app = get_app()
    cfg = config_hilo(thread_id)
    if not hay_interrupt(thread_id):
        nuevo = dict(estado)
        nuevo["respuesta"] = "No hay plan pendiente de aprobación."
        return nuevo

    app.update_state(cfg, {"plan_aprobado": bool(aprobado)})
    resultado = app.invoke(None, cfg)
    nuevo = estado_desde_grafo(resultado, estado)
    nuevo["pendiente_hitl"] = False
    nuevo.setdefault("traza", []).append(
        {
            "turno": len(estado.get("traza") or []) + 1,
            "mensaje": "HITL:" + ("aprobar" if aprobado else "rechazar"),
            "status": "ok",
            "done": nuevo.get("done"),
            "pendiente_hitl": False,
            "tools": [],
        }
    )
    return nuevo

def nuevo_thread_id() -> str:
    return f"ATM-{uuid.uuid4().hex[:8]}"