"""Grafo multiagente: supervisor ↔ especialistas + HITL.

Flujo:
START -> supervisor ──┬── tarifas ──────────┐
          ▲  ▲        ├── zonas ────────────┼──► supervisor -> sintetizar -> supervisor -> FINISH -> HITL -> aplicar -> END
          │  │        ├── recorridos ───────┤        │                                                          │
          │  │        └── tiempos   ────────┘        │                                                     (RECHAZO HITL)
          │  │                                       │                                                          │    
          │  └───────────────────────────────────────┘                                                          │
          └─────────────────────────────────────────────────────────────────────────────────────────────────────┘
"""
import re
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from common.config import MAX_STEPS_DEFAULT, MAX_ITER
from multiagent.llm import get_llm

from multiagent.tools import TOOLS, ejecutar_tool

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

def _preview(texto: str, n: int = 120) -> str:
    t = (texto or "").replace("\n", " ").strip()
    return t if len(t) <= n else t[: n - 1] + "…"

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


def _ejecutar_con_tools(
    system: str,
    user: str,
    max_steps: int,
) -> tuple[str, list[dict[str, Any]]]:
    """Mini-bucle agent↔tools dentro de un especialista.

    El LLM puede pedir tools; Python las ejecuta (allowlist).
    Se repite hasta que haya texto final o se agote max_steps.
    """
    #tools_nodo = tools if tools is not None else TOOLS
    llm = get_llm().bind_tools(TOOLS)
    messages: list = [SystemMessage(content=system), HumanMessage(content=user)]
    traza: list[dict[str, Any]] = []
    texto = ""

    for paso in range(1, max(1, max_steps) + 1):
        ai: AIMessage = llm.invoke(messages)
        messages.append(ai)
        calls = getattr(ai, "tool_calls", None) or []
        if not calls:
            # Sin tool_calls → el modelo ya respondió en texto
            texto = _texto_llm(ai.content)
            break
        for call in calls:
            nombre = call.get("name") or ""
            args = dict(call.get("args") or {})
            resultado = ejecutar_tool(nombre, args)
            status = "blocked" if "no está permitida" in resultado else (
                "error" if resultado.startswith("Error") else "ok"
            )
            traza.append(
                {
                    "step": paso,
                    "tool": nombre,
                    "args": args,
                    "status": status,
                    "preview": _preview(resultado),
                }
            )
            messages.append(
                ToolMessage(content=resultado, tool_call_id=call.get("id") or nombre)
            )
    else:
        texto = texto or "He parado por max_steps en el especialista."

    #print("Resultado del especialista:", texto)
    #print("Traza del especialista:", traza)

    return texto, traza

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

    # RMO: Si ya hay respuesta y plan generado por sintetizar, pasamos directamente a FINISH.
    # Lo hacemos manualmente porque parece que al LLM le cuesta reconocer que ya hay un plan listo.
    if estado.get("respuesta") and estado.get("plan"):
        return {
            "iteracion": it,
            "siguiente": "FINISH",
            "log": [f"iter {it}: supervisor → FINISH (plan ya sintetizado)"],
        }

    llm = get_llm(temperature=0)
    prompt = (
        "Eres el supervisor de ATeMto, un planificador multiagente de transporte (red ATM / Metro TMB).\n"
        "Analiza el pedido del usuario y las notas recopiladas hasta ahora para decidir el siguiente paso:\n"
        "- tarifas: consulta de billetes, abonos, precio o condiciones de uso.\n"
        "- zonas: determinar la zona/sector tarifario de una población.\n"
        "- recorridos: calcular rutas o transbordos entre estaciones/poblaciones.\n"
        "- tiempos: consultar el tiempo de llegada del próximo metro TMB.\n"
        "- sintetizar: Llama a sintetizar cuando ya se hayan recopilado todas las notas para redactar el plan final. "
        "Se encarga de unir las notas recopiladas para redactar el plan final. Pasa directamente a 'FINISH' una vez completado.\n"
        "- FINISH: ya hay una respuesta o un plan final listo completo.\n\n"
        "Responde SOLO con una palabra, SOLO con una palabra: tarifas, zonas, recorridos, tiempos, sintetizar o FINISH.\n"
        "Si los datos necesarios de las notas ya están recopilados (o la consulta no requiere ciertos roles), pasa directamente a 'sintetizar' para dar una respuesta final.\n" \
        "Con el plan listo dado por el especialista 'sintetizar' pasa directamente a 'FINISH'.\n\n"
        f"Pedido: {estado.get('pedido')}\n"
        f"Notas tarifas: {estado.get('notas_tarifas')}\n"
        f"Notas zonas: {estado.get('notas_zonas')}\n"
        f"Notas recorridos: {estado.get('notas_recorridos')}\n"
        f"Notas tiempos: {estado.get('notas_tiempos')}\n"
        f"Respuesta actual: {estado.get('respuesta')}\n"
    )

    try:
        print("Ejecutando nodo supervisor...")
        out = llm.invoke([HumanMessage(content=prompt)])
        raw = _texto_llm(out.content)
        palabra = re.findall(r"[A-Za-z_]+", raw)
        siguiente = (palabra[0] if palabra else "").strip()
        print("="*50)
        print(f"OPCION ELEGIDA POR EL SUPERVISOR ANTES DE FALLBACK: {siguiente}")
        print("="*50)
        if siguiente not in OPCIONES:
            siguiente = _fallback_siguiente(estado)
    except Exception:
        siguiente = _fallback_siguiente(estado)

    return {
        "iteracion": it,
        "siguiente": siguiente,
        "log": [f"iter {it}: supervisor → {siguiente}"],
    }


