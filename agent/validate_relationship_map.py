import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = PROJECT_ROOT / "config" / "relationship_map.json"

VALID_RELATIONSHIPS = {
    "family",
    "friend",
    "professional",
    "unknown",
}

INVALID_KEY_PATTERN = re.compile(r"[+\sA-Za-z-]")


def main():
    issues = []

    if not MAP_FILE.exists():
        print(f"FAIL: File not found: {MAP_FILE}")
        return 1

    try:
        with MAP_FILE.open("r", encoding="utf-8") as file:
            relationship_map = json.load(file)
    except json.JSONDecodeError as error:
        print(f"FAIL: Invalid JSON: {error}")
        return 1

    if not isinstance(relationship_map, dict):
        print("FAIL: Relationship map must contain a JSON object.")
        return 1

    if "_default" not in relationship_map:
        issues.append("Missing required '_default' key.")
    elif relationship_map["_default"] not in VALID_RELATIONSHIPS:
        issues.append(
            f"Invalid _default value: {relationship_map['_default']!r}. "
            f"Expected one of: {sorted(VALID_RELATIONSHIPS)}."
        )

    for key in relationship_map:
        if key == "_default":
            continue

        if not isinstance(key, str):
            issues.append(f"Invalid non-string key: {key!r}")
            continue

        if INVALID_KEY_PATTERN.search(key):
            issues.append(
                f"Invalid key {key!r}: contains '+', spaces, dashes, "
                "or letters."
            )

        if not key.isdigit():
            issues.append(
                f"Invalid key {key!r}: must contain digits only."
            )
            continue

        if len(key) < 8 or len(key) > 15:
            issues.append(
                f"Invalid key {key!r}: has {len(key)} digits; "
                "expected 8 to 15."
            )

    print(f"Checked file: {MAP_FILE}")
    print(f"Conversation IDs checked: {len(relationship_map) - 1}")

    if issues:
        print(f"\nFAIL: {len(issues)} issue(s) found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("\nPASS: Relationship map is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())