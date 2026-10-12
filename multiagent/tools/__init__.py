"""Allowlist de tools LangChain (@tool).

Solo las tools de esta lista se pueden ejecutar.
Si el modelo pide otra, ejecutar_tool la bloquea.
"""

from multiagent.tools.hora_actual import obtener_hora_actual
from multiagent.tools.api_tiempos_tmb import API_llegada_tren_estacion_tmb
from multiagent.tools.info_estacion import obtener_id_estacion, obtener_nombre_estacion_oficial
from multiagent.tools.rag_tarifas import rag_ask_tarifas
from multiagent.tools.ruta_plano import calcular_ruta_plano
from multiagent.tools.zonas import zonas_poblacion_text

TOOLS = [
    rag_ask_tarifas,
    zonas_poblacion_text,
    API_llegada_tren_estacion_tmb,
    calcular_ruta_plano,
    obtener_nombre_estacion_oficial,
    obtener_id_estacion,
    obtener_hora_actual,
]

TOOL_BY_NAME = {t.name: t for t in TOOLS}


def ejecutar_tool(nombre: str, args: dict | None = None) -> str:
    """Ejecuta una tool de la allowlist; si no está, bloquea."""
    args = args or {}
    tool = TOOL_BY_NAME.get(nombre)
    print(f"Ejecutando tool: {nombre} con args: {args}")
    if tool is None:
        return f"Error: tool '{nombre}' no está permitida."
    try:
        return str(tool.invoke(args))
    except Exception as e:  # noqa: BLE001
        return f"Error: {e}"