import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = PROJECT_ROOT / "config" / "settings.json"
RELATIONSHIP_MAP_FILE = PROJECT_ROOT / "config" / "relationship_map.json"
KILL_SWITCH_FILE = PROJECT_ROOT / "kill_switch.flag"

DEFAULT_SETTINGS = {
    "dry_run": True,
    "min_delay_seconds": 3,
    "max_delay_seconds": 12,
}


def load_settings() -> dict:
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as file:
            settings = json.load(file)

        if not isinstance(settings, dict):
            return DEFAULT_SETTINGS.copy()

        result = DEFAULT_SETTINGS.copy()
        result.update(settings)
        return result
    except (OSError, json.JSONDecodeError, TypeError):
        return DEFAULT_SETTINGS.copy()


def is_dry_run() -> bool:
    return bool(load_settings().get("dry_run", True))


def is_kill_switch_active() -> bool:
    return KILL_SWITCH_FILE.exists()


def get_allowlist() -> set[str]:
    try:
        with RELATIONSHIP_MAP_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            relationship_map = json.load(file)
    except (OSError, json.JSONDecodeError, TypeError):
        return set()

    if not isinstance(relationship_map, dict):
        return set()

    return {
        str(key)
        for key, relationship in relationship_map.items()
        if key != "_default"
        and relationship != "unknown"
    }


def enforce_allowlist(jid: str) -> bool:
    if not isinstance(jid, str) or not jid.strip():
        return False

    number = jid.split("@", 1)[0].strip()
    return bool(number) and number in get_allowlist()