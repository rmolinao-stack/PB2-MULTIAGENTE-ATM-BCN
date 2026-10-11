from services.rag_service import rag_ask
from langchain_core.tools import tool

@tool
def rag_ask_tarifas(consulta: str) -> str:
    return rag_ask(consulta)