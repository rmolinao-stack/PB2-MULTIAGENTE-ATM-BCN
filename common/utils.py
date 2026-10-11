from pathlib import Path
import re
import pandas as pd

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