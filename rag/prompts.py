"""Construcción del prompt RAG .
"""

INSTRUCCIONES_RAG = """Eres un asistente que responde preguntas sobre tarifas y abonos para la red ATM de Barcelona 
que es el sistema tarifario integrado que permite utilizar diferentes medios de transporte (metro, autobuses, Ferrocarrils y Rodalies). 

Reglas:
- Responde ÚNICAMENTE con la información del contexto proporcionado.
- Si el contexto no contiene información suficiente, indícalo explícitamente.
- Cuando cites un hecho, menciona la fuente si aparece en el contexto o en la información geográfica extraída del CSV.
- No inventes eventos, fechas ni datos que no estén en el contexto.
- No eres un asistente de rutas, solo de tarifas y abonos de la red ATM de Barcelona.
"""

from pathlib import Path

from common.config import DATA_DIR
from common.utils import _normalizar_texto, extraer_info_municipios_normalizado


def build_rag_prompt(contexto: str, pregunta: str) -> str:
    """Ensambla el prompt completo para el LLM."""
    return (
        f"{INSTRUCCIONES_RAG}\n\n"
        f"{extraer_info_municipios_normalizado(pregunta, Path(f"{DATA_DIR}/01_Municipios_por_zona_y_tarifa_metropolitana.csv"))}\n\n"
        f"--- CONTEXTO RECUPERADO ---\n"
        f"{contexto.strip()}\n\n"
        f"--- PREGUNTA ---\n"
        f"{pregunta.strip()}\n\n"
        f"--- RESPUESTA ---"
    )
