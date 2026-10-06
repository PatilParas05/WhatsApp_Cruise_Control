import json
import random
import re
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "data" / "processed_pairs"
NOISE_TERMS = ("omitted", "<media", "deleted")


def words(text):
    return re.findall(r"\w+", text.casefold())


def near_identical(left, right):
    left_words = set(words(left))
    right_words = set(words(right))

    if not left_words or not right_words:
        return False

    overlap = len(left_words & right_words)
    return overlap / max(len(left_words), len(right_words)) >= 0.8


def main():
    pairs = []
    issues = []
    files = sorted(INPUT_DIR.glob("*.jsonl"))

    if not files:
        print(f"FAIL: No processed pair files found in {INPUT_DIR} (*.jsonl)")
        return

    for file_path in files:
        with file_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                if not line.strip():
                    continue

                try:
                    pair = json.loads(line)
                    pairs.append(pair)
                except json.JSONDecodeError:
                    issues.append(
                        f"Invalid JSON in {file_path} on line {line_number}"
                    )

    counts = Counter(pair.get("conversation_id", "unknown") for pair in pairs)

    print("PAIR VALIDATION REPORT")
    print("======================")
    print(f"Total pairs: {len(pairs)}")
    print("\nPairs per conversation:")

    for conversation_id, count in sorted(counts.items()):
        print(f"  {conversation_id}: {count}")

        if count == 0:
            issues.append(
                f"Conversation '{conversation_id}' has zero pairs"
            )

    if not counts:
        issues.append("No conversation pairs were found")

    print("\nRandom sample:")
    sample = random.sample(pairs, min(5, len(pairs)))

    for index, pair in enumerate(sample, 1):
        print(f"\n--- Sample {index} ---")
        print(f"Conversation: {pair.get('conversation_id', 'unknown')}")
        print(f"Their message: {pair.get('their_message', '')}")
        print(f"My reply: {pair.get('my_reply', '')}")

    for index, pair in enumerate(pairs, 1):
        their_message = str(pair.get("their_message", "")).strip()
        my_reply = str(pair.get("my_reply", "")).strip()

        combined = f"{their_message}\n{my_reply}".casefold()

        for term in NOISE_TERMS:
            if term in combined:
                issues.append(
                    f"Pair {index}: leaked noise term {term!r}"
                )
                break

        if not their_message or not my_reply:
            issues.append(f"Pair {index}: empty message or reply")

        if len(words(my_reply)) > 100:
            issues.append(
                f"Pair {index}: reply has more than 100 words"
            )

        if their_message.casefold() == my_reply.casefold():
            issues.append(f"Pair {index}: messages are identical")
        elif near_identical(their_message, my_reply):
            issues.append(f"Pair {index}: messages are near-identical")

    print("\nValidation result:")

    if issues:
        print(f"⚠ {len(issues)} issues found — review above")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ Looks good")


if __name__ == "__main__":
    main()