from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path
import pandas as pd
from common.config import DATA_DIR, EXTENSIONES_PDF, EXTENSIONES_CSV

def valor_celda(fila, columna: str) -> str | None:
    """Lee una celda de un CSV y devuelve su texto, o None si está vacía."""
    if columna not in fila or pd.isna(fila[columna]):
        return None
    texto = str(fila[columna]).strip()
    return texto if texto else None

def fila_a_texto_municipios(fila) -> str | None:
    """Convierte UNA fila del CSV de municipios en texto legible."""

    lineas = [f"Poblacion: {valor_celda(fila, 'Poblacion')}",
              f"Zona Tarifaria: {valor_celda(fila, 'Zona Tarifaria')}",
              f"Sector: {valor_celda(fila, 'Sector') or 'Sin sector'}",
              f"Tarifa Metropolitana: {valor_celda(fila, 'Tarifa Metropolitana')}"]

    return "\n".join(lineas)


def cargar_csv_municipios(ruta: Path) -> list[Document]:
    """Lee el CSV de eventos: un Document por fila con título válido."""
    df = pd.read_csv(ruta, sep=";", encoding="UTF-8", dtype=str)
    documentos: list[Document] = []

    for _, fila in df.iterrows():
        texto = fila_a_texto_municipios(fila)
        if texto is None:
            continue

        metadata: dict = {
            "source": str(ruta),
            "tipo": "zona_tarifaria",  
            "Poblacion": valor_celda(fila, 'Poblacion'),
            "Zona Tarifaria": valor_celda(fila, 'Zona Tarifaria'),
            "Sector": valor_celda(fila, 'Sector') or 'Sin sector',
            "Tarifa Metropolitana": valor_celda(fila, 'Tarifa Metropolitana')
        }
        documentos.append(Document(page_content=texto, metadata=metadata))

    return documentos

def cargar_csv_municipios_por_zona(ruta: Path) -> list[Document]:
    """Lee el CSV de municipios agrupándolos por Zona Tarifaria y por Tarifa Metropolitana.
    La función original cargar_csv_municipios no funciona adecuadamente porque genera demasiado ruido"""
    df = pd.read_csv(ruta, sep=";", encoding="UTF-8", dtype=str)
    documentos: list[Document] = []

    # RMO: Normalizar sectores vacíos para que no los omita el groupby
    df["Sector"] = df["Sector"].fillna("Sin sector").str.strip()
    df["Sector"] = df["Sector"].replace("", "Sin sector")

    # RMO: Primero creamos un Document por cada Zona Tarifaria (agrupando sectores y poblaciones)
    for zona, df_zona in df.groupby("Zona Tarifaria"):
        lineas = [
            f"Zona Tarifaria: {zona}",
            "Sectores y municipios incluidos:"
        ]
        
        for sector, df_sector in df_zona.groupby("Sector"):
            poblaciones = ", ".join(df_sector["Poblacion"].dropna().tolist())
            lineas.append(f"  - Sector {sector}: {poblaciones}")

        texto = "\n".join(lineas)
        metadata = {
            "source": str(ruta),
            "tipo": "Municipios_por_zona",
            "zona_tarifaria": str(zona)
        }
        documentos.append(Document(page_content=texto, metadata=metadata))

    # RMO: Luego creamos un Document exclusivo para la Tarifa Metropolitana
    df_metro = df[df["Tarifa Metropolitana"].str.upper() == "SI"]
    if not df_metro.empty:
        poblaciones_metro = ", ".join(df_metro["Poblacion"].dropna().tolist())
        texto_metro = (
            "Tarifa Metropolitana: Municipios donde se aplican títulos de 1 sola zona para viajes metropolitanos:\n"
            f"{poblaciones_metro}"
        )
        metadata_metro = {
            "source": str(ruta),
            "tipo": "Tarifa_Metropolitana"
        }
        documentos.append(Document(page_content=texto_metro, metadata=metadata_metro))

    return documentos

