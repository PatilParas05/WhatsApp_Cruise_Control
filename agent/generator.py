import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from ingestion.retrieval import retrieve_similar


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONA_FILE = PROJECT_ROOT / "persona" / "persona.json"
MODEL_NAME = "gemini-3.5-flash"
NO_REPLY = "[no reply generated — check response.candidates for details]"


def load_persona():
    with PERSONA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def relationship_profile(persona, relationship):
    relationships = persona.get("relationships", {})

    profile = relationships.get(relationship)
    if profile is None:
        profile = relationships.get(f"{relationship}s")
    if profile is None:
        profile = relationships.get("friends", {})

    return profile if isinstance(profile, dict) else {}


def generate_reply(incoming_text: str, relationship: str) -> str:
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from .env")

    persona = load_persona()
    profile = relationship_profile(persona, relationship)

    similar_pairs = retrieve_similar(
        relationship,
        incoming_text,
        k=3,
    )

    examples_section = ""

    if similar_pairs:
        examples = []

        for pair in similar_pairs:
            examples.append(
                "Incoming: "
                f"{pair.get('their_message', '')}\n"
                "Reply: "
                f"{pair.get('my_reply', '')}"
            )

        examples_section = (
            "\nRelevant past examples:\n"
            + "\n\n".join(examples)
            + "\n"
        )

    tone = profile.get(
        "tone",
        profile.get("style", "casual and natural"),
    )

    typical_length = persona.get(
        "avg_message_length_words",
        persona.get("average_message_length_words", 4),
    )

    prompt = f"""
You are replying as this person:

Identity:
{persona.get("identity", "")}

Relationship:
{relationship}

Tone for this relationship:
{tone}

Hinglish ratio:
{persona.get("hinglish_ratio", 0)}

Typical message length:
approximately {typical_length} words

Hard rules:
{json.dumps(persona.get("hard_rules", []), ensure_ascii=False)}
{examples_section}
New incoming message:
{incoming_text}

Write one natural WhatsApp reply only.
Do not explain the reply.
Do not add quotation marks.
Keep it close to the typical message length.
"""

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    reply = getattr(response, "text", None)

    if not reply or not reply.strip():
        return NO_REPLY

    return reply.strip()


if __name__ == "__main__":
    examples = [
        ("Hii", "friend"),
        ("J1 zhala ka re", "friend"),
        ("Can you send me the project update?", "professional"),
    ]

    for incoming_text, relationship in examples:
        print(f"Incoming: {incoming_text}")
        print(f"Reply: {generate_reply(incoming_text, relationship)}")
        print("---")