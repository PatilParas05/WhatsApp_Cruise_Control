import argparse
import json
import re
from collections import Counter
from pathlib import Path


HINGLISH_WORDS = {
    "hai", "kya", "nahi", "yaar", "matlab",
    "acha", "theek", "bhai", "haan", "toh",
}

MARATHI_ENGLISH_WORDS = {
    "barr", "kay", "nahi", "yaar", "mhanje",
    "achha", "thik", "bhai", "haan", "mag",
}

MARKDOWN_MESSAGE_PATTERN = re.compile(
    r"^\[\d{1,2}:\d{2}\s*(?:AM|PM)\]\s*\*\*(.+?):\*\*\s*(.*)$",
    re.IGNORECASE,
)

TXT_MESSAGE_PATTERN = re.compile(
    r"^(?:.+?),\s*(?:.+?)\s-\s(.+?):\s(.*)$"
)

WORD_PATTERN = re.compile(r"\b[\w']+\b", re.UNICODE)

EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2300-\u23FF]"
)


def contains_any_word(message, words):
    tokens = {word.lower() for word in WORD_PATTERN.findall(message)}
    return bool(tokens & words)


def parse_messages(file_path, sender_name):
    messages = []

    with file_path.open("r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            line = line.rstrip("\r\n")

            match = (
                MARKDOWN_MESSAGE_PATTERN.match(line)
                or TXT_MESSAGE_PATTERN.match(line)
            )

            if not match:
                continue

            sender, message = match.groups()

            if sender == sender_name:
                messages.append(message.strip())

    return messages


def build_stats(messages):
    count = len(messages)

    hinglish_count = sum(
        contains_any_word(message, HINGLISH_WORDS)
        for message in messages
    )

    marathi_count = sum(
        contains_any_word(message, MARATHI_ENGLISH_WORDS)
        for message in messages
    )

    word_counts = [
        len(WORD_PATTERN.findall(message))
        for message in messages
    ]

    emojis = Counter(
        emoji
        for message in messages
        for emoji in EMOJI_PATTERN.findall(message)
    )

    return {
        "total_sample_size": count,
        "hinglish_ratio_percent": round(
            hinglish_count / count * 100, 2
        ) if count else 0,
        "marathienglish_ratio_percent": round(
            marathi_count / count * 100, 2
        ) if count else 0,
        "average_message_length_words": round(
            sum(word_counts) / count, 2
        ) if count else 0,
        "top_emojis": [
            {"emoji": emoji, "frequency": frequency}
            for emoji, frequency in emojis.most_common(15)
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build persona style signals from a WhatsApp export."
    )

    parser.add_argument("--file", required=True)
    parser.add_argument(
        "--name",
        required=True,
        help='Exact sender name, such as "You"',
    )
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    input_path = Path(args.file)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    messages = parse_messages(input_path, args.name)

    if not messages:
        print(
            f'Warning: no messages found for sender "{args.name}". '
            "Check the exact sender name and file format."
        )
        return

    stats = build_stats(messages)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(stats, file, indent=2, ensure_ascii=False)

    print(f"Messages analyzed: {stats['total_sample_size']}")
    print(f"Hinglish ratio: {stats['hinglish_ratio_percent']}%")
    print(
        "Marathienglish ratio: "
        f"{stats['marathienglish_ratio_percent']}%"
    )
    print(
        "Average message length: "
        f"{stats['average_message_length_words']} words"
    )
    print(f"JSON written to: {output_path}")


if __name__ == "__main__":
    main()