def nodo_tarifas(estado: EstadoGrafo) -> dict:
    """Especialista: Responde sobre tarifas y condiciones de uso (puede usar tools). No cierra el plan."""
    print("Ejecutando nodo tarifas...")
    max_steps = int(estado.get("max_steps") or MAX_STEPS_DEFAULT)
    system = (
        "Eres el especialista en TARIFAS y CONDICIONES DE USO de la red ATM.\n"
        "Usa tools si ayudan (principalmente rag_ask_tarifas).\n"
        "Escribe notas cortas en español (no el plan final).\n"
    )
    user = (
        f"Pedido del usuario:\n{estado.get('pedido')}\n\n"
        "Devuelve solo las notas de tarifas o condiciones de uso."
    )
    
    texto, traza = _ejecutar_con_tools(system, user, max_steps)
    return {
        "notas_tarifas": texto,
        "traza_tools": traza,
        "log": ["tarifas: notas listas"],
    }

def nodo_zonas(estado: EstadoGrafo) -> dict:
    """Especialista: Responde las zonas a la que pertenecen las poblaciones (puede usar tools). No cierra el plan."""
    print("Ejecutando nodo zonas...")
    max_steps = int(estado.get("max_steps") or MAX_STEPS_DEFAULT)
    system = (
        "Eres el especialista en ZONAS de la red ATM.\n"
        "Usa tools si ayudan (principalmente zonas_poblacion_text, pero puedes usar otras si es necesario). \n"
        "Escribe notas cortas y directas con la población, su zona y su sector. En español (no el plan final).\n"
    )
    user = (
        f"Pedido del usuario:\n{estado.get('pedido')}\n\n"
        "Devuelve solo las notas sobre las zonas a las que pertenecen las poblaciones."
    )
    texto, traza = _ejecutar_con_tools(system, user, max_steps)
    return {
        "notas_zonas": texto,
        "traza_tools": traza,
        "log": ["zonas: notas listas"],
    }


