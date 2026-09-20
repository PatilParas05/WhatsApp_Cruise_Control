import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=api_key)
model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

try:
    response = client.models.generate_content(
        model=model,
        contents="Say hello in one word.",
    )
    print(f"API key works. Model response: {response.text.strip()}")
except Exception as error:
    print(f"Gemini API request failed: {error}")