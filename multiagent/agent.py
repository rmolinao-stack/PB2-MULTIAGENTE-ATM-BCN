"""Orquestación: procesar_turno + HITL (interrupt_before aplicar)."""

import uuid
from typing import Any

def nuevo_thread_id() -> str:
    return f"cultural-{uuid.uuid4().hex[:8]}"