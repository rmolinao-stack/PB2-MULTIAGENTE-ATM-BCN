
"""Limpieza de texto antes del chunking."""

import re
from langchain_core.documents import Document
from pathlib import Path

def normalizar_texto(texto: str) -> str:
    """Deja el texto listo para fragmentar: menos ruido, mismas frases."""
    if not texto:
        return ""

    t = texto.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = "\n".join(linea.strip() for linea in t.split("\n"))
    return t.strip()

def limpiar_metadatos_fuente(doc: Document) -> Document:
    """Normaliza la propiedad 'source' para conservar solo el nombre del fichero."""
    if "source" in doc.metadata:
        doc.metadata["source"] = Path(doc.metadata["source"]).name
    return doc

def limpiar_documentos(documentos: list[Document]) -> list[Document]:
    """Aplica normalizar_texto a cada documento; omite los que quedan vacíos."""
    limpios: list[Document] = []
    for doc in documentos:
        contenido = normalizar_texto(doc.page_content)
        meta = dict(doc.metadata)
        meta = limpiar_metadatos_fuente(Document(page_content="", metadata=meta)).metadata
        if not contenido:
            continue
        limpios.append(
            Document(page_content=contenido, metadata=meta)
        )
    return limpios