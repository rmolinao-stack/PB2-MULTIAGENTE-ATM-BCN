"""Punto de entrada del pipeline RAG completo (S8 + S9 + S10).

Uso CLI para RAG:
  python main.py --prepare                      # Ingesta + embeddings
  python main.py --prepare --solo-ingesta       # Solo realizar la ingesta sin ejecutar embeddings
  python main.py --index                        # Indexar en ChromaDB
  python main.py --index --recreate-index       # Borra la colección de ChromaDB antes de indexar
  python main.py --query "pregunta"             # Pregunta de prueba (retrieval + contexto)
  python main.py --ask "pregunta"               # RAG completo: respuesta generada
  python main.py --query "pregunta" --top-k 5   # Sobreescribe TOP-K
  python main.py --ask "pregunta" --top-k 5     # Sobreescribe TOP-K
  python main.py --eval                         # Evaluación del retrieval con preguntas preestablecidas

Uso CLI para workflow LangGraph:
  python main.py --agente-interactivo           # Ejecuta el workflow del multiagente por CLI en modo interactivo
  python main.py --agente-demo                  # Ejecuta una demo del workflow del multiagente por CLI. Por defecto autoaprueba las acciones.
  python main.py --agente-max-turns 4           # Limita el número máximo de turnos del workflow del multiagente
  python main.py --agente-max-steps 4           # Limita el número máximo de pasos del workflow del multiagente
  python main.py --agente-sin-auto-aprobar      # Solo para --agente-demo. Desactiva la autoaprobación de acciones.

Uso para test de tools
  python main.py --test-tool-rag-tarifas      # Ejecuta un test de pruebas para la tool rag-tarifas
  python main.py --test-tool-plano            # Ejecuta un juego de pruebas para la tool calcular_ruta_plano
  python main.py --test-tool-zonas            # Ejecuta un test de pruebas para la tool de obtención de la zona de varias poblaciones

App Streamlit: streamlit run app_rag.py
"""

import argparse
import json

from multiagent.state import crear_estado
from multiagent.agent import aprobar_plan, nuevo_thread_id, procesar_turno, run_demo
from rag.pipeline import ejecutar_ingesta
from rag.embed import ejecutar_embeddings
from rag.index import ejecutar_indexacion
from rag.retriever import recuperar
from rag.context import imprimir_contexto
from services.rag_service import responder
from rag.eval_retrieval import ejecutar_evaluacion


def preparar_ingesta_y_embeddings(solo_ingesta: bool = False) -> None:
    ejecutar_ingesta()
    if not solo_ingesta:
        ejecutar_embeddings()

def indexar_en_chromadb(recreate: bool) -> None:
    total = ejecutar_indexacion(recreate=recreate)
    print(f"\nÍndice listo: {total} vectores en ChromaDB.")

def ejecutar_opcion_query(pregunta: str, top_k: int | None) -> None:
    chunks = recuperar(pregunta, top_k=top_k)
    imprimir_contexto(chunks)

def ejecutar_opcion_ask(pregunta: str, top_k: int | None) -> None:

    resultado = responder(pregunta, top_k=top_k)
    print(json.dumps(
        {
            "respuesta": resultado.get("respuesta"),
            "fuentes": resultado.get("fuentes"),
            "error": resultado.get("error"),
        },
        ensure_ascii=False,
        indent=2,
    ))

def ejecutar_opcion_multiagente_interactivo(max_turns: int | None, max_steps: int | None) -> None:
    print("Ejecutando multiagente en modo interactivo...")
    estado = crear_estado("")
    tid = nuevo_thread_id()
    
    print(f"Modo multiagente interactivo | thread_id={tid}")
    print("Para terminar teclar: 'salir', 'exit' o 'quit'. Si hay HITL: 'aprobar' / 'rechazar'.\n")
    
    for _ in range(max_turns):
              
        if estado.get("pendiente_hitl"):
            print("HITL: plan pendiente. Escribe aprobar / rechazar")
            for item in estado.get("plan") or []:
                print(f"  - {item}")
        mensaje = input("Tú: ").strip()
        
        if not mensaje or mensaje.lower() in {"salir", "exit", "quit"}:
            break
        
        if mensaje.lower() in {"aprobar", "approve", "si", "sí", "yes"}:
            if estado.get("pendiente_hitl"):
                estado = aprobar_plan(tid, True, estado)
            else:
                print("(No hay plan pendiente)")
                continue
        elif mensaje.lower() in {"rechazar", "reject", "no"}:
            if estado.get("pendiente_hitl"):
                estado = aprobar_plan(tid, False, estado)
            else:
                print("(No hay plan pendiente)")
                continue
        else:
            estado = procesar_turno(estado, mensaje, tid, max_steps=max_steps)
        
        print("Agente:", estado.get("respuesta") or "(sin respuesta)")
        
        if estado.get("plan"):
            print("Plan:", estado["plan"])
        
        if estado.get("log"):
            print("Log:", estado["log"][-5:])
        
        print(
            "done:",
            estado.get("done"),
            "| hitl:",
            estado.get("pendiente_hitl"),
            "| error:",
            estado.get("error"),
        )
        
        print()
        
        if estado.get("done") or estado.get("error"):
            break
    
    estado["thread_id"] = tid
    
    return estado

def ejecutar_opcion_multiagente_demo(max_turns: int | None, max_steps: int | None, sin_auto_aprobar: bool) -> None:
    print("Ejecutando multiagente en modo demo...")
    # Aquí se llamaría a la función correspondiente del multiagente en modo demo

    run_demo(
        max_turns=max_turns,
        max_steps=max_steps,
        auto_aprobar=not sin_auto_aprobar,
    )

