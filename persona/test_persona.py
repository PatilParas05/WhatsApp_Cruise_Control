import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONA_FILE = PROJECT_ROOT / "persona" / "persona.json"
OUTPUT_FILE = PROJECT_ROOT / "persona" / "sample_output.md"

TEST_LIMIT = 5

CHAT_CONFIG = [
    {
        "chat": PROJECT_ROOT / "Chat with friends" / "chatGau.md",
        "signals": PROJECT_ROOT / "persona" / "style_signals_chatGau.json",
    },
    {
        "chat": PROJECT_ROOT / "Chat with friends" / "chatKru.md",
        "signals": PROJECT_ROOT / "persona" / "style_signals_chatKru.json",
    },
]

MESSAGE_PATTERN = re.compile(
    r"^\[(\d{1,2}:\d{2}\s*(?:AM|PM))\]\s+\*\*(.+?):\*\*\s*(.*)$",
    re.IGNORECASE,
)


def parse_messages(chat_file):
    messages = []

    for line in chat_file.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines():
        match = MESSAGE_PATTERN.match(line)

        if not match:
            continue

        time_text, sender, message = match.groups()

        if sender != "You" and message.strip():
            messages.append(
                {
                    "time": time_text,
                    "sender": sender,
                    "message": message.strip(),
                }
            )

    return messages[:TEST_LIMIT]


def generate_reply(client, persona, signals, incoming, model):
    relationship = persona["relationships"]["friends"]

    prompt = f"""
You are texting as: {persona["identity"]}

Relationship tone:
{relationship["tone"]}

Real example replies:
{json.dumps(relationship["example_replies"], ensure_ascii=False)}

Style signals for this chat:
{json.dumps(signals, ensure_ascii=False, indent=2)}

Hard rules:
{json.dumps(persona["hard_rules"], ensure_ascii=False)}

Incoming message:
"{incoming}"

Reply with one short WhatsApp-style message only.
Match the real texting cadence. Do not explain the reply.
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as error:
        return f"_Generation failed: `{error}`_"


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY was not found in .env.")

    persona = json.loads(
        PERSONA_FILE.read_text(encoding="utf-8")
    )

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    output = [
        "# Persona Test Output",
        "",
        f"Model: `{model}`",
        "",
        f"Testing {TEST_LIMIT} messages from each chat.",
        "",
    ]

    total = 0

    for config in CHAT_CONFIG:
        chat_file = config["chat"]
        signals_file = config["signals"]

        if not chat_file.exists() or not signals_file.exists():
            continue

        signals = json.loads(
            signals_file.read_text(encoding="utf-8")
        )
        messages = parse_messages(chat_file)

        output.extend(
            [
                f"## {chat_file.name}",
                "",
                f"Signals file: `{signals_file.name}`",
                "",
            ]
        )

        for index, item in enumerate(messages, start=1):
            total += 1

            reply = generate_reply(
                client,
                persona,
                signals,
                item["message"],
                model,
            )

            output.extend(
                [
                    f"### Test {index}",
                    "",
                    f"**From:** {item['sender']}",
                    "",
                    f"**Incoming:** {item['message']}",
                    "",
                    f"**Generated reply:** {reply}",
                    "",
                    "---",
                    "",
                ]
            )

            print(f"Tested {chat_file.name}: {index}/{len(messages)}")

    output.insert(3, f"Total messages tested: {total}")
    OUTPUT_FILE.write_text("\n".join(output), encoding="utf-8")

    print(f"\nSaved output to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()