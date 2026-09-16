"""Generación de embeddings con Gemini."""

import json
import time
from pathlib import Path

from google import genai
from google.genai import types

from common.config import CHUNKS_JSON, EMBEDDING_MODEL, EMBEDDING_SLEEP, EMBEDDINGS_JSON, MAX_CHUNKS_EMBED, EMBED_BATCH_SIZE

from .gemini_auth import configurar_gemini_api_key

def _extraer_vector(embedding_obj) -> list[float]:
    if hasattr(embedding_obj, "values"):
        return list(embedding_obj.values)
    return list(embedding_obj)

def cargar_chunks_json() -> list[dict]:
    if not CHUNKS_JSON.exists():
        raise FileNotFoundError(
            f"No existe {CHUNKS_JSON}. Ejecuta antes: python main.py --prepare"
        )
    data = json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))
    return data.get("chunks", [])

def embeddear_textos(client: genai.Client, textos: list[str]) -> list[list[float]]:
    if not textos:
        return []

    vectores: list[list[float]] = []
    loop = 0
    for inicio in range(0, len(textos), EMBED_BATCH_SIZE):
        #RMO: La primera vez no esperamos, el resto sí.
        if loop > 0:
            time.sleep(EMBEDDING_SLEEP)
        print("Embeddings: lote", loop + 1, "de", (len(textos) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE)
        loop += 1
        lote = textos[inicio : inicio + EMBED_BATCH_SIZE]
        contents = [types.Content(parts=[types.Part(text=t)]) for t in lote]
        result = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=contents,
                    )
        lote_vectores = [_extraer_vector(emb) for emb in result.embeddings]
        if len(lote_vectores) != len(lote):
            raise RuntimeError(
                f"Se esperaban {len(lote)} embeddings, se recibieron {len(lote_vectores)}."
                )
        vectores.extend(lote_vectores) 
    return vectores

def embeddear_consulta(client: genai.Client, pregunta: str) -> list[float]:
    vectores = embeddear_textos(client, [pregunta])
    return vectores[0]

def ejecutar_embeddings() -> tuple[list[dict], Path]:
    """chunks.json → vectores → embeddings.json."""
    configurar_gemini_api_key()
    client = genai.Client()

    chunks = cargar_chunks_json()
    total_disponibles = len(chunks)

    if MAX_CHUNKS_EMBED is not None:
        chunks = chunks[:MAX_CHUNKS_EMBED]

    textos = [c["text"] for c in chunks]

    inicio = time.perf_counter()
    vectores = embeddear_textos(client, textos)
    latencia_ms = (time.perf_counter() - inicio) * 1000

    print(
        f"Embeddings: {len(textos)} chunks en {latencia_ms:.0f} ms ({EMBEDDING_MODEL})"
    )
    if len(textos) < total_disponibles:
        print(f"  (de {total_disponibles} en {CHUNKS_JSON.name}; ver MAX_CHUNKS_EMBED)")

    items = []
    for chunk, vector in zip(chunks, vectores):
        items.append(
            {
                "text": chunk["text"],
                "vector": vector,
                "metadata": chunk.get("metadata", {}),
            }
        )

    payload = {
        "embedding_model": EMBEDDING_MODEL,
        "total": len(items),
        "total_chunks_en_origen": total_disponibles,
        "dimensions": len(vectores[0]) if vectores else 0,
        "items": items,
    }

    EMBEDDINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    EMBEDDINGS_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  Guardado: {EMBEDDINGS_JSON} ({payload['dimensions']} dimensiones)")

    return items, EMBEDDINGS_JSON