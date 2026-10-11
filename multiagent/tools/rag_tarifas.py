from services.rag_service import rag_ask
from langchain_core.tools import tool

@tool
def rag_ask_tarifas(consulta: str) -> str:
    """Consulta sobre tarifas y condiciones de uso de la red ATM usando RAG."""
    return rag_ask(consulta)