def nodo_recorridos(estado: EstadoGrafo) -> dict:
    """Especialista: Calcula el recorrido entre dos estaciones o poblaciones de la red ATM (puede usar tools). No cierra el plan."""
    print("Ejecutando nodo recorridos...")
    max_steps = int(estado.get("max_steps") or MAX_STEPS_DEFAULT)
    system = (
        "Eres el especialista que calcula RUTAS y RECORRIDOS entre DOS estaciones o poblacionies de la red ATM.\n"
        "Debes usar la tool calcular_ruta_plano. Puedes usar otras tools si ayudan. \n"
        "Escribe notas cortas en español (no el plan final).\n"
    )
    user = (
        f"Pedido del usuario:\n{estado.get('pedido')}\n\n"
        "Devuelve solo las notas sobre los recorridos de la red ATM."
    )
    texto, traza = _ejecutar_con_tools(system, user, max_steps)
    return {
        "notas_recorridos": texto,
        "traza_tools": traza,
        "log": ["recorridos: notas listas"],
    }
    

def nodo_tiempos_tmb(estado: EstadoGrafo) -> dict:
    """Especialista: Responde los tiempos de llegada de los trenes a las estaciones únicamente del metro (TMB) (puede usar tools). No cierra el plan."""
    print("Ejecutando nodo tiempos TMB...")

    max_steps = int(estado.get("max_steps") or MAX_STEPS_DEFAULT)
    system = (
        "Eres el especialista que calcula los TIEMPOS DE LLEGADA de los trenes a las estaciones del metro (TMB)\n"
        "Solo considera las estaciones del metro (TMB). No incluye estaciones de otras redes como FGC, Rodalies, TRAM o buses.\n"
        "Usa tools si ayudan (principalmente API_llegada_tren_estacion_tmb y otras relacionadas, pero puedes usar otras si es necesario). \n"
        "Escribe notas cortas en español (no el plan final).\n"
    )
    user = (
        f"Pedido del usuario:\n{estado.get('pedido')}\n\n"
        "Devuelve solo las notas sobre los tiempos de llegada de los trenes a las estaciones del metro (TMB)."
    )
    texto, traza = _ejecutar_con_tools(system, user, max_steps)
    return {
        "notas_tiempos": texto,
        "traza_tools": traza,
        "log": ["tiempos: notas listas"],
    }

def nodo_sintetizar(estado: EstadoGrafo) -> dict:
    """Une las notas en respuesta + plan (viñetas). Deja el flujo listo para HITL."""
    llm = get_llm()
    prompt = (
        "Une las notas del plan de transporte (red ATM / Metro TMB)\n"
        "Incluye al menos 2 opciones (pero puedes incluir más opciones) como viñetas que empiecen por '- '.\n"
        "Una intro de 1-2 frases y luego las viñetas.\n\n"
        f"Pedido del usuario: {estado.get('pedido')}\n"
        f"Tarifas: {estado.get('notas_tarifas') or '(nada)'}\n"
        f"Zonas: {estado.get('notas_zonas') or '(nada)'}\n"
        f"Recorridos: {estado.get('notas_recorridos') or '(nada)'}\n"
        f"Tiempos: {estado.get('notas_tiempos') or '(nada)'}\n"
        "Excepciones: Si el pedido del usuario es un saludo ('hola', 'buenas', etc.):\n"
        "   - Saluda de forma amable e indícale que estás listo para ayudarle.\n"
        "   - Ofrece como opciones (en viñetas con '- ') las diferentes consultas"
        " que puede hacerte para continuar la conversación (calcular rutas,"
        " consultar tarifas/zonas o ver tiempos de espera del Metro TMB)."
    )
    out = llm.invoke([HumanMessage(content=prompt)])
    texto = _texto_llm(out.content)
    plan = _parse_plan(texto)

    print("Texto generado por el LLM:", texto)
    print("Plan parseado:", plan)
    
    if len(plan) < 2:
        print("No se generó un plan, se usarán las opciones por defecto.")
        plan = [
            "Consulta sobre una ruta o itinerario entre dos estaciones.",
            "Pregunta por zonas tarifarias, abonos de transporte o precios.",
            "Consulta el tiempo de llegada del próximo metro TMB a una estación.",
        ]
        texto = texto or (
            "¡Hola! Soy **ATeMto**, tu asistente de transporte de la ATM de Barcelona. ¿En qué puedo ayudarte hoy?\n\n"
            + "\n".join(f"- {p}" for p in plan)
        )
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
    grafo.add_node("tiempos", nodo_tiempos_tmb)
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
