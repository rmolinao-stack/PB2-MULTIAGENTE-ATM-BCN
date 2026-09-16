"""Punto de entrada del pipeline RAG completo (S8 + S9 + S10).

Uso:
  python main.py --prepare                  # Ingesta + embeddings
  python main.py --index                    # Indexar en ChromaDB
  python main.py --index --recreate-index   # Borra la colección de ChromaDB antes de indexar
  python main.py --query "pregunta"         # Pregunta de prueba (retrieval + contexto)
  python main.py --ask "pregunta"           # RAG completo: respuesta generada
  python main.py --eval                     # Evaluación del retrieval con preguntas preestablecidas


App Streamlit: streamlit run app.py
"""

import argparse
import json

from core.pipeline import ejecutar_ingesta
from core.embed import ejecutar_embeddings
from core.index import ejecutar_indexacion
from core.retriever import recuperar
from core.context import imprimir_contexto
from services.rag_service import responder
from core.eval_retrieval import ejecutar_evaluacion


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

def main() -> None:
    parser = argparse.ArgumentParser(
        description="""
        Asistente de tarifas y abonos para la red ATM de Barcelona -
        sistema tarifario integrado que permite utilizar diferentes medios de transporte 
        (metro, autobuses, Ferrocarrils y Rodalies)
        """
    )
    parser.add_argument("--prepare", action="store_true", help="Ingesta + embeddings (tiempo estimado de ejecución ~ 10 min)")
    parser.add_argument("--solo-ingesta", action="store_true", help="Solo realizar la ingesta sin ejecutar embeddings")
    parser.add_argument("--index", action="store_true", help="Indexar en ChromaDB")
    parser.add_argument("--recreate-index", action="store_true", help="Borra la colección de ChromaDB antes de indexar")
    parser.add_argument("--query", type=str, help="Pregunta de prueba que solo ataca al retrieval (recuperación de contexto)")
    parser.add_argument("--ask", type=str, help="Pregunta con respusta generada por el modelo (RAG completo)")
    parser.add_argument("--eval", action="store_true", help="Evaluación del retrieval con preguntas preestablecidas")
    parser.add_argument("--top-k", type=int, default=None, help="Sobreescribe TOP-K")
    

    args = parser.parse_args()

    if not any(
        [args.prepare, args.index, args.recreate_index, args.query, args.ask, args.eval]
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
        #_cmd_query(args.query, args.top_k)
    if args.ask:
        print("Opción ask seleccionada ...")
        ejecutar_opcion_ask(args.ask, args.top_k)
    if args.eval:
        print("Opción eval seleccionada ...")
        ejecutar_evaluacion()
    

if __name__ == "__main__":
    main()