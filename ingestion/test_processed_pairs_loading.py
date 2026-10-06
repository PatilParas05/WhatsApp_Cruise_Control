import json

import pytest

from ingestion import embed_to_chroma


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row) + "\n")


def test_pair_files_and_load_pairs_are_deterministic(tmp_path, monkeypatch):
    write_jsonl(
        tmp_path / "b_chat.jsonl",
        [
            {
                "conversation_id": "chat-b",
                "their_message": "Hello",
                "my_reply": "Hi",
                "timestamp": "2025-01-01 10:00",
            }
        ],
    )
    write_jsonl(
        tmp_path / "a_chat.jsonl",
        [
            {
                "conversation_id": "chat-a",
                "their_message": "How are you?",
                "my_reply": "Great",
                "timestamp": "2025-01-01 09:00",
            }
        ],
    )

    monkeypatch.setattr(embed_to_chroma, "PAIRS_DIR", tmp_path)

    files = embed_to_chroma.pair_files()
    assert [file.name for file in files] == [
        "a_chat.jsonl",
        "b_chat.jsonl",
    ]

    pairs = embed_to_chroma.load_pairs(files)
    assert [(item["source_file"], item["pair_index"]) for item in pairs] == [
        ("a_chat.jsonl", 0),
        ("b_chat.jsonl", 0),
    ]


def test_stable_ids_include_source_file_context():
    pair = {
        "conversation_id": "chat-a",
        "timestamp": "2025-01-01 09:00",
    }

    left = embed_to_chroma.stable_id(pair, 0, "a_chat.jsonl")
    right = embed_to_chroma.stable_id(pair, 0, "b_chat.jsonl")

    assert left != right


def test_load_pairs_reports_json_error_with_file_context(tmp_path):
    broken_file = tmp_path / "broken.jsonl"
    broken_file.write_text(
        '{"conversation_id":"chat-a"}\n{bad json}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match=r"broken\.jsonl"):
        embed_to_chroma.load_pairs([broken_file])
