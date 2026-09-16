""" Aquí vamos a incluir los servicios relacionados 
con RAG (Retrieval-Augmented Generation) 
para el asistente de tarifas de ATM BCN.

El frontend (o quien los consuma) llamará a estas funciones.
"""

import time

from common.config import GEMINI_MODEL
from core.retriever import recuperar
from core.context import formatear_contexto
from core.prompts import build_rag_prompt
from core.generate import generar_respuesta
from common.utils import _extraer_fuentes

def responder(pregunta: str, top_k: int | None = None) -> dict:
    """Pipeline: retrieve → prompt → generate."""
    started = time.time()
    if not (pregunta or "").strip():
        elapsed_ms = int((time.time() - started) * 1000)
        return {
            "respuesta": "",
            "contexto": "",
            "chunks": [],
            "fuentes": [],
            "modelo": GEMINI_MODEL,
            "tiempo_ms": elapsed_ms,
            "error": "La pregunta no puede estar vacía.",
        }

    chunks = recuperar(pregunta.strip(), top_k=top_k)
    contexto = formatear_contexto(chunks)
    prompt = build_rag_prompt(contexto, pregunta.strip())
    #print(f"Prompt construido:\n{prompt}\n")
    respuesta = generar_respuesta(prompt)

    elapsed_ms = int((time.time() - started) * 1000)

    return {
        "respuesta": respuesta,
        "contexto": contexto,
        "chunks": chunks,
        "fuentes": _extraer_fuentes(chunks),
        "modelo": GEMINI_MODEL,
        "tiempo_ms": elapsed_ms,
        "error": None,
    }

def rag_ask(consulta: str) -> str:
    """Pendiente documentar."""
    print("rag_ask: Pendiente de realizar")    
    return None