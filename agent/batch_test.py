import json
from pathlib import Path

from agent.decision_engine import should_reply
from agent.generator import generate_reply
from agent.router import resolve_relationship


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = PROJECT_ROOT / "config" / "relationship_map.json"


def known_jid():
    relationship_map = json.loads(
        MAP_FILE.read_text(encoding="utf-8")
    )

    for number in relationship_map:
        if number != "_default":
            return f"{number}@s.whatsapp.net"

    raise RuntimeError("No contact found in relationship_map.json")


def main():
    jid = known_jid()

    cases = [
        ("Own message", jid, True, "I sent it", "text", False),
        ("Group", "123456789@g.us", False, "Hello everyone", "text", False),
        ("Unknown", "000000000000@s.whatsapp.net", False, "Hello", "text", False),
        ("Media only", jid, False, "", "image", False),
        ("Forwarded", jid, False, "Forwarded news", "text", True),
        ("Acknowledgement", jid, False, "thanks", "text", False),
        ("Money", jid, False, "Can you send me 5000 rupees?", "text", False),
        ("Casual 1", jid, False, "What are you doing today?", "text", False),
        ("Casual 2", jid, False, "Are you coming to college?", "text", False),
    ]

    print(f"{'Test':<18} {'Relationship':<15} {'Decision':<8} Reason")
    print("-" * 90)

    for name, case_jid, from_me, text, kind, forwarded in cases:
        relationship, _ = resolve_relationship(
            case_jid,
            str(MAP_FILE),
        )

        message = {
            "from_me": from_me,
            "text": text,
            "message_type": kind,
            "is_forwarded": forwarded,
        }

        can_reply, reason = should_reply(message, relationship)
        reply = ""

        if can_reply:
            reply = generate_reply(text, relationship)

        print(
            f"{name:<18} {relationship:<15} "
            f"{'reply' if can_reply else 'ignore':<8} {reason}"
        )

        if reply:
            print(f"  Reply: {reply}")


if __name__ == "__main__":
    main()