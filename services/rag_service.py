""" Aquí vamos a incluir los servicios relacionados 
con RAG (Retrieval-Augmented Generation) 
para el asistente de tarifas de ATM BCN.

El frontend (o quien los consuma) llamará a estas funciones.
"""

import time

from common.config import GEMINI_MODEL
from rag.retriever import recuperar
from rag.context import formatear_contexto
from rag.prompts import build_rag_prompt
from rag.generate import generar_respuesta
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
    """Función auxiliar para realizar un RAG completo y devolver solo la respuesta generada."""
    resultado = responder(consulta)
    return resultado.get("respuesta") if resultado else None