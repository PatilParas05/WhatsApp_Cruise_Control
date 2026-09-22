import json
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request

from agent.decision_engine import should_reply
from agent.generator import generate_reply
from agent.router import resolve_relationship
from ingestion.retrieval import retrieve_similar


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
CONSOLE_FEED = LOG_DIR / "console_feed.jsonl"

app = Flask(__name__)


def append_console_feed(record):
    os.makedirs(LOG_DIR, exist_ok=True)

    with CONSOLE_FEED.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


@app.post("/process")
def process_message():
    payload = request.get_json(silent=True) or {}

    jid = payload.get("jid", "")
    text = payload.get("text", "")
    message_type = payload.get("message_type", "text")
    is_forwarded = payload.get("is_forwarded", False)
    from_me = payload.get("from_me", False)

    relationship, _ = resolve_relationship(jid)

    message = {
        "from_me": from_me,
        "text": text,
        "message_type": message_type,
        "is_forwarded": is_forwarded,
    }

    can_reply, reason = should_reply(message, relationship)
    reply = None
    retrieval_trace = []

    if relationship != "group":
        retrieval_trace = retrieve_similar(
            relationship,
            text,
            k=3,
        )

    if can_reply:
        if reason == "media_ack":
            reply = message.get("reply")
        else:
            reply = generate_reply(text, relationship)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "jid": jid,
        "relationship": relationship,
        "decision": "reply" if can_reply else "ignore",
        "reason": reason,
        "reply": reply,
        "retrieval_trace": retrieval_trace,
    }

    append_console_feed(record)

    return jsonify(
        {
            "should_reply": can_reply,
            "reply": reply,
            "relationship": relationship,
            "reason": reason,
        }
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=False,
    )