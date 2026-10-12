"""Tool multimodal: calcula la ruta ferroviaría entre dos estaciones de la red ATM a partir de la imagen con la 'Red Ferroviaria Integrada'."""

import os

from google import genai
from google.genai import types

from pathlib import Path

from langchain_core.tools import tool

from common.config import PLANO_ATM_PATH, GEMINI_MODEL, AGENT_TEMPERATURE

@tool
def calcular_ruta_plano(estacion1: str, estacion2: str) -> str:
    """Calcula la ruta ferroviaria entre dos estaciones de la red ATM a partir de la imagen del plano con la 'Red Ferroviaria Integrada'."""
    #Llamar a esta tool cuando el usuario quiera conocer la ruta o recorrido entre dos estaciones de la red ATM.
    #"""
    path = PLANO_ATM_PATH
    if not path.exists():
        return f"Error: no hay imagen en {path}"

    try:
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return "Error: falta GEMINI_API_KEY"

        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        client = genai.Client(api_key=api_key)
        out = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=path.read_bytes(), mime_type=mime),
                        types.Part.from_text(
                            text=(
                                f"Describe la ruta ferroviaria entre las estaciones {estacion1} y {estacion2} en 2-3 frases en español. "
                                "Si hay detalles sobre transbordos, líneas o cambios entre tipo de transporte (Metro, FGC, Rodalies, TRAM, Bus), menciónalos."
                            )
                        ),
                    ],
                )
            ],
            config=types.GenerateContentConfig(
        temperature=AGENT_TEMPERATURE  
    )
        )
        return (out.text or "").strip() or "Error: respuesta vacía del modelo."
    except Exception as e: 
        return f"Error al leer el plano: {e}"