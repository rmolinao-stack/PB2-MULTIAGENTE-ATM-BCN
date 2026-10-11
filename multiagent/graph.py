"""Grafo multiagente: supervisor ↔ especialistas + HITL.

Flujo:
START → supervisor  ──┬── tarifas ──────────┐
                      ├── zonas ────────────┼──► supervisor → …
                      ├── recorridos ───────┤
                      ├── tiempos ──────────┤
                      └── sintetizar ───────┘
                              │
                     FINISH → aplicar (interrupt_before) → END
"""
import re
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from common.config import MAX_STEPS_DEFAULT, MAX_ITER
from multiagent.llm import get_llm

def _acumular(actual: list, nuevo: list) -> list:
    """Reducer de LangGraph: concatena listas (no pisa el valor anterior)."""
    return (actual or []) + (nuevo or [])

class EstadoGrafo(TypedDict):
    pedido: str  # mensaje del usuario
    notas_tarifas: str  # las escribe el especialista tarifas
    notas_zonas: str  # las escribe el especialista zonas
    notas_tiempos: str  # las escribe el especialista de tiempos de espera de metro de TMB
    notas_recorridos: str  # las escribe el especialista recorridos que usará plano_ATM.jpg (equivalente a notas_vision)
    respuesta: str  # texto del plan (sintetizar / aplicar)
    plan: list  # viñetas del plan (≥2 para HITL)
    siguiente: str  # lo elige el supervisor: tarifas|zonas|tiempos|recorridos|sintetizar|FINISH
    iteracion: int  # contador del supervisor (tope MAX_ITER)
    log: Annotated[list, _acumular]  # traza legible del orquestador
    traza_tools: Annotated[list, _acumular]  # tools usadas en los especialistas
    max_steps: int  # tope modelo↔tools dentro de un especialista
    plan_aprobado: bool  # lo escribe el humano vía update_state (HITL)
    done: bool  # True solo tras aprobar en aplicar
    pendiente_hitl: bool  # True mientras el grafo está pausado antes de aplicar


OPCIONES = ("tarifas", "zonas", "tiempos", "recorridos", "sintetizar", "FINISH")

