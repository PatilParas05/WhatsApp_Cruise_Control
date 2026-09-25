import html
import json
import os
import tempfile
from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEED_FILE = PROJECT_ROOT / "logs" / "console_feed.jsonl"
SETTINGS_FILE = PROJECT_ROOT / "config" / "settings.json"
KILL_SWITCH_FILE = PROJECT_ROOT / "kill_switch.flag"

DEFAULT_SETTINGS = {
    "dry_run": True,
    "min_delay_seconds": 3,
    "max_delay_seconds": 12,
}

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


def load_settings():
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as file:
            settings = json.load(file)

        if not isinstance(settings, dict):
            settings = {}

    except (OSError, json.JSONDecodeError):
        settings = {}

    result = DEFAULT_SETTINGS.copy()
    result.update(settings)
    return result


def save_settings(settings):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=SETTINGS_FILE.parent,
            prefix="settings_",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            json.dump(settings, temporary_file, indent=2)
            temporary_file.write("\n")
            temporary_path = temporary_file.name

        os.replace(temporary_path, SETTINGS_FILE)

    except OSError:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
        raise


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
                st.write(f"Distance: {item.get('distance', '')}")
                st.write(
                    f"Their message: {item.get('their_message', '')}"
                )
                st.write(f"My reply: {item.get('my_reply', '')}")

    st.divider()


settings = load_settings()

if KILL_SWITCH_FILE.exists():
    st.error(
        "🛑 KILL SWITCH ACTIVE — all WhatsApp message processing is disabled."
    )

with st.sidebar:
    st.header("System controls")

    dry_run = st.toggle(
        "DRY_RUN mode",
        value=bool(settings["dry_run"]),
        help="When enabled, replies are generated but not sent.",
    )

    min_delay = st.number_input(
        "Minimum delay (seconds)",
        min_value=1,
        value=int(settings["min_delay_seconds"]),
        step=1,
    )

    max_delay = st.number_input(
        "Maximum delay (seconds)",
        min_value=1,
        value=int(settings["max_delay_seconds"]),
        step=1,
    )

    if min_delay >= max_delay:
        st.error("Minimum delay must be less than maximum delay.")
    else:
        updated_settings = settings.copy()
        updated_settings.update(
            {
                "dry_run": dry_run,
                "min_delay_seconds": min_delay,
                "max_delay_seconds": max_delay,
            }
        )

        if updated_settings != settings:
            try:
                save_settings(updated_settings)
                st.success("Settings saved.")
            except OSError as error:
                st.error(f"Could not save settings: {error}")

    st.divider()

    if KILL_SWITCH_FILE.exists():
        if st.button("Clear kill switch", use_container_width=True):
            KILL_SWITCH_FILE.unlink(missing_ok=True)
            st.rerun()
    else:
        if st.button(
            "🛑 KILL SWITCH",
            type="primary",
            use_container_width=True,
        ):
            KILL_SWITCH_FILE.touch()
            st.rerun()

    records = read_feed()

    st.divider()
    st.header("Metrics")
    st.metric("Messages processed", len(records))
    st.metric(
        "Replies sent",
        sum(
            1
            for record in records
            if record.get("decision") == "reply"
        ),
    )

records = read_feed()

st.title("WhatsApp AI Live Console")
st.caption("Updates automatically every 2 seconds.")

st.header("Live feed")

if not records:
    st.info("waiting for first message...")
else:
    for record in records:
        display_record(record)