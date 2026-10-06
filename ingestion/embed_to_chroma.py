import hashlib
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAIRS_DIR = PROJECT_ROOT / "data" / "processed_pairs"
RELATIONSHIP_MAP_FILE = (
    PROJECT_ROOT / "config" / "contact_relationship_map.json"
)

MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
BATCH_SIZE = 32

RELATIONSHIPS = {
    "family",
    "friend",
    "professional",
    "unknown",
}


def normalize_relationship(value):
    value = str(value).strip().casefold()

    aliases = {
        "friends": "friend",
        "colleagues": "professional",
        "work": "professional",
    }

    value = aliases.get(value, value)
    return value if value in RELATIONSHIPS else "unknown"


def stable_id(pair, index, source_file):
    raw_value = (
        f"{source_file}|"
        f"{pair.get('conversation_id', '')}|"
        f"{pair.get('timestamp', '')}|"
        f"{index}"
    )
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def pair_files():
    return sorted(PAIRS_DIR.glob("*.jsonl"))


def load_pairs(files):
    pairs = []

    for file_path in files:
        pair_index = 0

        with file_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                if not line.strip():
                    continue

                try:
                    pair = json.loads(line)
                except json.JSONDecodeError as error:
                    raise SystemExit(
                        f"Invalid JSON in {file_path} on line "
                        f"{line_number}: {error}"
                    ) from error

                pairs.append(
                    {
                        "pair": pair,
                        "source_file": file_path.name,
                        "pair_index": pair_index,
                    }
                )
                pair_index += 1

    return pairs


def main():
    files = pair_files()
    if not files:
        raise SystemExit(
            f"No processed pair files found in {PAIRS_DIR} (*.jsonl)"
        )

    if not RELATIONSHIP_MAP_FILE.exists():
        raise SystemExit(
            f"Relationship map not found: {RELATIONSHIP_MAP_FILE}"
        )

    with RELATIONSHIP_MAP_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        relationship_map = json.load(file)

    pairs = load_pairs(files)
    if not pairs:
        raise SystemExit(
            f"No conversation pairs found across files in {PAIRS_DIR}"
        )

    print(
        f"Loaded {len(files)} file(s) and {len(pairs)} pairs "
        f"from {PAIRS_DIR}"
    )

    import chromadb
    from sentence_transformers import SentenceTransformer

    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print("Connecting to ChromaDB at http://localhost:8000")
    client = chromadb.HttpClient(host="localhost", port=8000)

    collections = {
        relationship: client.get_or_create_collection(
            name=f"history_{relationship}"
        )
        for relationship in sorted(RELATIONSHIPS)
    }

    counts = Counter()
    batches = {
        relationship: []
        for relationship in RELATIONSHIPS
    }

    for index, item in enumerate(pairs):
        pair = item["pair"]
        conversation_id = str(pair.get("conversation_id", ""))
        relationship = normalize_relationship(
            relationship_map.get(conversation_id, "unknown")
        )

        incoming_message = str(pair.get("their_message", "")).strip()

        if not incoming_message:
            continue

        batches[relationship].append(
            {
                "id": stable_id(
                    pair,
                    item["pair_index"],
                    item["source_file"],
                ),
                "document": incoming_message,
                "metadata": {
                    "conversation_id": conversation_id,
                    "my_reply": str(pair.get("my_reply", "")),
                    "timestamp": str(pair.get("timestamp", "")),
                    "relationship": relationship,
                },
            }
        )

        if len(batches[relationship]) >= BATCH_SIZE:
            flush_batch(
                model,
                collections[relationship],
                batches[relationship],
            )
            counts[relationship] += len(batches[relationship])
            batches[relationship].clear()

        processed = index + 1
        if processed % 50 == 0:
            print(f"Processed {processed}/{len(pairs)} pairs")

    for relationship, batch in batches.items():
        if batch:
            flush_batch(model, collections[relationship], batch)
            counts[relationship] += len(batch)

    print("\nEmbedding summary")
    print("-----------------")

    for relationship in sorted(RELATIONSHIPS):
        collection_name = f"history_{relationship}"
        collection_count = collections[relationship].count()
        print(
            f"{collection_name}: "
            f"{collection_count} entries "
            f"({counts[relationship]} processed this run)"
        )

        if collection_count == 0:
            print(
                f"WARNING: collection '{collection_name}' is empty."
            )


def flush_batch(model, collection, batch):
    documents = [item["document"] for item in batch]
    embeddings = model.encode(
        documents,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).tolist()

    collection.upsert(
        ids=[item["id"] for item in batch],
        documents=documents,
        embeddings=embeddings,
        metadatas=[item["metadata"] for item in batch],
    )


if __name__ == "__main__":
    main()