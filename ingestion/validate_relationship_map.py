import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAIRS_DIR = PROJECT_ROOT / "data" / "processed_pairs"
MAP_FILE = PROJECT_ROOT / "config" / "contact_relationship_map.json"


def main():
    pair_files = sorted(PAIRS_DIR.glob("*.jsonl"))
    if not pair_files:
        print(
            f"FAIL: No processed pair files found in {PAIRS_DIR} (*.jsonl)"
        )
        return 1

    if not MAP_FILE.exists():
        print(f"FAIL: Relationship map not found: {MAP_FILE}")
        return 1

    conversation_ids = set()

    for file_path in pair_files:
        with file_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                if not line.strip():
                    continue

                try:
                    pair = json.loads(line)
                except json.JSONDecodeError as error:
                    print(
                        f"FAIL: Invalid JSON in {file_path} on line "
                        f"{line_number}: {error}"
                    )
                    return 1

                conversation_id = pair.get("conversation_id")
                if conversation_id:
                    conversation_ids.add(conversation_id)

    with MAP_FILE.open("r", encoding="utf-8") as file:
        relationship_map = json.load(file)

    missing = sorted(
        conversation_id
        for conversation_id in conversation_ids
        if relationship_map.get(conversation_id) in (None, "REPLACE_ME")
    )

    if missing:
        print("FAIL: These conversation IDs need classification:")
        for conversation_id in missing:
            print(f"  - {conversation_id}")
        return 1

    print(
        f"PASS: All {len(conversation_ids)} conversation IDs "
        "have relationships."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())