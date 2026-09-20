import argparse
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from ingestion.retrieval import retrieve_similar


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "retrieval_demo_output.txt"

RELATIONSHIPS = [
    "family",
    "friend",
    "professional",
    "unknown",
]

SAMPLE_QUERIES = {
    "family": [
        "Have you eaten?",
        "Are you coming home today?",
        "What are you doing?",
    ],
    "friend": [
        "Are you coming to college?",
        "What are you doing today?",
        "Send me the details.",
    ],
    "professional": [
        "Please share the project update.",
        "Can we schedule a meeting?",
        "What is the task status?",
    ],
    "unknown": [
        "Who is this?",
        "Why did you message me?",
        "Please introduce yourself.",
    ],
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--relationship",
        choices=["all", *RELATIONSHIPS],
        default="all",
    )
    parser.add_argument("--query")
    return parser.parse_args()


def run_demo():
    args = parse_args()
    relationships = (
        RELATIONSHIPS
        if args.relationship == "all"
        else [args.relationship]
    )

    distances_by_relationship = {}

    for relationship in relationships:
        queries = (
            [args.query]
            if args.query
            else SAMPLE_QUERIES[relationship]
        )

        all_distances = []

        for query in queries:
            results = retrieve_similar(relationship, query)

            if not results:
                print(
                    f"⚠ no data in history_{relationship}, "
                    "or no results; skipping"
                )
                continue

            print("---")
            print(f"Relationship: {relationship}")
            print(f"Query: {query}")
            print("---")

            for index, result in enumerate(results, start=1):
                print(f"Result {index}")
                print(f"Distance: {result['distance']:.6f}")
                print(f"Their message: {result['their_message']}")
                print(f"My reply: {result['my_reply']}")
                print("---")

            all_distances.extend(
                result["distance"]
                for result in results
            )

        distances_by_relationship[relationship] = all_distances

    print("\nSanity checks")
    print("=============")

    for relationship, distances in distances_by_relationship.items():
        if not distances:
            print(f"{relationship}: skipped — no distances available")
            continue

        increasing = all(
            left <= right
            for left, right in zip(distances, distances[1:])
        )

        status = "✅ expected" if increasing else "⚠ worth a second look"
        print(
            f"{relationship}: distances "
            f"{'monotonically increasing' if increasing else 'not globally monotonic'} "
            f"{status}"
        )


def main():
    captured = StringIO()

    try:
        with redirect_stdout(captured):
            run_demo()
    except Exception:
        output = captured.getvalue()
        print(output, end="")
        raise

    output = captured.getvalue()
    print(output, end="")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(output, encoding="utf-8")
    print(f"Saved output to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()