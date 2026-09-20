from sentence_transformers import SentenceTransformer
import chromadb


MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"

MODEL = SentenceTransformer(MODEL_NAME)
CHROMA_CLIENT = chromadb.HttpClient(host="localhost", port=8000)


def retrieve_similar(
    relationship: str,
    incoming_message: str,
    k: int = 3,
) -> list[dict]:
    collection_name = f"history_{relationship}"

    existing_collections = CHROMA_CLIENT.list_collections()
    existing_names = {
        collection.name
        for collection in existing_collections
    }

    if collection_name not in existing_names:
        return []

    collection = CHROMA_CLIENT.get_collection(collection_name)
    count = collection.count()

    if count == 0:
        return []

    query_embedding = MODEL.encode(
        [incoming_message],
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0].tolist()

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(k, count),
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0] or []
    metadatas = result.get("metadatas", [[]])[0] or []
    distances = result.get("distances", [[]])[0] or []

    return [
        {
            "their_message": documents[index] or "",
            "my_reply": (
                metadatas[index].get("my_reply", "")
                if index < len(metadatas) and metadatas[index]
                else ""
            ),
            "distance": float(distances[index]),
        }
        for index in range(len(documents))
    ]