"""Allowlist de tools LangChain (@tool).

Solo las tools de esta lista se pueden ejecutar.
Si el modelo pide otra, ejecutar_tool la bloquea.
"""

from multiagent.tools.rag_tarifas import rag_ask_tarifas
from multiagent.tools.zonas import zonas_poblacion_text

TOOLS = [
    rag_ask_tarifas,
    zonas_poblacion_text,
]

TOOL_BY_NAME = {t.name: t for t in TOOLS}


def ejecutar_tool(nombre: str, args: dict | None = None) -> str:
    """Ejecuta una tool de la allowlist; si no está, bloquea."""
    args = args or {}
    tool = TOOL_BY_NAME.get(nombre)
    print("="*10 + " EJECUTANDO TOOL " + "="*10)
    print(f"Ejecutando tool: {nombre} con args: {args}")
    print("="*10 + " END EJECUTANDO TOOL " + "="*10)
    if tool is None:
        return f"Error: tool '{nombre}' no está permitida."
    try:
        return str(tool.invoke(args))
    except Exception as e:  # noqa: BLE001
        return f"Error: {e}"