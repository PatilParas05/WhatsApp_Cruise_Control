import json

from router import resolve_relationship


def write_map(tmp_path, data):
    map_file = tmp_path / "relationship_map.json"
    map_file.write_text(
        json.dumps(data),
        encoding="utf-8",
    )
    return str(map_file)


def test_known_number_resolves_correctly(tmp_path):
    map_path = write_map(
        tmp_path,
        {
            "_default": "unknown",
            "000000000000": "friend",
        },
    )

    result = resolve_relationship(
        "000000000000@s.whatsapp.net",
        map_path,
    )

    assert result == ("friend", "history_friend")


def test_unknown_number_uses_default(tmp_path):
    map_path = write_map(
        tmp_path,
        {
            "_default": "professional",
        },
    )

    result = resolve_relationship(
        "911234567890@lid",
        map_path,
    )

    assert result == ("professional", "history_professional")


def test_group_jid_never_reads_map(tmp_path):
    missing_map = tmp_path / "does_not_exist.json"

    result = resolve_relationship(
        "123456789@g.us",
        str(missing_map),
    )

    assert result == ("group", None)


def test_malformed_or_empty_jid_is_safe(tmp_path):
    map_path = write_map(tmp_path, {"_default": "unknown"})

    assert resolve_relationship("", map_path) == (
        "unknown",
        "history_unknown",
    )

    assert resolve_relationship("@lid", map_path) == (
        "unknown",
        "history_unknown",
    )

    assert resolve_relationship(None, map_path) == (
        "unknown",
        "history_unknown",
    )


def test_missing_default_falls_back_to_unknown(tmp_path):
    map_path = write_map(tmp_path, {})

    result = resolve_relationship(
        "911234567890@s.whatsapp.net",
        map_path,
    )

    assert result == ("unknown", "history_unknown")