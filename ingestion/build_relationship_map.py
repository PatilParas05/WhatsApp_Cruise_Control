import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAIRS_FILE = PROJECT_ROOT / "data" / "processed_pairs.jsonl"
MAP_FILE = PROJECT_ROOT / "config" / "contact_relationship_map.json"


def load_conversation_ids():
    conversation_ids = set()

    with PAIRS_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue

            try:
                pair = json.loads(line)
            except json.JSONDecodeError as error:
                raise SystemExit(
                    f"Invalid JSON on line {line_number}: {error}"
                )

            conversation_id = pair.get("conversation_id")
            if conversation_id:
                conversation_ids.add(conversation_id)

    return sorted(conversation_ids)


def main():
    if not PAIRS_FILE.exists():
        raise SystemExit(f"Pairs file not found: {PAIRS_FILE}")

    conversation_ids = load_conversation_ids()

    if MAP_FILE.exists():
        with MAP_FILE.open("r", encoding="utf-8") as file:
            relationship_map = json.load(file)
    else:
        relationship_map = {}

    new_ids = []

    for conversation_id in conversation_ids:
        if conversation_id not in relationship_map:
            relationship_map[conversation_id] = "REPLACE_ME"
            new_ids.append(conversation_id)

    relationship_map["_default"] = relationship_map.get(
        "_default",
        "unknown",
    )

    sorted_map = dict(sorted(relationship_map.items()))

    MAP_FILE.parent.mkdir(parents=True, exist_ok=True)

    with MAP_FILE.open("w", encoding="utf-8") as file:
        json.dump(sorted_map, file, indent=2, ensure_ascii=False)
        file.write("\n")

    placeholders = [
        key
        for key, value in sorted_map.items()
        if key != "_default" and value == "REPLACE_ME"
    ]

    print(f"Total conversation IDs: {len(conversation_ids)}")
    print(f"New IDs added: {len(new_ids)}")
    print(f"Relationship map written to: {MAP_FILE}")

    if placeholders:
        print("\nStill requiring classification:")
        for conversation_id in placeholders:
            print(f"  - {conversation_id}")
    else:
        print("\nNo conversation IDs require classification.")


if __name__ == "__main__":
    main()