import os
import json
import time
import re
import unicodedata
import difflib
from pathlib import Path
import pandas as pd
from langchain_core.tools import tool

from google import genai
from google.genai import types, errors


from common.config import ESTACIONS_CSV_PATH, GEMINI_MODEL, AGENT_TEMPERATURE

#def _normalizar(texto: str) -> str:
#    """Limpia el texto convirtiendo a minúsculas y eliminando tildes/diacríticos."""
#    texto = str(texto).lower().strip()
#    return "".join(
#        c for c in unicodedata.normalize("NFD", texto)
#        if unicodedata.category(c) != "Mn"
#    )
#
#@tool
#def obtener_id_estacion_determinista(nombre_estacion: str) -> str:
#    """
#    Busca y devuelve el ID_ESTACION de una estación de la red ATM a partir de su nombre.
#    Admite nombres parciales, faltas de ortografía o variaciones idiomáticas.
#    """
#    path = ESTACIONS_CSV_PATH
#    if not path.exists():
#        return f"Error: no hay archivo CSV en {path}"
#
#    try:
#        df = pd.read_csv(path, sep=";")
#        if "ID_ESTACION" not in df.columns or "NOMBRE_ESTACION" not in df.columns:
#            return "Error: el CSV debe incluir las columnas 'ID_ESTACION' y 'NOMBRE_ESTACION'."
#
#        target_norm = _normalizar(nombre_estacion)
#        df["norm_name"] = df["NOMBRE_ESTACION"].apply(_normalizar)
#
#        # 1. Coincidencia exacta
#        exact = df[df["norm_name"] == target_norm]
#        if not exact.empty:
#            row = exact.iloc[0]
#            return f"ID_ESTACION: {row['ID_ESTACION']} (Estación: {row['NOMBRE_ESTACION']})"
#
#        # 2. Búsqueda por subcadena (ej: "Carrilet" en "Av. Carrilet")
#        contains = df[df["norm_name"].str.contains(target_norm, regex=False)]
#        if not contains.empty:
#            row = contains.iloc[0]
#            return f"ID_ESTACION: {row['ID_ESTACION']} (Estación: {row['NOMBRE_ESTACION']})"
#
#        # 3. Coincidencia difusa (fuzzy match) para erratas (ej: "Once de Setiembre" -> "Onze de Setembre")
#        nombres_lista = df["norm_name"].tolist()
#        coincidencias = difflib.get_close_matches(target_norm, nombres_lista, n=1, cutoff=0.4)
#        if coincidencias:
#            row = df[df["norm_name"] == coincidencias[0]].iloc[0]
#            return f"ID_ESTACION: {row['ID_ESTACION']} (Estación: {row['NOMBRE_ESTACION']})"
#
#        return f"No se encontró ninguna estación correspondiente a '{nombre_estacion}'."
#
#    except Exception as e:
#        return f"Error al procesar el CSV: {e}"

@tool
def obtener_id_estacion_gemini(
    nombre_estacion: str, max_reintentos: int = 3, espera_base: int = 2
) -> dict:
  """Obtiene el ID_ESTACION del CSV utilizando Gemini para interpretar nombres ambiguos, incompletos o mal escritos.

  Devuelve siempre un dict con 'ID_ESTACION' y 'NOMBRE_ESTACION' o con la clave 'ERROR'. Ejemplo:
  {"ID_ESTACION": 113, "NOMBRE_ESTACION": "Av. Carrilet"}
  {"ERROR": "No se encontró la estación."}
  """
  path = ESTACIONS_CSV_PATH
  if not path.exists():
    return {"ERROR": f"No hay archivo CSV en {path}"}

  api_key = os.environ.get("GEMINI_API_KEY")
  if not api_key:
    return {"ERROR": "Falta GEMINI_API_KEY en las variables de entorno"}

  try:
    contenido_csv = path.read_text(encoding="utf-8")
  except Exception as e:
    return {"ERROR": f"Error al leer el archivo CSV: {e}"}

  prompt = (
      f"A partir del siguiente archivo CSV con el listado de estaciones:\n\n"
      f"{contenido_csv}\n\n"
      f"Encuentra la estación solicitada: '{nombre_estacion}'.\n"
      f"El usuario puede haber escrito el nombre con errores, de forma parcial"
      f" o traducida (ejemplos: 'Carrilet' -> 'Av. Carrilet', 'Once de"
      f" Setiembre' -> 'Onze de Setembre').\n"
      f"Responde estrictamente con un objeto JSON válido con los campos"
      f" 'ID_ESTACION' (entero) y 'NOMBRE_ESTACION' (string):\n"
      '{"ID_ESTACION": 113, "NOMBRE_ESTACION": "Av. Carrilet"}'
  )

  for intento in range(max_reintentos):
    print(f"Intento {intento + 1}/{max_reintentos} para obtener ID_ESTACION de '{nombre_estacion}'")
    try:
      client = genai.Client(api_key=api_key)

      out = client.models.generate_content(
          model=GEMINI_MODEL,
          contents=prompt,
          config=types.GenerateContentConfig(
              temperature=AGENT_TEMPERATURE,
              response_mime_type="application/json",  # Fuerza respuesta JSON pura
          ),
      )

      texto_raw = (out.text or "").strip()
      if not texto_raw:
        return {"ERROR": "Respuesta vacía del modelo."}

      # Limpieza de bloque Markdown por si el modelo incluye ```json ... ```
      texto_limpio = re.sub(
          r"^```(?:json)?\s*|\s*```$", "", texto_raw, flags=re.MULTILINE
      ).strip()

      # Parsear el JSON limpiado
      data = json.loads(texto_limpio)

      if isinstance(data, dict):
        return data
      else:
        return {"ERROR": f"El formato devuelto no es un diccionario: {data}"}

    except json.JSONDecodeError as e:
      return {
          "ERROR": (
              f"Error al parsear el JSON de Gemini: {e}. Texto recibido:"
              f" '{texto_raw}'"
          )
      }

    except errors.APIError as e:
      # Reintentar si el servidor está saturado (503) o sobrepasó el límite de cuota (429)
      if e.code in (503, 429) and intento < max_reintentos - 1:
        tiempo_espera = espera_base * (intento + 1)
        print(
            f"Gemini ocupado (Error {e.code}). Reintentando en"
            f" {tiempo_espera}s... (Intento {intento + 1}/{max_reintentos})"
        )
        time.sleep(tiempo_espera)
      else:
        return {
            "ERROR": (
                f"Error de API Gemini tras {intento + 1} intentos:"
                f" [{e.code}] {e.message}"
            )
        }

    except Exception as e:
      return {"ERROR": f"Error no controlado: {e}"}

  return {"ERROR": "No se pudo obtener respuesta de Gemini tras varios intentos."}