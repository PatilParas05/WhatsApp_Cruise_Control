import html
import json
from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEED_FILE = PROJECT_ROOT / "logs" / "console_feed.jsonl"
MODE_FILE = PROJECT_ROOT / "config" / "mode.txt"

st.set_page_config(
    page_title="WhatsApp AI Console",
    page_icon="💬",
    layout="wide",
)

st_autorefresh(interval=2000, key="console_refresh")

BADGE_COLORS = {
    "family": "#198754",
    "friend": "#0d6efd",
    "professional": "#6f42c1",
    "unknown": "#6c757d",
    "group": "#6c757d",
}


def read_feed():
    if not FEED_FILE.exists():
        return []

    lines = FEED_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()

    records = []

    for line in lines[-20:]:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        records.append(record)

    return list(reversed(records))


def read_mode():
    if not MODE_FILE.exists():
        return "UNKNOWN"

    mode = MODE_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    ).strip().upper()

    return mode or "UNKNOWN"


def safe_text(value):
    return html.escape(str(value or ""))


def display_record(record):
    relationship = str(
        record.get("relationship", "unknown")
    ).lower()
    color = BADGE_COLORS.get(relationship, "#6c757d")
    decision = str(record.get("decision", "unknown")).upper()
    reason = record.get("reason", "")
    timestamp = record.get("timestamp", "")

    st.markdown(
        f"""
        <div style="margin-bottom: 4px;">
            <strong>{safe_text(timestamp)}</strong>
            <span style="
                background-color: {color};
                color: white;
                padding: 3px 9px;
                border-radius: 12px;
                margin-left: 8px;
                font-size: 0.85em;
            ">
                {safe_text(relationship)}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write(f"**Decision:** {decision} — {reason}")

    reply = record.get("reply")
    if reply:
        st.info(f"Reply: {reply}")
    else:
        st.caption("Reply: none")

    trace = record.get("retrieval_trace") or []

    with st.expander(f"Retrieval trace ({len(trace)} results)"):
        if not trace:
            st.caption("No similar past pairs used.")
        else:
            for index, item in enumerate(trace, 1):
                st.markdown(f"**Result {index}**")
                st.write(
                    f"Distance: {item.get('distance', '')}"
                )
                st.write(
                    f"Their message: "
                    f"{item.get('their_message', '')}"
                )
                st.write(
                    f"My reply: {item.get('my_reply', '')}"
                )

    st.divider()


records = read_feed()
mode = read_mode()

st.title("WhatsApp AI Live Console")
st.caption("Updates automatically every 2 seconds.")

with st.sidebar:
    st.header("System status")
    st.metric("Mode", mode)

    total_messages = len(records)
    total_replies = sum(
        1
        for record in records
        if record.get("decision") == "reply"
    )

    st.metric("Messages processed", total_messages)
    st.metric("Replies sent", total_replies)

st.header("Live feed")

if not records:
    st.info("waiting for first message...")
else:
    for record in records:
        display_record(record)