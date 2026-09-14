import argparse
from contextlib import redirect_stdout
from pathlib import Path
from io import StringIO

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "retrieval_demo_output.txt"
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"

RELATIONSHIPS = [
    "family",
    "friend",
    "professional",
    "unknown",
]

SAMPLE_QUERIES = {
    "family": [
        "Are you coming home today?",
        "Have you eaten?",
        "What are you doing?",
    ],
    "friend": [
        "Bro, are you coming to college?",
        "What are you doing today?",
        "Send me the details.",
    ],
    "professional": [
        "Please share the project update.",
        "Can we schedule a meeting?",
        "What is the status of the task?",
    ],
    "unknown": [
        "Who is this?",
        "Why did you message me?",
        "Please introduce yourself.",
    ],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Search relationship-specific WhatsApp history."
    )
    parser.add_argument(
        "--relationship",
        default="all",
        choices=["all", *RELATIONSHIPS],
        help="Relationship to search. Defaults to all.",
    )
    parser.add_argument(
        "--query",
        help="Custom query. If omitted, built-in queries are used.",
    )
    return parser.parse_args()


def search_collection(collection, model, query):
    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0].tolist()

    return collection.query(
        query_embeddings=[query_embedding],
        n_results=min(3, collection.count()),
        include=["documents", "metadatas", "distances"],
    )


def print_results(relationship, query, results):
    print("---")
    print(f"Relationship: {relationship}")
    print(f"Query: {query}")
    print("---")

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for index, document in enumerate(documents, start=1):
        metadata = metadatas[index - 1] or {}
        distance = distances[index - 1]

        print(f"Result {index}")
        print(f"Distance: {distance:.6f}")
        print(f"Incoming message: {document}")
        print(f"My reply: {metadata.get('my_reply', '')}")
        print(f"Timestamp: {metadata.get('timestamp', '')}")
        print("---")


def main():
    args = parse_args()

    relationships = (
        RELATIONSHIPS
        if args.relationship == "all"
        else [args.relationship]
    )

    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print("Connecting to ChromaDB at http://localhost:8000")
    client = chromadb.HttpClient(host="localhost", port=8000)

    distance_results = {}

    for relationship in relationships:
        collection_name = f"history_{relationship}"
        collection = client.get_or_create_collection(
            name=collection_name
        )

        count = collection.count()

        if count == 0:
            print(
                f"⚠ no data in {collection_name}, skipping"
            )
            distance_results[relationship] = []
            continue

        queries = (
            [args.query]
            if args.query
            else SAMPLE_QUERIES[relationship]
        )

        relationship_distances = []

        for query in queries:
            results = search_collection(collection, model, query)
            print_results(relationship, query, results)

            distances = results.get("distances", [[]])[0]
            relationship_distances.extend(distances)

        distance_results[relationship] = relationship_distances

    print("\nSanity checks")
    print("=============")

    for relationship in relationships:
        distances = distance_results[relationship]

        if not distances:
            print(
                f"{relationship}: skipped — no distances available"
            )
            continue

        monotonic = all(
            left <= right
            for left, right in zip(distances, distances[1:])
        )

        if monotonic:
            print(
                f"{relationship}: distances monotonically increasing "
                "✅ expected"
            )
        else:
            print(
                f"{relationship}: distances not globally monotonic "
                "⚠ worth a second look"
            )


def run_and_save():
    captured = StringIO()

    with redirect_stdout(captured):
        main()

    output = captured.getvalue()
    print(output)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(output, encoding="utf-8")
    print(f"Saved output to: {OUTPUT_FILE}")


if __name__ == "__main__":
    run_and_save()