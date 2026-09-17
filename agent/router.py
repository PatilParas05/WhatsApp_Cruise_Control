import json
from pathlib import Path


def resolve_relationship(
    jid: str,
    map_path: str = "config/relationship_map.json",
) -> tuple[str, str | None]:
    """Resolve a WhatsApp JID to a relationship and Chroma collection."""

    if isinstance(jid, str) and jid.endswith("@g.us"):
        return "group", None

    if not isinstance(jid, str) or not jid.strip():
        relationship = "unknown"
    else:
        number = jid.split("@", 1)[0].strip()

        if not number:
            relationship = "unknown"
        else:
            try:
                with Path(map_path).open("r", encoding="utf-8") as file:
                    relationship_map = json.load(file)
            except (OSError, json.JSONDecodeError, TypeError):
                relationship_map = {}

            relationship = relationship_map.get(
                number,
                relationship_map.get("_default", "unknown"),
            )

            if not isinstance(relationship, str) or not relationship:
                relationship = "unknown"

    return relationship, f"history_{relationship}"