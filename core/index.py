"""Indexación de embeddings.json en ChromaDB"""
import json
import chromadb

from common.config import EMBEDDING_MODEL, EMBEDDINGS_JSON, CHROMA_DIR, COLLECTION_NAME, INDEX_BATCH_SIZE

def _sanitizar_metadata(metadata: dict) -> dict:
    limpia: dict = {}
    for clave, valor in metadata.items():
        if valor is None:
            continue
        if isinstance(valor, (str, int, float, bool)):
            limpia[clave] = valor
        else:
            limpia[clave] = str(valor)
    return limpia

def cargar_embeddings_json() -> tuple[list[dict], str]:
    if not EMBEDDINGS_JSON.exists():
        raise FileNotFoundError(
            f"No existe {EMBEDDINGS_JSON}. Ejecuta antes: python main.py --prepare"
        )
    data = json.loads(EMBEDDINGS_JSON.read_text(encoding="utf-8"))
    modelo = data.get("embedding_model", EMBEDDING_MODEL)
    return data.get("items", []), modelo

def _generar_id(item: dict, indice: int) -> str:
    meta = item.get("metadata", {})
    chunk_index = meta.get("chunk_index", indice)
    return f"chunk_{chunk_index}"


def obtener_cliente_chroma() -> chromadb.PersistentClient:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def obtener_coleccion(
    client: chromadb.PersistentClient,
    crear: bool = True,
) -> chromadb.Collection:
    if crear:
        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return client.get_collection(name=COLLECTION_NAME)


def borrar_coleccion(client: chromadb.PersistentClient) -> None:
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Colección '{COLLECTION_NAME}' eliminada.")
    except Exception:
        print(f"  Colección '{COLLECTION_NAME}' no existía.")

def ejecutar_indexacion(recreate: bool = False) -> int:
    items, modelo_json = cargar_embeddings_json()
    if not items:
        raise ValueError("embeddings.json no contiene items.")

    client = obtener_cliente_chroma()
    if recreate:
        borrar_coleccion(client)

    collection = obtener_coleccion(client)

    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for i, item in enumerate(items):
        ids.append(_generar_id(item, i))
        embeddings.append(item["vector"])
        documents.append(item["text"])
        meta = _sanitizar_metadata(item.get("metadata", {}))
        meta["embedding_model"] = modelo_json
        metadatas.append(meta)

    print(f"Indexando {len(ids)} vectores en '{COLLECTION_NAME}' ...")

    for inicio in range(0, len(ids), INDEX_BATCH_SIZE):
        fin = inicio + INDEX_BATCH_SIZE
        collection.add(
            ids=ids[inicio:fin],
            embeddings=embeddings[inicio:fin],
            documents=documents[inicio:fin],
            metadatas=metadatas[inicio:fin],
        )

    total = collection.count()
    print(f"  ChromaDB: {total} documentos en {CHROMA_DIR}")
    return total
