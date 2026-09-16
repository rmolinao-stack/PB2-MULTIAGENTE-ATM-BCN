from pathlib import Path
import re

def _extraer_fuentes(chunks: list[dict]) -> list[str]:
    fuentes: list[str] = []
    vistos: set[str] = set()
    for chunk in chunks:
        source = chunk.get("metadata", {}).get("source", "?")
        nombre = Path(str(source)).name
        if nombre not in vistos:
            vistos.add(nombre)
            fuentes.append(nombre)
    return fuentes

def _normalizar_texto(texto: str) -> str:
    """Convierte a minúsculas y elimina artículos al inicio de palabra (el, la, els, les, l')."""
    t = texto.lower()
    t = re.sub(r"\b(el|la|els|les)\b\s*", "", t)
    t = re.sub(r"\bl['’]", "", t)
    return re.sub(r'\s+', ' ', t).strip()