"""Construcción del prompt RAG .
"""

INSTRUCCIONES_RAG = """Eres un asistente que responde preguntas sobre tarifas y abonos para la red ATM de Barcelona 
que es el sistema tarifario integrado que permite utilizar diferentes medios de transporte (metro, autobuses, Ferrocarrils y Rodalies). 

Reglas:
- Responde ÚNICAMENTE con la información del contexto proporcionado.
- Si el contexto no contiene información suficiente, indícalo explícitamente.
- Cuando cites un hecho, menciona la fuente si aparece en el contexto o en la información geográfica extraída del CSV.
- No inventes eventos, fechas ni datos que no estén en el contexto.
- No eres un asistente de rutas, solo de tarifas y abonos de la red ATM de Barcelona.
"""
#- UNICAMENTE si te preguntan sobre la como ir de una población a otra y por qué zonas pasa debes redirigir  
#a la web de cálculo de zonas: https://www.atm.cat/es/titols-tarifes/sistema-de-transport/mapa-de-la-zonificacio

import re
import pandas as pd
from pathlib import Path

from common.config import DATA_DIR
from common.utils import _normalizar_texto


def extraer_info_municipios_normalizado(pregunta: str, ruta_csv: Path) -> str:
    """
    Busca municipios en la consulta con tolerancia a omission de artículos 
    (ej: 'Masnou' -> 'El Masnou') y coincidencias por nombre base (ej: 'Sant Cugat' -> 'Sant Cugat del Vallès').
    """
    df = pd.read_csv(ruta_csv, sep=";", encoding="UTF-8", dtype=str)
    df["Poblacion"] = df["Poblacion"].str.strip()
    
    pregunta_norm = _normalizar_texto(pregunta)
    pregunta_orig = pregunta.lower()
    
    encontrados = []
    
    for _, fila in df.iterrows():
        pob_real = fila.get("Poblacion", "").strip()
        if not pob_real:
            continue
            
        pob_norm = _normalizar_texto(pob_real)
        pob_orig = pob_real.lower()
        
        # RMO: Coincidencia directa exacta (con o sin artículos)
        patron_norm = r'\b' + re.escape(pob_norm) + r'\b'
        patron_orig = r'\b' + re.escape(pob_orig) + r'\b'
        
        coincide = False
        if re.search(patron_norm, pregunta_norm) or re.search(patron_orig, pregunta_orig):
            coincide = True
        else:
            # RMO: Coincidencia por nombre base (separa calificativos como 'de', 'del', 'de la', 'd'')
            partes_base = re.split(r'\s+(de\s+la|de\s+les|de\s+los|del|de|d\'|d’)\s+', pob_norm)
            nombre_base = partes_base[0].strip()
            
            # RMO: Evita falsos positivos con raíces demasiado cortas (longitud > 3)
            if len(nombre_base) > 3:
                patron_base = r'\b' + re.escape(nombre_base) + r'\b'
                if re.search(patron_base, pregunta_norm):
                    coincide = True
        
        if coincide:
            zona = fila.get("Zona Tarifaria", "N/A")
            sector = fila.get("Sector", "Sin sector")
            if pd.isna(sector) or str(sector).strip() == "":
                sector = "Sin sector"
            metro = fila.get("Tarifa Metropolitana", "NO")
            
            encontrados.append(
                f"- {pob_real}: Zona {zona}, Sector {sector}, Tarifa Metropolitana: {metro}"
            )

    if not encontrados:
        return "No se han detectado municipios específicos en la consulta."

    return f"Información geográfica determinista (extraída del {ruta_csv.name}):\n" + "\n".join(encontrados)


def build_rag_prompt(contexto: str, pregunta: str) -> str:
    """Ensambla el prompt completo para el LLM."""
    return (
        f"{INSTRUCCIONES_RAG}\n\n"
        f"{extraer_info_municipios_normalizado(pregunta, Path(f"{DATA_DIR}/01_Municipios_por_zona_y_tarifa_metropolitana.csv"))}\n\n"
        f"--- CONTEXTO RECUPERADO ---\n"
        f"{contexto.strip()}\n\n"
        f"--- PREGUNTA ---\n"
        f"{pregunta.strip()}\n\n"
        f"--- RESPUESTA ---"
    )
