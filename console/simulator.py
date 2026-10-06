"""
WhatsApp AI Message Simulator

Interactive Streamlit interface to simulate incoming WhatsApp messages
and test the full pipeline (Routing, Decision Engine, ChromaDB Retrieval,
Gemini Persona Generator) without needing a real WhatsApp client or second phone.
"""

import json
import time
from pathlib import Path

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RELATIONSHIP_MAP_FILE = PROJECT_ROOT / "config" / "relationship_map.json"
BRIDGE_URL = "http://localhost:5001/process"

PRESET_MESSAGES = [
    "Hey kasa ahes?",
    "Bhai kal college la yetoys ka?",
    "Can you send me the project update?",
    "Kiti vajta yenar ahes?",
    "ok",
    "Mala ek doubt aahe Android madhe",
    "Bro send me your API key",
    "Hii",
    "Aaj raat free ahes ka gaming karuya?",
    "Can you lend me 500 rupees?",
]


def load_relationship_map():
    try:
        with RELATIONSHIP_MAP_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        data = {}

    contacts = {}
    for key, value in data.items():
        if key.startswith("_"):
            continue
        contacts[key] = value

    return contacts


def send_to_bridge(jid, text, message_type="text", is_forwarded=False):
    payload = {
        "jid": jid,
        "text": text,
        "message_type": message_type,
        "is_forwarded": is_forwarded,
        "from_me": False,
    }

    start = time.perf_counter()
    response = requests.post(BRIDGE_URL, json=payload, timeout=30)
    elapsed = time.perf_counter() - start

    response.raise_for_status()
    result = response.json()
    result["_elapsed_ms"] = round(elapsed * 1000)
    return result


# ── Streamlit page config ──────────────────────────────────────────

st.set_page_config(
    page_title="WhatsApp AI Simulator",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 WhatsApp AI Message Simulator")
st.caption(
    "Send simulated messages to the bridge without a real WhatsApp connection. "
    "The Live Console will also update in real time."
)

# ── Sidebar: contacts & presets ────────────────────────────────────

contacts = load_relationship_map()

with st.sidebar:
    st.header("Sender")

    if contacts:
        contact_options = {
            f"{number} ({rel})": number for number, rel in contacts.items()
        }
        selected_label = st.selectbox(
            "Configured contact",
            options=list(contact_options.keys()),
        )
        default_number = contact_options[selected_label]
    else:
        default_number = "1234567890"

    custom_number = st.text_input(
        "Or enter a custom number",
        placeholder="e.g. 1234567890",
    )

    sender_number = custom_number.strip() if custom_number.strip() else default_number
    sender_jid = f"{sender_number}@s.whatsapp.net"
    st.code(sender_jid, language=None)

    st.divider()
    st.header("Message options")

    message_type = st.selectbox(
        "Message type",
        options=["text", "image", "audio", "video"],
        index=0,
    )

    is_forwarded = st.checkbox("Mark as forwarded")

    st.divider()
    st.header("Quick presets")
    st.caption("Click any preset to auto-fill the message box.")


# ── Main area ──────────────────────────────────────────────────────

if "history" not in st.session_state:
    st.session_state.history = []

if "message_input" not in st.session_state:
    st.session_state.message_input = ""


def _set_preset(text):
    """Callback: write the preset into the text_area widget key."""
    st.session_state.message_input = text


# Preset buttons in sidebar
with st.sidebar:
    for preset in PRESET_MESSAGES:
        st.button(
            preset,
            key=f"preset_{preset}",
            use_container_width=True,
            on_click=_set_preset,
            args=(preset,),
        )

# Message input
col_input, col_send = st.columns([5, 1])

with col_input:
    message_text = st.text_area(
        "Message",
        key="message_input",
        height=80,
        placeholder="Type a message to simulate...",
        label_visibility="collapsed",
    )

with col_send:
    st.write("")  # vertical spacing
    send_clicked = st.button(
        "▶ Send",
        type="primary",
        use_container_width=True,
    )

# ── Send & display result ──────────────────────────────────────────

if send_clicked and message_text.strip():
    with st.spinner("Processing through pipeline..."):
        try:
            result = send_to_bridge(
                jid=sender_jid,
                text=message_text.strip(),
                message_type=message_type,
                is_forwarded=is_forwarded,
            )

            entry = {
                "sender": sender_jid,
                "message": message_text.strip(),
                "message_type": message_type,
                "is_forwarded": is_forwarded,
                "result": result,
            }

            st.session_state.history.insert(0, entry)

        except requests.ConnectionError:
            st.error(
                "❌ Cannot reach the bridge at `localhost:5001`. "
                "Make sure ChromaDB and the Flask bridge (`python -m agent.bridge`) are running."
            )
        except Exception as error:
            st.error(f"❌ Error: {error}")

elif send_clicked:
    st.warning("Please enter a message before sending.")

# ── Conversation history ───────────────────────────────────────────

if st.session_state.history:
    st.divider()
    st.header("Pipeline results")

    for index, entry in enumerate(st.session_state.history):
        result = entry["result"]
        decision = "REPLY" if result.get("should_reply") else "IGNORE"
        relationship = result.get("relationship", "unknown")
        reason = result.get("reason", "")
        reply = result.get("reply")
        elapsed = result.get("_elapsed_ms", "?")

        badge_colors = {
            "family": "green",
            "friend": "blue",
            "professional": "violet",
            "unknown": "gray",
            "group": "gray",
        }
        badge_color = badge_colors.get(relationship, "gray")

        with st.container(border=True):
            header_col1, header_col2, header_col3 = st.columns([3, 1, 1])

            with header_col1:
                st.markdown(f"**From:** `{entry['sender']}`")
            with header_col2:
                st.markdown(
                    f":{badge_color}[**{relationship.upper()}**]"
                )
            with header_col3:
                st.caption(f"⏱ {elapsed}ms")

            st.markdown(f"> 💬 {entry['message']}")

            if entry["is_forwarded"]:
                st.caption("↪ Forwarded message")
            if entry["message_type"] != "text":
                st.caption(f"📎 Type: {entry['message_type']}")

            if decision == "REPLY":
                st.success(f"✅ **{decision}** — {reason}")
            else:
                st.warning(f"🚫 **{decision}** — {reason}")

            if reply:
                st.info(f"💬 **Reply:** {reply}")
            else:
                st.caption("No reply generated.")

    if st.button("🗑 Clear history"):
        st.session_state.history = []
        st.rerun()

else:
    st.info("👆 Send a message above to see the full pipeline in action.")
