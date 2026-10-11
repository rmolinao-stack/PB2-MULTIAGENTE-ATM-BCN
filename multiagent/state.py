import copy
from typing import Any


def crear_estado(pedido: str = "") -> dict[str, Any]:
    """Plantilla visible en Streamlit / resumen CLI."""
    return {
        "objetivo": "Planifica rutas y tarifas dentro de la red de ATM. Calcula el tiempo en llegar el próximo metro de TMB" ,
        "pedido_original": pedido,
        "pedido": pedido,
        "notas_tarifas_zonas": "",
        "notas_practico": "",
        "notas_vision": "",
        "respuesta": "",
        "plan": [],
        "siguiente": "",
        "iteracion": 0,
        "log": [],
        "traza_tools": [],
        "done": False,
        "error": None,
        "pendiente_hitl": False,
        "plan_aprobado": False,
        "preferencias": {
            "intereses": None,
            "presupuesto": None,
            "zona": None,
            "duracion_horas": None,
        },
        "traza": [],
    }