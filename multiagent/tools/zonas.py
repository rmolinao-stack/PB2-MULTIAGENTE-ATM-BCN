
from langchain_core.tools import tool
from common.utils import extraer_info_municipios_normalizado
from pathlib import Path
from common.config import DATA_DIR

@tool
def zonas_poblacion_text(texto: str) -> str:
    """Busca en el texto si hay poblaciones que pertenecen a la red de ATM. Para cada población encontrada, devuelve un texto
    donde se indica por población encontrada, la zona a la que pertenece, el sector y si aplica la tarifa metropolitana."""
    return extraer_info_municipios_normalizado(texto, Path(f"{DATA_DIR}/01_Municipios_por_zona_y_tarifa_metropolitana.csv"))