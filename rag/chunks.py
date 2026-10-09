"""Fragmentación (chunking) de documentos."""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from common.config import CHUNK_SIZE, CHUNK_OVERLAP

def _crear_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )

def fragmentar_documentos(documentos: list[Document]) -> list[Document]:
    """Parte cada documento en chunks y añade metadata útil para depurar."""
    if not documentos:
        return []

    splitter = _crear_splitter()
    chunks = splitter.split_documents(documentos)

    enriquecidos: list[Document] = []
    for i, chunk in enumerate(chunks):
        meta = dict(chunk.metadata)
        meta["chunk_index"] = i
        meta["chunk_size"] = len(chunk.page_content)
        enriquecidos.append(
            Document(page_content=chunk.page_content, metadata=meta)
        )
    return enriquecidos