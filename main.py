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
  python main.py --agent-sin-auto-aprobar       # Solo para --agente-demo. Desactiva la autoaprobación de acciones.

App Streamlit: streamlit run app.py
"""

import argparse
import json

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
    # Aquí se llamaría a la función correspondiente del multiagente en modo interactivo

def ejecutar_opcion_multiagente_demo(max_turns: int | None, max_steps: int | None, sin_auto_aprobar: bool) -> None:
    print("Ejecutando multiagente en modo demo...")
    # Aquí se llamaría a la función correspondiente del multiagente en modo demo

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

    args = parser.parse_args()

    if not any(
        [args.prepare, args.index, args.recreate_index, args.query, args.ask, args.eval,
         args.agente_interactivo, args.agente_demo]
    ):
        parser.print_help()
        print(
            "\nEjemplo:\n"
            "  python main.py --prepare --index\n"
            '  python main.py --ask "¿Cuantos viajes puedo hacer con T-Usual?"\n'
            "  streamlit run app.py"
        )
        return

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
      

if __name__ == "__main__":
    main()