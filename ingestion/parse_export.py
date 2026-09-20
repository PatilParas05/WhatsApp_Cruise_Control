import argparse
import json
import re
from pathlib import Path
from config.constants import ONE_WORD_ACKS


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_EXPORT_DIR = PROJECT_ROOT / "data" / "raw_export"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed_pairs.jsonl"
PROCESSED_PAIRS_DIR = PROJECT_ROOT / "data" / "processed_pairs"

MAX_PAIRS_PER_CONVERSATION = 500

FILTER_SUBSTRINGS = (
    "messages and calls are end-to-end encrypted",
    "<media omitted>",
    "<image omitted>",
    "<video omitted>",
    "<audio omitted>",
    "<sticker omitted>",
    "<gif omitted>",
    "<document omitted>",
    "<album message>",
    "<unknown message>",
    "[forwarded]",
    "[call]",
    "- [call]",
    "this message was deleted",
    "you deleted this message",
    "missed voice call",
    "missed video call",
    "created group",
    "changed the subject",
    "added you",
    "changed this group's icon",
)

ACKNOWLEDGEMENTS = {
       "haa",
       "ok",
       "okay",
       "barr",
       "thik",
       "yup",
       "haan",
       "yes",
       "thanks",
       "thank you",
       "cool",
       "nice",
}

MESSAGE_PATTERN = re.compile(
    r"^\[(?P<date>[^,\]]+),\s*"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\]\s*"
    r"(?P<sender>[^:]+):\s*(?P<message>.*)$"
    r"|^(?P<plain_date>[^,\[]+),\s*"
    r"(?P<plain_time>\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\s*[-–]\s*"
    r"(?P<plain_sender>[^:]+):\s*(?P<plain_message>.*)$",
    re.IGNORECASE,
)


def is_filtered(text):
    lowered = text.casefold()
    return any(item in lowered for item in FILTER_SUBSTRINGS)


def is_acknowledgement(text):
    cleaned = text.strip().casefold()
    cleaned = re.sub(r"[.!?,;:]+$", "", cleaned).strip()
    return cleaned in ONE_WORD_ACKS


def conversation_id(filename):
    name = Path(filename).stem
    prefix = "WhatsApp Chat with "

    if name.casefold().startswith(prefix.casefold()):
        name = name[len(prefix):]

    return re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()


def parse_file(file_path):
    messages = []
    current = None

    def flush():
        if current and current["message"].strip():
            if not is_filtered(current["message"]):
                messages.append(current.copy())

    for raw_line in file_path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines():
        line = raw_line.strip()
        match = MESSAGE_PATTERN.match(line)

        if match:
            flush()
            current = None

            date = match.group("date") or match.group("plain_date")
            time = match.group("time") or match.group("plain_time")
            sender = (
                match.group("sender")
                or match.group("plain_sender")
            ).strip()
            message = (
                match.group("message")
                if match.group("message") is not None
                else match.group("plain_message")
            ).strip()

            if not is_filtered(message):
                current = {
                    "sender": sender,
                    "message": message,
                    "timestamp": f"{date.strip()}, {time.strip()}",
                }

        elif current and line and not is_filtered(line):
            current["message"] += f"\n{line}"

    flush()

    return [
        message
        for message in messages
        if not is_acknowledgement(message["message"])
    ]


def group_turns(messages):
    turns = []

    for message in messages:
        if turns and turns[-1]["sender"] == message["sender"]:
            turns[-1]["message"] += f"\n{message['message']}"
            turns[-1]["timestamp"] = message["timestamp"]
        else:
            turns.append(message.copy())

    return turns


def create_pairs(file_path, my_name):
    turns = group_turns(parse_file(file_path))
    pairs = []
    chat_id = conversation_id(file_path.name)

    for previous, current in zip(turns, turns[1:]):
        if (
            previous["sender"] != my_name
            and current["sender"] == my_name
        ):
            pairs.append(
                {
                    "conversation_id": chat_id,
                    "their_message": previous["message"],
                    "my_reply": current["message"],
                    "timestamp": current["timestamp"],
                }
            )

    return pairs[-MAX_PAIRS_PER_CONVERSATION:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--name",
        required=True,
        help="Exact sender name, for example: You",
    )
    args = parser.parse_args()

    files = sorted(RAW_EXPORT_DIR.glob("*.txt"))

    if not files:
        raise SystemExit(f"No .txt files found in {RAW_EXPORT_DIR}")

    PROCESSED_PAIRS_DIR.mkdir(parents=True, exist_ok=True)

    for file_path in files:
        pairs = create_pairs(file_path, args.name)
        output_file = (
            PROCESSED_PAIRS_DIR
            / f"{file_path.stem}.jsonl"
        )

        with output_file.open("w", encoding="utf-8") as output:
            for pair in pairs:
                output.write(
                    json.dumps(pair, ensure_ascii=False) + "\n"
                )

        print(f"{file_path.name}: {len(pairs)} pairs kept")
        print(f"Written to: {output_file}")

        if not pairs:
            print(
                f"Warning: {file_path.name} produced zero pairs. "
                "Check --name exactly."
            )


if __name__ == "__main__":
    main()