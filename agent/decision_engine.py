import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from config.constants import ONE_WORD_ACKS


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
DECISION_LOG = LOG_DIR / "decision_log.jsonl"

VALID_LABELS = {
    "safe_to_auto_reply",
    "needs_human_money_or_serious",
}

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

load_dotenv(PROJECT_ROOT / ".env")
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _log_decision(message, relationship, decision, reason):
    os.makedirs(LOG_DIR, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": str(message.get("text", "")),
        "relationship": relationship,
        "decision": decision,
        "reason": reason,
    }

    with DECISION_LOG.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def _ignore(message, relationship, reason):
    _log_decision(message, relationship, "ignore", reason)
    return False, reason


def _reply(message, relationship):
    reason = "passed all gates"
    _log_decision(message, relationship, "reply", reason)
    return True, reason


def _normalized_ack(text):
    text = text.strip().casefold()
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return text.strip()


def _classify_intent(text):
    prompt = f"""
Classify the following incoming WhatsApp message as exactly one label:

safe_to_auto_reply
needs_human_money_or_serious

Use needs_human_money_or_serious for anything involving money, payments,
loans, medical matters, legal matters, serious personal matters, or genuine
ambiguity.

Return exactly one label and nothing else.

Message:
{text}
"""

    try:
        response = _client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )
        raw_response = (response.text or "").strip()
    except Exception as error:
        logger.warning("Intent classification failed: %s", error)
        return "needs_human_money_or_serious"

    if raw_response in VALID_LABELS:
        return raw_response

    logger.warning(
        "Unexpected intent response; failing closed. Raw response: %r",
        raw_response,
    )
    return "needs_human_money_or_serious"


def should_reply(
    message: dict,
    relationship: str,
) -> tuple[bool, str]:
    """Apply reply-safety gates and log the resulting decision."""

    text = str(message.get("text", ""))
    message_type = message.get("message_type", "")

    if message.get("from_me") is True:
        return _ignore(message, relationship, "own message")

    if relationship == "group":
        return _ignore(
            message,
            relationship,
            "group chat, not allowlisted",
        )

    if relationship == "unknown":
        return _ignore(
            message,
            relationship,
            "sender not in allowlist",
        )

    if (
        message_type in {"image", "audio", "video"}
        and not text.strip()
    ):
        # Session 4.1 will upgrade this into a contextual rule-based
        # acknowledgement. For now, ignoring media-only messages is correct.
        return _ignore(
            message,
            relationship,
            "media-only, no text to ground a reply",
        )

    if message.get("is_forwarded") is True:
        return _ignore(
            message,
            relationship,
            "forwarded content, not a real question",
        )

    if _normalized_ack(text) in ONE_WORD_ACKS:
        return _ignore(
            message,
            relationship,
            "low-signal ack, no reply needed",
        )

    intent = _classify_intent(text)

    if intent != "safe_to_auto_reply":
        return _ignore(
            message,
            relationship,
            "needs human review",
        )

    return _reply(message, relationship)