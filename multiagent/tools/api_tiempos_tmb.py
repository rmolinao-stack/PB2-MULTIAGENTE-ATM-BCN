"""Tool: API para consultar el tiempo que tardará un tren en llegar a la estación en tiempo real — HTTP + fallback local.

Ejemplo de JSON que devuelve la API:

{
"timestamp": 1746449254397, // timestamp de la consulta
"linies": [		// Per cada linia...
  {
    //Atributs de la linia
    "codi_linia": 1,
    "nom_linia": "L1",
    "nom_familia": "Metro",
    "codi_familia": 1,
    "color_linia": "CE1126",
    "estacions": [  // per cada estació per la que passa la linia
      {
        "codi_via": 1,		// Via 1 o 2
        "id_sentit": 1,		// 1 = Anada, 2 = Tornada
        "codi_estacio": 120,
        "linies_trajectes": [	// per cada trajecte que pot tenir la línia, en el cas de metro normalment 1 per sentit
          {
            "codi_linia": 1,
            "nom_linia": "L1",
            "color_linia": "CE1126",
            "codi_trajecte": "0011",
            "desti_trajecte": "Fondo", // Destinació del trajecte
            "propers_trens": [			// llista dels propers trens que arribaran a la estació
              {
                "codi_servei": "120",				// codi del servei que té assignat el tren (es veu al frontal del tren)
                "temps_arribada": 1746449431000 	// timestamp absolut del moment d'arribada a la estació
              },
              {
                "codi_servei": "121",
                "temps_arribada": 1746449707000
              }
            ]
          }
        ]
      },
    ]
  }
]}
"""

import json
import os

from dotenv import load_dotenv
import requests
from langchain_core.tools import tool

from common.config import TMB_METRO_ESTACIONS_URL, HTTP_TIMEOUT_SECONDS

def _procesar_tiempos_llegada(datos_json: dict | str) -> str:
  """Procesa el JSON de respuesta de TMB y calcula el tiempo restante

  para la llegada del próximo tren por línea y dirección.
  """
  # Si se pasa como string JSON, se parsea a diccionario
  if isinstance(datos_json, str):
    datos = json.loads(datos_json)
  else:
    datos = datos_json

  timestamp_base = datos.get("timestamp", 0)
  lineas_resultado = []

  for linia in datos.get("linies", []):
    nom_linia_padre = linia.get("nom_linia")

    for estacio in linia.get("estacions", []):
      for trajecte in estacio.get("linies_trajectes", []):
        # Filtrar solo aquellos trajectes que coincidan con el nom_linia de la línea principal
        if trajecte.get("nom_linia") == nom_linia_padre:
          desti = trajecte.get("desti_trajecte")
          propers_trens = trajecte.get("propers_trens", [])

          if not propers_trens:
            continue

          # Obtener el tren con el menor temps_arribada
          siguiente_tren = min(
              propers_trens, key=lambda t: t.get("temps_arribada", float("inf"))
          )
          temps_arribada = siguiente_tren.get("temps_arribada", 0)

          # Calcular la diferencia de tiempo en segundos
          diferencia_ms = temps_arribada - timestamp_base
          diferencia_segundos = max(0, int(diferencia_ms / 1000))

          minutos = diferencia_segundos // 60
          segundos = diferencia_segundos % 60

          # Formatear la cadena de tiempo según la duración
          if minutos > 0:
            tiempo_str = f"{minutos:02d}:{segundos:02d} minutos"
          else:
            tiempo_str = f"{segundos} segundos"

          lineas_resultado.append(
              f"- Línea {nom_linia_padre}, dirección {desti} el siguiente tren"
              f" llegará en {tiempo_str}."
          )

  return "\n".join(lineas_resultado)

@tool
def API_llegada_tren_estacion_tmb(id_estacion: int, forzar_fallback: bool = False) -> str:
    """ Dada una estación de metro por su ID (obtener ID_ESTACION con la tool correspondiente), 
    obtiene los próximos trenes que llegarán a dicha estación.
    
    Por cada línea y dirección, se indica el tiempo estimado de llegada del siguiente tren en minutos o segundos
    
    En caso de error devuelve un fallback con información general sobre la frecuencia de los trenes."""

    load_dotenv()
    tmb_app_id = os.getenv("TMB_API_ID")
    tmb_app_key = os.getenv("TMB_API_KEY")

    url = f"{TMB_METRO_ESTACIONS_URL}{id_estacion}&app_id={tmb_app_id}&app_key={tmb_app_key}"
    resultado = "No se pudo obtener la información de llegada de trenes."

    try:
        if forzar_fallback:
            raise Exception("Forzando fallback")
        resp = requests.get(
            url,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        #print(f"RESPUESTA: {json.dumps(resp.json(), indent=4, ensure_ascii=False)}")
        resp.raise_for_status()
        items = resp.json()
        resultado = _procesar_tiempos_llegada(items)
        #fuente = "api"
    except Exception:
        #fuente = "fallback"
        resultado = """
        No se pudo obtener la información de llegada de trenes.
        La frecuencia de paso de los trenes es aproximadamente cada 2-4 minutos en horario diurno y
        cada 10 minutos en horario nocturno.
        """
    if not resultado:
        resultado = "No hay información disponible sobre la llegada de trenes a la estación especificada."
    return resultado
