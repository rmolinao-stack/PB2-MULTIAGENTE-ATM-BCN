"""Evaluación de respuestas generadas"""

import json
from common.config import QUERIES_EVAL_JSON
from services.rag_service import responder

def evaluar_pregunta(item: dict) -> dict:
    texto = item.get("texto", "")
    resultado = responder(texto)
    return {
        "id": item.get("id"),
        "texto": texto,
        "deberia_abstenerse": bool(item.get("deberia_abstenerse")),
        "respuesta": resultado.get("respuesta", ""),
        "fuentes": resultado.get("fuentes") or [],
        "error": resultado.get("error"),
        "notas": item.get("notas", ""),
    }

def ejecutar_evaluacion() -> None:
    if not QUERIES_EVAL_JSON.exists():
        raise FileNotFoundError(f"No existe {QUERIES_EVAL_JSON}")

    data = json.loads(QUERIES_EVAL_JSON.read_text(encoding="utf-8"))
    preguntas = data.get("preguntas", [])
    print(f"Evaluando {len(preguntas)} preguntas…\n")

    for item in preguntas:
        r = evaluar_pregunta(item)
        print("=" * 60)
        print(f"[{r['id']}] {r['texto']}")
        print(f"  deberia_abstenerse={r['deberia_abstenerse']}")
        if r.get("error"):
            print(f"  ERROR: {r['error']}")
        else:
            resp = (r.get("respuesta") or "")
            print(f"  respuesta: {resp}")
            print(f"  fuentes: {r.get('fuentes')}")
        if r.get("notas"):
            print(f"  notas: {r['notas']}")
        print()