def _texto_llm(content: Any) -> str:
    """Normaliza ai.content (str o lista de bloques Gemini) a texto plano."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        partes: list[str] = []
        for bloque in content:
            if isinstance(bloque, str):
                partes.append(bloque)
            elif isinstance(bloque, dict):
                t = bloque.get("text") or bloque.get("content") or ""
                if t:
                    partes.append(str(t))
            else:
                t = getattr(bloque, "text", None)
                if t:
                    partes.append(str(t))
        return "\n".join(p.strip() for p in partes if p and str(p).strip()).strip()
    return str(content).strip()

def _parse_plan(texto: str) -> list[str]:
    items: list[str] = []
    for line in (texto or "").splitlines():
        s = line.strip()
        if s.startswith(("-", "•", "*")):
            items.append(s.lstrip("-•* ").strip())
    return [i for i in items if i]

def _fallback_siguiente(estado: EstadoGrafo) -> str:
    """Si el LLM falla o responde mal: reglas deterministas en Python."""
    if not (estado.get("notas_tarifas") or "").strip():
        return "tarifas"
    if not (estado.get("notas_zonas") or "").strip():
        return "zonas"
    if not (estado.get("notas_tiempos") or "").strip():
        return "tiempos"
    if not (estado.get("notas_recorridos") or "").strip():
        return "recorridos"
    if not (estado.get("respuesta") or "").strip():
        return "sintetizar"
    return "FINISH"

def nodo_supervisor(estado: EstadoGrafo) -> dict:
    """Orquesta: no escribe el plan; solo elige el siguiente nodo (o FINISH).

    MAX_ITER evita bucles infinitos supervisor ↔ especialistas.
    """
    it = int(estado.get("iteracion") or 0) + 1
    if it >= MAX_ITER:
        return {
            "iteracion": it,
            "siguiente": "FINISH",
            "log": [f"iter {it}: supervisor → FINISH (MAX_ITER)"],
        }

    llm = get_llm(temperature=0)
    prompt = (
        "Eres el supervisor de un planificador de rutas, tarifas y zonas de la red ATM y tiempos de llegada de trenes a las estaciones de Metro (TMB).\n"
        "Elige el siguiente rol:\n"
        "- tarifas: tarifas, abonos y condiciones de uso para la red ATM de Barcelona.\n"
        "- zonas: zona de la red ATM a la que pertenece una población.\n"
        "- recorridos: rutas y recorridos dentro de la red ferrovial integrada en ATM (Rodalies, FGC, Metro y TRAM, excluyendo autobuses).\n"
        "- tiempos: calcula el tiempo en llegar el próximo metro de TMB a una parada concreta.\n"
        "- sintetizar: une notas en un plan final con viñetas\n"
        "- FINISH: ya hay plan/respuesta lista\n"
        "Responde SOLO una palabra: tarifas, zonas, recorridos, tiempos, sintetizar o FINISH.\n"
        "Regla: sin notas_tarifas → tarifas; sin notas_zonas → zonas; sin notas_recorridos → recorridos; sin notas_tiempos → tiempos; "
        "con todas y sin respuesta → sintetizar; con respuesta → FINISH.\n\n"
        f"pedido: {estado.get('pedido')}\n"
        #f"notas_tarifas: {(estado.get('notas_tarifas') or '')[:400]}\n"
        #f"notas_zonas: {(estado.get('notas_zonas') or '')[:400]}\n"
        #f"notas_recorridos: {(estado.get('notas_recorridos') or '')[:400]}\n"
        #f"notas_tiempos: {(estado.get('notas_tiempos') or '')[:200]}\n"
        #f"respuesta: {(estado.get('respuesta') or '')[:200]}\n"
        f"notas_tarifas: {(estado.get('notas_tarifas') or '')}\n"
        f"notas_zonas: {(estado.get('notas_zonas') or '')}\n"
        f"notas_recorridos: {(estado.get('notas_recorridos') or '')}\n"
        f"notas_tiempos: {(estado.get('notas_tiempos') or '')}\n"
        f"respuesta: {(estado.get('respuesta') or '')}\n"
    )
    print(prompt)
    siguiente = _fallback_siguiente("FINISH")
    try:
        out = llm.invoke([HumanMessage(content=prompt)])
        raw = _texto_llm(out.content)
        palabra = re.findall(r"[A-Za-z_]+", raw)
        siguiente = (palabra[0] if palabra else "").strip()
        if siguiente not in OPCIONES:
            siguiente = _fallback_siguiente(estado)
    except Exception:
        siguiente = _fallback_siguiente(estado)

    return {
        "iteracion": it,
        "siguiente": siguiente,
        "log": [f"iter {it}: supervisor → {siguiente}"],
    }

# RMO: PENDIENTE REVISAR
def nodo_tarifas(estado: EstadoGrafo) -> dict:
    """Genera notas sobre tarifas según el pedido."""
    print("="*10+" ¡¡¡¡¡¡ PENDIENTE REVISAR !!!!!!!!!!!! "+"="*10)
    llm = get_llm()
    prompt = (
        "Genera notas sobre tarifas según el pedido.\n\n"
        f"Pedido: {estado.get('pedido')}\n"
        f"Notas previas: {estado.get('notas_tarifas') or '(nada)'}\n"
    )
    out = llm.invoke([HumanMessage(content=prompt)])
    texto = _texto_llm(out.content)
    return {
        "notas_tarifas": texto,
        "log": ["tarifas: notas generadas"],
    }

# RMO: PENDIENTE REVISAR
def nodo_zonas(estado: EstadoGrafo) -> dict:
    """Genera notas sobre zonas según el pedido."""
    print("="*10+" ¡¡¡¡¡¡ PENDIENTE REVISAR !!!!!!!!!!!! "+"="*10)
    llm = get_llm()
    prompt = (
        "Genera notas sobre zonas según el pedido.\n\n"
        f"Pedido: {estado.get('pedido')}\n"
        f"Notas previas: {estado.get('notas_zonas') or '(nada)'}\n"
    )
    out = llm.invoke([HumanMessage(content=prompt)])
    texto = _texto_llm(out.content)
    return {
        "notas_zonas": texto,
        "log": ["zonas: notas generadas"],
    }

# RMO: PENDIENTE REVISAR
def nodo_recorridos(estado: EstadoGrafo) -> dict:
    """Genera notas sobre recorridos según el pedido."""
    print("="*10+" ¡¡¡¡¡¡ PENDIENTE REVISAR !!!!!!!!!!!! "+"="*10)
    llm = get_llm()
    prompt = (
        "Genera notas sobre recorridos según el pedido.\n\n"
        f"Pedido: {estado.get('pedido')}\n"
        f"Notas previas: {estado.get('notas_recorridos') or '(nada)'}\n"
    )
    out = llm.invoke([HumanMessage(content=prompt)])
    texto = _texto_llm(out.content)
    return {
        "notas_recorridos": texto,
        "log": ["recorridos: notas generadas"],
    }

# RMO: PENDIENTE REVISAR
def nodo_tiempos(estado: EstadoGrafo) -> dict:
    """Genera notas sobre tiempos según el pedido."""
    print("="*10+" ¡¡¡¡¡¡ PENDIENTE REVISAR !!!!!!!!!!!! "+"="*10)
    llm = get_llm()
    prompt = (
        "Genera notas sobre tiempos según el pedido.\n\n"
        f"Pedido: {estado.get('pedido')}\n"
        f"Notas previas: {estado.get('notas_tiempos') or '(nada)'}\n"
    )
    out = llm.invoke([HumanMessage(content=prompt)])
    texto = _texto_llm(out.content)
    return {
        "notas_tiempos": texto,
        "log": ["tiempos: notas generadas"],
    }

def nodo_sintetizar(estado: EstadoGrafo) -> dict:
    """Une las notas en respuesta + plan (viñetas). Deja el flujo listo para HITL."""
    llm = get_llm()
    prompt = (
        "Une las notas en un plan de rutas, tarifas y zonas de la red ATM y tiempos de llegada de trenes a las estaciones de Metro (TMB).\n"
        "Incluye al menos 2 opciones como viñetas que empiecen por '- '.\n"
        "Una intro de 1-2 frases y luego las viñetas.\n\n"
        f"Pedido: {estado.get('pedido')}\n"
        f"Tarifas: {estado.get('notas_tarifas') or '(nada)'}\n"
        f"Zonas: {estado.get('notas_zonas') or '(nada)'}\n"
        f"Recorridos: {estado.get('notas_recorridos') or '(nada)'}\n"
        f"Tiempos: {estado.get('notas_tiempos') or '(nada)'}\n"
    )
    out = llm.invoke([HumanMessage(content=prompt)])
    texto = _texto_llm(out.content)
    plan = _parse_plan(texto)
    if len(plan) < 2:
        # Fallback mínimo para poder pausar en HITL con algo que mostrar
        plan = [
            p
            for p in (
                (estado.get("notas_tarifas") or "").split(".")[0].strip(),
                (estado.get("notas_zonas") or "").split(".")[0].strip(),
                (estado.get("notas_recorridos") or "").split(".")[0].strip(),
                (estado.get("notas_tiempos") or "").split(".")[0].strip(),
            )
            if p
        ]
        if len(plan) < 2:
            plan = ["Plan ruta, tarifa, zonas o tiempo según preferencias", "Cierre"]
        texto = texto or "Plan propuesto:\n" + "\n".join(f"- {p}" for p in plan)
    return {
        "respuesta": texto,
        "plan": plan,
        "pendiente_hitl": True,
        "log": ["sintetizar: plan listo (pendiente HITL)"],
    }

def nodo_aplicar(estado: EstadoGrafo) -> dict:
    """Cierra o resetea según plan_aprobado.

    Solo se ejecuta DESPUÉS de la decisión humana: el grafo pausa con
    interrupt_before; el cliente hace update_state + invoke(None).
    """
    if estado.get("plan_aprobado"):
        prev = (estado.get("respuesta") or "").strip()
        cierre = "Plan aprobado. ¡Listo!"
        return {
            "done": True,
            "pendiente_hitl": False,
            "respuesta": f"{prev}\n\n{cierre}".strip() if prev else cierre,
            "log": ["aplicar: plan aprobado"],
        }
    return {
        "done": False,
        "pendiente_hitl": False,
        "plan_aprobado": False,
        "plan": [],
        "respuesta": (
            "Plan rechazado. Dime qué cambiar (ruta, tarifa, zona, estación) "
            "y proponemos otro."
        ),
        "notas_tarifas": "",
        "notas_zonas": "",
        "notas_recorridos": "",
        "notas_tiempos": "",
        "log": ["aplicar: plan rechazado"],
    }


def _router_supervisor(
    estado: EstadoGrafo,
) -> Literal["tarifas", "zonas", "recorridos", "tiempos", "sintetizar", "aplicar"]:
    """Lee estado['siguiente'] y elige el edge.

    FINISH → nodo aplicar (donde está el interrupt HITL).
    Si aún no hay plan/respuesta → sintetizar antes de pausar.
    """
    sig = (estado.get("siguiente") or "").strip()
    if sig == "FINISH":
        if not (estado.get("plan") or estado.get("respuesta")):
            return "sintetizar"
        return "aplicar"
    if sig in ("tarifas", "zonas", "recorridos", "tiempos", "sintetizar"):
        return sig  # type: ignore[return-value]
    return "sintetizar"

def build_graph():
    """Monta el grafo: especialistas vuelven al supervisor; HITL ante aplicar."""

    grafo = StateGraph(EstadoGrafo)
    grafo.add_node("supervisor", nodo_supervisor)
    grafo.add_node("tarifas", nodo_tarifas)
    grafo.add_node("zonas", nodo_zonas)
    grafo.add_node("tiempos", nodo_tiempos)
    grafo.add_node("recorridos", nodo_recorridos)
    grafo.add_node("sintetizar", nodo_sintetizar)
    grafo.add_node("aplicar", nodo_aplicar)

    grafo.add_edge(START, "supervisor")
    grafo.add_conditional_edges(
        "supervisor",
        _router_supervisor,
        {
            "tarifas": "tarifas",
            "zonas": "zonas",
            "tiempos": "tiempos",
            "recorridos": "recorridos",
            "sintetizar": "sintetizar",
            "aplicar": "aplicar",
        },
    )
    # Tras cada especialista, el control vuelve al supervisor
    grafo.add_edge("tarifas", "supervisor")
    grafo.add_edge("zonas", "supervisor")    
    grafo.add_edge("tiempos", "supervisor")
    grafo.add_edge("recorridos", "supervisor")
    grafo.add_edge("sintetizar", "supervisor")
    grafo.add_edge("aplicar", END)

    return grafo.compile(
        checkpointer=MemorySaver(),  # checkpoints por thread_id
        interrupt_before=["aplicar"],  # pausa HITL antes de este nodo
    )

   

_APP = None

def get_app():
    global _APP
    if _APP is None:
        _APP = build_graph()
    return _APP

def config_hilo(thread_id: str) -> dict:
    """Config de LangGraph: identifica el hilo del checkpointer."""
    return {"configurable": {"thread_id": thread_id}}

def estado_inicial_grafo(pedido: str, max_steps: int | None = None) -> EstadoGrafo:
    return {
        "pedido": pedido,
        "notas_tarifas": "",
        "notas_zonas": "",
        "notas_tiempos": "",
        "notas_recorridos": "",
        "respuesta": "",
        "plan": [],
        "siguiente": "",
        "iteracion": 0,
        "log": [],
        "traza_tools": [],
        "max_steps": max_steps if max_steps is not None else MAX_STEPS_DEFAULT,
        "plan_aprobado": False,
        "done": False,
        "pendiente_hitl": False,
    }

def hay_interrupt(thread_id: str) -> bool:
    """True si el hilo está pausado antes de aplicar (HITL pendiente).

    get_state(...).next incluye el nombre del siguiente nodo bloqueado.
    """
    snap = get_app().get_state(config_hilo(thread_id))
    nxt = snap.next or ()
    return "aplicar" in nxt
