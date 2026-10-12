import os
import unicodedata
import difflib
from pathlib import Path
import pandas as pd
from langchain_core.tools import tool

from google import genai
from google.genai import types

from common.config import ESTACIONS_CSV_PATH, GEMINI_MODEL, AGENT_TEMPERATURE

def _normalizar(texto: str) -> str:
    """Limpia el texto convirtiendo a minúsculas y eliminando tildes/diacríticos."""
    texto = str(texto).lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )

@tool
def obtener_id_estacion_determinista(nombre_estacion: str) -> str:
    """
    Busca y devuelve el ID_ESTACION de una estación de la red ATM a partir de su nombre.
    Admite nombres parciales, faltas de ortografía o variaciones idiomáticas.
    """
    path = ESTACIONS_CSV_PATH
    if not path.exists():
        return f"Error: no hay archivo CSV en {path}"

    try:
        df = pd.read_csv(path, sep=";")
        if "ID_ESTACION" not in df.columns or "NOMBRE_ESTACION" not in df.columns:
            return "Error: el CSV debe incluir las columnas 'ID_ESTACION' y 'NOMBRE_ESTACION'."

        target_norm = _normalizar(nombre_estacion)
        df["norm_name"] = df["NOMBRE_ESTACION"].apply(_normalizar)

        # 1. Coincidencia exacta
        exact = df[df["norm_name"] == target_norm]
        if not exact.empty:
            row = exact.iloc[0]
            return f"ID_ESTACION: {row['ID_ESTACION']} (Estación: {row['NOMBRE_ESTACION']})"

        # 2. Búsqueda por subcadena (ej: "Carrilet" en "Av. Carrilet")
        contains = df[df["norm_name"].str.contains(target_norm, regex=False)]
        if not contains.empty:
            row = contains.iloc[0]
            return f"ID_ESTACION: {row['ID_ESTACION']} (Estación: {row['NOMBRE_ESTACION']})"

        # 3. Coincidencia difusa (fuzzy match) para erratas (ej: "Once de Setiembre" -> "Onze de Setembre")
        nombres_lista = df["norm_name"].tolist()
        coincidencias = difflib.get_close_matches(target_norm, nombres_lista, n=1, cutoff=0.4)
        if coincidencias:
            row = df[df["norm_name"] == coincidencias[0]].iloc[0]
            return f"ID_ESTACION: {row['ID_ESTACION']} (Estación: {row['NOMBRE_ESTACION']})"

        return f"No se encontró ninguna estación correspondiente a '{nombre_estacion}'."

    except Exception as e:
        return f"Error al procesar el CSV: {e}"


@tool
def obtener_id_estacion_gemini(nombre_estacion: str) -> str:
    """Obtiene el ID_ESTACION del CSV utilizando Gemini para interpretar nombres ambiguos, incompletos o mal escritos."""
    path = ESTACIONS_CSV_PATH
    if not path.exists():
        return f"Error: no hay archivo CSV en {path}"

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return "Error: falta GEMINI_API_KEY"

        contenido_csv = path.read_text(encoding="utf-8")
        client = genai.Client(api_key=api_key)

        prompt = (
            f"A partir del siguiente archivo CSV con el listado de estaciones:\n\n"
            f"{contenido_csv}\n\n"
            f"Encuentra la estación solicitada: '{nombre_estacion}'.\n"
            f"El usuario puede haber escrito el nombre con errores, de forma parcial o traducida (ejemplos: 'Carrilet' -> 'Av. Carrilet', 'Once de Setiembre' -> 'Onze de Setembre').\n"
            f"Responde estrictamente en el siguiente formato: 'ID_ESTACION: <ID> (Estación: <NOMBRE_OFICIAL>)'."
        )

        out = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=AGENT_TEMPERATURE
            )
        )
        return (out.text or "").strip() or "Error: respuesta vacía del modelo."

    except Exception as e:
        return f"Error al consultar la estación con Gemini: {e}"