"""Orquestación del pipeline de ingesta.

Flujo: load → clean → chunk → guardar chunks.json
"""

import json
from collections import Counter
from pathlib import Path

from langchain_core.documents import Document

from .load import cargar_documentos
from .clean import limpiar_documentos
from .chunks import fragmentar_documentos
from common.config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, CHUNKS_JSON

def _nombre_fuente(metadata: dict) -> str:
    source = metadata.get("source", "desconocido")
    return Path(str(source)).name

def calcular_stats_ingesta(
    crudos: list[Document],
    limpios: list[Document],
    chunks: list[Document],
) -> dict:
    return {
        "documentos_cargados": len(crudos),
        "documentos_tras_limpieza": len(limpios),
        "chunks_generados": len(chunks),
        "documentos_por_fuente": dict(
            Counter(_nombre_fuente(d.metadata) for d in crudos)
        ),
        "chunks_por_fuente": dict(
            Counter(_nombre_fuente(c.metadata) for c in chunks)
        ),
    }

def documentos_a_dicts(documentos: list[Document]) -> list[dict]:
    return [
        {"text": doc.page_content, "metadata": dict(doc.metadata)}
        for doc in documentos
    ]


def guardar_chunks_json(chunks: list[Document], ruta: Path, stats: dict) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "chunk_size_config": {
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
        },
        "total_chunks": len(chunks),
        "ingesta_stats": stats,
        "chunks": documentos_a_dicts(chunks),
    }

    ruta.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta

def imprimir_resumen_consola(chunks: list[Document], stats: dict) -> None:
    print("\n--- Resumen ingesta ---")
    print(f"  Documentos cargados:      {stats['documentos_cargados']}")
    print(f"  Tras limpieza:            {stats['documentos_tras_limpieza']}")
    print(f"  Chunks generados:         {stats['chunks_generados']}")
    print("  Chunks por fuente:")
    for fuente, n in sorted(stats["chunks_por_fuente"].items()):
        print(f"    {fuente}: {n}")

    #RMO: No mostramos los chunks de ejemplo para no saturar la consola.
    #if not chunks:
    #    return

    #_mostrar_chunk_ejemplo("Muestra: primer chunk", chunks[0])

    #for chunk in chunks:
    #    if chunk.metadata.get("tipo") == "Tarifas_por_zonan" or chunk.metadata.get("tipo") == "Municipios_por_zona":
    #        _mostrar_chunk_ejemplo("Muestra: medición CSV", chunk)
    #        break

def ejecutar_ingesta() -> tuple[list[Document], Path, dict]:
    """Ejecuta la ingesta de documentos y genera los chunks para embeddings."""
    print(f"Ingesta: cargando documentos desde {DATA_DIR} ...")
    crudos = cargar_documentos()
    print(f" Documentos cargados: {len(crudos)}")

    limpios = limpiar_documentos(crudos)
    print(f"  Tras limpieza: {len(limpios)}")

    # RMO: Para depurar que nos devuelve cada documento limpiado.
    #for c in limpios:
    #    print(c)
    #    input()

    chunks = fragmentar_documentos(limpios)
    print(f"  Chunks generados: {len(chunks)}")

    #RMO: Para depurar que nos devuelve cada chunk.
    #for c in chunks:
    #    print(c)
    #    input()

    stats = calcular_stats_ingesta(crudos, limpios, chunks)
    ruta = guardar_chunks_json(chunks, CHUNKS_JSON, stats)
    print(f"  Guardado: {ruta}")

    imprimir_resumen_consola(chunks, stats)
    return chunks, ruta, stats