def main() -> None:
    parser = argparse.ArgumentParser(
        description="""
        Asistente de tarifas y abonos para la red ATM de Barcelona -
        sistema tarifario integrado que permite utilizar diferentes medios de transporte 
        (metro, autobuses, Ferrocarrils y Rodalies)
        """
    )

    ############ RMO: PARAMETROS DEL RAG ###################
    parser.add_argument("--prepare", action="store_true", help="Ingesta + embeddings (tiempo estimado de ejecución ~ 10 min)")
    parser.add_argument("--solo-ingesta", action="store_true", help="Solo realizar la ingesta sin ejecutar embeddings")
    parser.add_argument("--index", action="store_true", help="Indexar en ChromaDB")
    parser.add_argument("--recreate-index", action="store_true", help="Borra la colección de ChromaDB antes de indexar")
    parser.add_argument("--query", type=str, help="Pregunta de prueba que solo ataca al retrieval (recuperación de contexto)")
    parser.add_argument("--ask", type=str, help="Pregunta con respusta generada por el modelo (RAG completo)")
    parser.add_argument("--eval", action="store_true", help="Evaluación del retrieval con preguntas preestablecidas")
    parser.add_argument("--top-k", type=int, default=None, help="Sobreescribe TOP-K")
    
    ########## RMO: PARAMETROS DEL MULTIAGENTE ###############
    parser.add_argument("--agente-interactivo", action="store_true", help="Ejecuta el workflow del multiagente en modo interactivo por CLI")
    parser.add_argument("--agente-demo", action="store_true", help="Ejecuta el workflow del multiagente por CLI")
    parser.add_argument("--agente-max-turns", type=int, default=None, help="Limita el número máximo de turnos del workflow del multiagente")
    parser.add_argument("--agente-max-steps", type=int, default=None, help="Limita el número máximo de pasos del workflow del multiagente")
    parser.add_argument("--agente-sin-auto-aprobar", action="store_true", help="Solo para --agente-demo. Desactiva la autoaprobación de acciones.")    
    
    ########## RMO: PARAMETROS DE TESTEO PUNTUAL ###############
    parser.add_argument("--test-tool-plano", action="store_true", help="Ejecuta un juego de pruebas para la tool calcular_ruta_plano")
    parser.add_argument("--test-tool-rag-tarifas", action="store_true", help="Ejecuta un test de pruebas para la tool rag-tarifas")
    parser.add_argument("--test-tool-zonas", action="store_true", help="Ejecuta un test de pruebas para la tool de obtención de la zona de varias poblaciones")


    args = parser.parse_args()

    #if not any(
    #    [args.prepare, args.index, args.recreate_index, args.query, args.ask, args.eval,
    #     args.agente_interactivo, args.agente_demo]
    #):
    #    parser.print_help()
    #    print(
    #        "\nEjemplo:\n"
    #        "  python main.py --prepare --index\n"
    #        '  python main.py --ask "¿Cuantos viajes puedo hacer con T-Usual?"\n'
    #        "  streamlit run app.py"
    #    )
    #    return

    if args.prepare:
        print("Opción prepare seleccionada ...")
        preparar_ingesta_y_embeddings(solo_ingesta=args.solo_ingesta)
    if args.index:
        print("Opción index seleccionada ...")
        indexar_en_chromadb(recreate=args.recreate_index)
    if args.query:
        print("Opción query seleccionada ...")
        ejecutar_opcion_query(args.query, args.top_k)
    if args.ask:
        print("Opción ask seleccionada ...")
        ejecutar_opcion_ask(args.ask, args.top_k)
    if args.eval:
        print("Opción eval seleccionada ...")
        ejecutar_evaluacion()
    if args.agente_interactivo:
        print("Opción agente-interactivo seleccionada ...")
        ejecutar_opcion_multiagente_interactivo(max_turns=args.agente_max_turns, max_steps=args.agente_max_steps)
    if args.agente_demo:
        print("Opción agente-demo seleccionada ...")
        ejecutar_opcion_multiagente_demo(max_turns=args.agente_max_turns, max_steps=args.agente_max_steps, sin_auto_aprobar=args.agente_sin_auto_aprobar)
    if args.test_tool_plano:
        print("Opción test-tool-plano seleccionada ...")
        from multiagent.tools.ruta_plano import calcular_ruta_plano
        from common.cargar_api_key import configurar_gemini_api_key
        configurar_gemini_api_key()
        print("EVALUACION 1: ", calcular_ruta_plano.func("Santa coloma", "Sants"))
        print("EVALUACION 2: ", calcular_ruta_plano.func("Masnou", "Viladecavall"))
        print("EVALUACION 3: ", calcular_ruta_plano.func("Alella", "Terrassa"))
        print("EVALUACION 4: ", calcular_ruta_plano.func("Madrid", "Valencia"))
    if args.test_tool_rag_tarifas:
        print("Opción test-tool-rag-tarifas seleccionada ...")
        from multiagent.tools.rag_tarifas import rag_ask_tarifas
        from common.cargar_api_key import configurar_gemini_api_key
        configurar_gemini_api_key()
        print("EVALUACION 1: ", rag_ask_tarifas.func("¿Cual es el billete de 10 viajes?"))
    if args.test_tool_zonas:
        print("Opción test-tool-zonas seleccionada ...")
        from multiagent.tools.zonas import zonas_poblacion_text
        print("EVALUACION 1: ", zonas_poblacion_text.func("Santa coloma y Sant Cugat y Masnou"))

if __name__ == "__main__":
    main()