#def cargar_csv_municipios_completo(ruta: Path) -> list[Document]:
#    """Carga todo el CSV de municipios como un único Documento estructurado."""
#    df = pd.read_csv(ruta, sep=";", encoding="UTF-8", dtype=str)
#    
#    # Cabecera descriptiva para reforzar la semántica en el vector embedding
#    lineas = [
#        "Tabla completa de municipios, zonas tarifarias, sectores y tarifa metropolitana de la ATM de Barcelona.",
#        "Listado oficial para consultar a qué zona tarifaria (1 a 7) pertenece cada población de Cataluña:\n"
#    ]
#    
#    for _, fila in df.iterrows():
#        poblacion = str(fila.get("Poblacion", "")).strip()
#        zona = str(fila.get("Zona Tarifaria", "")).strip()
#        sector = str(fila.get("Sector", "")).strip()
#        metro = str(fila.get("Tarifa Metropolitana", "")).strip()
#        
#        sector_str = sector if sector and sector.upper() != "NAN" else "Sin sector"
#        lineas.append(f"Población: {poblacion} | Zona: {zona} | Sector: {sector_str} | Tarifa Metropolitana: {metro}")
#
#    texto_completo = "\n".join(lineas)
#    
#    metadata = {
#        "source": ruta.name,
#        "tipo": "Tabla_Completa_Municipios"
#    }
#    
#    return [Document(page_content=texto_completo, metadata=metadata)]


def cargar_csv_tarifas(ruta: Path) -> list[Document]:
    """Lee el CSV de eventos: un Document por fila con título válido."""
    df = pd.read_csv(ruta, sep=";", encoding="UTF-8", dtype=str)
    documentos: list[Document] = []

    for _, fila in df.iterrows():
        texto = fila_a_texto_tarifas(fila)
        if texto is None:
            continue

        metadata: dict = {
            "source": str(ruta),
            "tipo": "Tarifas_por_zona",  
            "Denominación de tarifa": valor_celda(fila, 'Titulo'),
            "Importe zona 1": valor_celda(fila, '1 zona'),
            "Importe zona 2": valor_celda(fila, '2 zonas'),
            "Importe zona 3": valor_celda(fila, '3 zonas'),
            "Importe zona 4": valor_celda(fila, '4 zonas'),
            "Importe zona 5": valor_celda(fila, '5 zonas'),
            "Importe zona 6": valor_celda(fila, '6 zonas'),
            "Importe zona 7": valor_celda(fila, '7 zonas')
        }
        documentos.append(Document(page_content=texto, metadata=metadata))

    return documentos


def fila_a_texto_tarifas(fila) -> str | None:
    """Convierte UNA fila del CSV de tarifas en texto legible."""

    lineas = [f"Denominación de tarifa: {valor_celda(fila, 'Titulo')}",
              f"Importe zona 1: {valor_celda(fila, '1 zona')}",
              f"Importe zona 2: {valor_celda(fila, '2 zonas')}",
              f"Importe zona 3: {valor_celda(fila, '3 zonas')}",
              f"Importe zona 4: {valor_celda(fila, '4 zonas')}",
              f"Importe zona 5: {valor_celda(fila, '5 zonas')}",
              f"Importe zona 6: {valor_celda(fila, '6 zonas')}",
              f"Importe zona 7: {valor_celda(fila, '7 zonas')}"
              ]

    return "\n".join(lineas)



def cargar_archivo(ruta: Path) -> list[Document]:
    """Elige el loader según la extensión del archivo."""
    sufijo = ruta.suffix.lower()

    print(f"La ruta del archivo a cargar es: {ruta}")

    if sufijo in EXTENSIONES_PDF:
        return PyPDFLoader(str(ruta)).load()

    if sufijo in EXTENSIONES_CSV:
        if (ruta.name == "01_Municipios_por_zona_y_tarifa_metropolitana.csv"):
            #return cargar_csv_municipios_por_zona(ruta)
            #return cargar_csv_municipios(ruta)
            # RMO: Finalmente no cargamos este CSV porque se maneja de manera especial en el prompt.
            # El motivo es que genera mucho ruido lo trates como lo trate y hace que la información relevante se diluya.
            print(f"[omitido] CSV especial: {ruta.name}")
        elif (ruta.name == "22_tarifas_transporte_abonos_normales.csv"):
            return cargar_csv_tarifas(ruta)
        else:
            print(f"Archivo CSV no reconocido: {ruta.name}")
        
    return []

def cargar_documentos() -> list[Document]:
    """Recorre data/ y concatena todos los Document soportados."""
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"No existe la carpeta de datos: {DATA_DIR}")

    documentos: list[Document] = []

    for ruta in sorted(DATA_DIR.rglob("*")):
        if not ruta.is_file():
            continue

        docs = cargar_archivo(ruta)
        if docs:
            print(f"  Cargado: {ruta.name} ({len(docs)} documento(s))")
            documentos.extend(docs)
        elif ruta.suffix:
            print(f"  [omitido] extensión/fichero no soportada: {ruta.name}")

    return documentos
