# 🧭 WhatsApp Cruise Control — File-by-File Build Guide

> A beginner-friendly, step-by-step guide for creating the WhatsApp Cruise Control project one file at a time.
>
> **Use this guide when you want to understand the build order, purpose of every important file, and the checkpoint to complete before moving forward.**

[⬅️ Back to the main README](README.md)

---

## 🧠 What you are building

WhatsApp Cruise Control is a local-first assistant that can:

- Read incoming WhatsApp messages through Baileys.
- Identify the sender's relationship category.
- Decide whether a message should be ignored or considered for a reply.
- Retrieve similar examples from your private conversation history.
- Generate a reply using your persona and Google Gemini.
- Preview replies safely in `DRY_RUN` mode.
- Display decisions and retrieval traces in a Streamlit console.
- Send a reply only after safety and allowlist checks pass.

The build is divided into four logical stages:

| Stage | Name | Main result |
|---|---|---|
| 1 | 🧍 Persona Brain | The assistant understands your identity and writing style |
| 2 | 🗃️ History Brain | Past messages become searchable examples |
| 3 | 🧭 Router & Safety | The system knows who to reply to and when to stop |
| 4 | 📱 Live Integration | WhatsApp, Flask, and Streamlit work together |

---

## ⚠️ Before you begin

This project automates WhatsApp Web using Baileys. Automation can violate WhatsApp's Terms of Service and may cause account restrictions or bans.

Use only:

- A dedicated secondary WhatsApp number.
- Chats and contacts where you have permission to experiment.
- `dry_run: true` during development and testing.
- Human review for money, medical, legal, emergency, or serious personal topics.

Never commit private chat exports, phone numbers, API keys, authentication data, logs, databases, or persona files.

---

## 🧰 Step 0 — Prepare your tools

Install the following before creating project files:

- Python 3.10+
- Node.js 18+
- npm
- Git
- VS Code
- A Google Gemini API key
- ChromaDB CLI

### Windows PowerShell verification

```powershell
python --version
py --version
node --version
npm --version
git --version
```

Create the project and enter it:

```powershell
git clone https://github.com/PatilParas05/WhatsApp_Cruise_Control.git
Set-Location .\WhatsApp_Cruise_Control
```

Create the Python environment:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Install the Python packages used by the current codebase:

```powershell
python -m pip install chromadb sentence-transformers google-genai python-dotenv flask streamlit streamlit-autorefresh pytest
```

Install Node.js packages:

```powershell
npm install
```

✅ **Checkpoint:** Python, Node.js, npm, Git, and the virtual environment work correctly.

---

# 🏗️ Step 1 — Create the base project structure

Create the main directories first:

```powershell
New-Item -ItemType Directory -Force agent, config, console, ingestion, persona, whatsapp, data, logs, chroma_data
New-Item -ItemType Directory -Force data\raw_export, data\processed_pairs
```

Create Python package marker files:

```powershell
New-Item -ItemType File -Force agent\__init__.py
New-Item -ItemType File -Force ingestion\__init__.py
```

Your initial structure should look like this:

```text
WhatsApp_Cruise_Control/
├── agent/
├── config/
├── console/
├── ingestion/
├── persona/
├── whatsapp/
├── data/
│   ├── raw_export/
│   └── processed_pairs/
├── logs/
└── chroma_data/
```

### Why these directories exist

| Directory | Purpose |
|---|---|
| `agent/` | Reply decisions, routing, generation, and Flask bridge |
| `config/` | Runtime settings, constants, and relationship maps |
| `console/` | Streamlit monitoring UI |
| `ingestion/` | Convert exports into searchable history |
| `persona/` | Your private writing style and persona tools |
| `whatsapp/` | Node.js Baileys integration |
| `data/` | Private raw exports and generated message pairs |
| `logs/` | Decision and console JSONL logs |
| `chroma_data/` | Local vector database files |

---

# 🧍 Week 1 — Create the Persona Brain

The Persona Brain describes **who you are**, not the exact history of a conversation.

## File 1 — `persona/persona.json`

Create this file first:

```powershell
New-Item -ItemType File -Force persona\persona.json
```

Add your private persona information:

```json
{
  "identity": "Describe yourself briefly and honestly",
  "hinglish_ratio": 0.25,
  "avg_message_length_words": 8,
  "hard_rules": [
    "Be honest",
    "Do not invent commitments",
    "Ask for human review when a topic is serious"
  ],
  "relationships": {
    "family": {
      "tone": "warm and familiar"
    },
    "friends": {
      "tone": "casual and natural"
    },
    "professional": {
      "tone": "clear and respectful"
    }
  }
}
```

### What this file does

`agent/generator.py` reads this file and adds its values to the Gemini prompt. It controls identity, tone, language habits, typical message length, and hard rules.

🔐 Keep the real file private. It is ignored by Git through `.gitignore`.

Validate it:

```powershell
python -m json.tool .\persona\persona.json
```

## File 2 — `persona/build_persona.py`

This file calculates style signals from a local WhatsApp export, including:

- Total messages analyzed.
- Hinglish ratio.
- Marathi-English ratio.
- Average message length.
- Frequently used emojis.

Run it after you have an export:

```powershell
python .\persona\build_persona.py `
  --file ".\data\raw_export\chatGau.txt" `
  --name "Your Exact Name" `
  --output ".\persona\style_signals_chatGau.json"
```

## File 3 — `persona/test_persona.py`

This test harness loads the persona, reads sample chat files, sends example messages to Gemini, and writes generated examples to `persona/sample_output.md`.

Run it only after the private persona and style-signal files exist:

```powershell
python .\persona\test_persona.py
```

✅ **Week 1 checkpoint:** The persona JSON is valid, private style data can be generated, and sample replies can be produced.

---

# 🗃️ Week 2 — Create the History Brain

The History Brain stores real examples in the form:

```text
they said X → I replied Y
```

## File 4 — `data/raw_export/`

Export your own WhatsApp chats **without media** and place the `.txt` files here:

```text
data/raw_export/
├── chatGau.txt
└── chatKru.txt
```

On Windows, inspect an export:

```powershell
Get-Content .\data\raw_export\chatGau.txt -TotalCount 20
```

Use the exact sender name shown in the export.

## File 5 — `ingestion/parse_export.py`

This parser:

- Reads WhatsApp text exports.
- Supports common export formats.
- Removes system messages and media placeholders.
- Groups consecutive messages from the same sender.
- Finds incoming-message/reply pairs.
- Writes generated JSONL files under `data/processed_pairs/`.

Run it:

```powershell
python -m ingestion.parse_export --name "Your Exact Name"
```

Expected output location:

```text
data/processed_pairs/
```

Validate the result:

```powershell
python .\ingestion\validate_pairs.py
```

## File 6 — `config/contact_relationship_map.json`

This map connects conversation IDs from exported filenames to relationship categories used during embedding.

Example:

```json
{
  "chatgau": "friend",
  "chatkru": "friend",
  "family-chat": "family",
  "work-chat": "professional"
}
```

Supported categories:

```text
family
friend
professional
unknown
```

### Important: two maps have different jobs

| File | Used for | Key format |
|---|---|---|
| `contact_relationship_map.json` | Assign historical conversations before embedding | Conversation ID from file name |
| `relationship_map.json` | Allow or reject live WhatsApp contacts | Phone number from WhatsApp JID |

Do not mix these files. They solve different problems.

## File 7 — `ingestion/embed_to_chroma.py`

This script:

1. Loads processed message pairs.
2. Loads the historical relationship map.
3. Creates ChromaDB collections.
4. Embeds incoming messages with `paraphrase-multilingual-mpnet-base-v2`.
5. Stores the original reply as metadata.

Start ChromaDB first:

```powershell
chroma run --path .\chroma_data --port 8000
```

Then create embeddings:

```powershell
python .\ingestion\embed_to_chroma.py
```

Expected collections:

```text
history_family
history_friend
history_professional
history_unknown
```

## File 8 — `ingestion/retrieval.py`

This module connects to ChromaDB and retrieves the most similar historical messages. The generator uses up to three results as examples when composing a reply.

## File 9 — `ingestion/retrieval_demo.py`

Use this file to confirm that the History Brain can retrieve similar examples:

```powershell
python -m ingestion.retrieval_demo
```

✅ **Week 2 checkpoint:** Exports are parsed, relationships are assigned, embeddings exist in ChromaDB, and retrieval returns useful examples.

---

# 🧭 Week 3 — Create Routing and Safety

## File 10 — `config/constants.py`

Store shared values such as low-signal acknowledgement words. These are used by the parser and decision engine to avoid unnecessary replies.

## File 11 — `config/settings.py`

This module provides helpers for:

- Loading `config/settings.json`.
- Checking whether dry-run mode is active.
- Checking the kill switch.
- Reading the live allowlist.
- Verifying a JID before sending.

## File 12 — `config/relationship_map.json`

Create it from the sanitized example:

```powershell
Copy-Item .\config\relationship_map_example.json .\config\relationship_map.json
```

Replace example numbers with real phone-number keys:

```json
{
  "_default": "unknown",
  "15551234567": "friend",
  "15557654321": "professional"
}
```

This file controls live routing and allowlisting. Keep it private.

Validate it:

```powershell
python .\agent\validate_relationship_map.py
```

## File 13 — `agent/router.py`

`resolve_relationship()` receives a WhatsApp JID and returns:

- The relationship category.
- The ChromaDB collection name, such as `history_friend`.

Group JIDs ending in `@g.us` are identified separately and do not use a personal history collection.

## File 14 — `agent/decision_engine.py`

`should_reply()` is the safety gate. It can ignore:

- Your own messages.
- Group messages.
- Unknown senders.
- Media-only messages.
- Forwarded content.
- Low-signal acknowledgements.
- Money, medical, legal, serious, or ambiguous messages.

If Gemini intent classification fails, the code is designed to fail closed and request human review.

## File 15 — `agent/test_router.py`

Run the router tests:

```powershell
python -m pytest .\agent\test_router.py
```

## File 16 — `agent/batch_test.py`

This script exercises several cases, including own messages, groups, unknown contacts, media, forwarded messages, acknowledgements, money-related text, and casual questions:

```powershell
python -m agent.batch_test
```

✅ **Week 3 checkpoint:** Live contacts route correctly, unsafe cases are ignored, and router tests pass.

---

# 📱 Week 4 — Create the Runtime Integration

## File 17 — `config/settings.json`

Create safe runtime defaults:

```powershell
@"
{
  "dry_run": true,
  "min_delay_seconds": 3,
  "max_delay_seconds": 12
}
"@ | Set-Content .\config\settings.json
```

Always start with `dry_run: true`.

## File 18 — `agent/generator.py`

`generate_reply()` combines:

- The incoming message.
- The relationship category.
- Your persona profile.
- Relationship-specific tone.
- Similar historical pairs.
- Gemini generation rules.

It returns one short WhatsApp-style reply without an explanation.

## File 19 — `agent/bridge.py`

The Flask bridge exposes:

```text
POST http://localhost:5001/process
```

It receives a message payload, calls the router and decision engine, retrieves examples, generates a reply when allowed, and records the result in `logs/console_feed.jsonl`.

Start it:

```powershell
python -m agent.bridge
```

## File 20 — `console/app.py`

The Streamlit console displays:

- Recent messages.
- Relationship badges.
- Reply or ignore decisions.
- Decision reasons.
- Generated replies.
- Retrieval traces.
- Runtime settings.
- Message metrics.
- Kill-switch controls.

Start it:

```powershell
python -m streamlit run .\console\app.py
```

Open:

```text
http://localhost:8501
```

## File 21 — `whatsapp/baileys_client.js`

This is the Node.js WhatsApp runtime. It:

- Connects to WhatsApp with Baileys.
- Displays a QR code during first login.
- Extracts text, media type, JID, and forwarded status.
- Sends payloads to the Flask bridge.
- Respects the kill switch.
- Logs replies during dry-run mode.
- Checks the allowlist immediately before sending.
- Waits for the configured random delay.
- Sends the reply only when all checks pass.

Start it last:

```powershell
node .\whatsapp\baileys_client.js
```

On first run, scan the terminal QR code from the dedicated secondary phone:

1. Open WhatsApp.
2. Open **Linked devices**.
3. Select **Link a device**.
4. Scan the QR code.

Authentication is stored in:

```text
auth_info_baileys/
```

Never commit this folder.

✅ **Week 4 checkpoint:** ChromaDB, Flask, Streamlit, and Baileys run in separate terminals and the system remains in dry-run mode until verified.

---

# 🔁 Final startup order

Open four PowerShell windows. Activate the virtual environment in each one.

### Window 1 — ChromaDB

```powershell
chroma run --path .\chroma_data --port 8000
```

### Window 2 — Flask bridge

```powershell
python -m agent.bridge
```

### Window 3 — Streamlit console

```powershell
python -m streamlit run .\console\app.py
```

### Window 4 — Baileys client

```powershell
node .\whatsapp\baileys_client.js
```

The safe first-run order is:

```text
DRY_RUN → inspect logs → inspect console → test routing → verify retrieval → only then consider LIVE
```

---

# 🧪 Final verification checklist

## Environment

- [ ] Python 3.10+ works.
- [ ] Node.js 18+ works.
- [ ] `.venv` is activated.
- [ ] Python packages are installed.
- [ ] Node packages are installed.
- [ ] `.env` contains `GEMINI_API_KEY`.

## Persona Brain

- [ ] `persona/persona.json` is valid JSON.
- [ ] Relationship tones are defined.
- [ ] Hard rules are present.
- [ ] Style signals are generated locally.

## History Brain

- [ ] WhatsApp exports are in `data/raw_export/`.
- [ ] The exact sender name was used.
- [ ] Processed pairs were created.
- [ ] `contact_relationship_map.json` is configured.
- [ ] ChromaDB is running on port 8000.
- [ ] Embeddings were created.
- [ ] Retrieval returns examples.

## Safety and runtime

- [ ] `relationship_map.json` contains only approved contacts.
- [ ] `config/settings.json` has `dry_run: true`.
- [ ] The Flask bridge responds on port 5001.
- [ ] The Streamlit console opens on port 8501.
- [ ] The kill switch has been tested.
- [ ] Router tests pass.
- [ ] No private files appear in `git status`.

Check before committing:

```powershell
git status
```

---

# 📁 Important files at a glance

| File | What it is responsible for |
|---|---|
| `persona/persona.json` | Your identity, tone, habits, and hard rules |
| `persona/build_persona.py` | Calculates style statistics from exports |
| `ingestion/parse_export.py` | Converts WhatsApp exports into message/reply pairs |
| `config/contact_relationship_map.json` | Categorizes historical conversations |
| `ingestion/embed_to_chroma.py` | Creates searchable vector history |
| `ingestion/retrieval.py` | Finds similar historical messages |
| `config/relationship_map.json` | Maps live phone numbers to relationships |
| `agent/router.py` | Resolves JIDs and history collections |
| `agent/decision_engine.py` | Applies reply/ignore safety rules |
| `agent/generator.py` | Creates persona-aware Gemini replies |
| `agent/bridge.py` | Connects WhatsApp payloads to the Python agent |
| `console/app.py` | Displays live decisions and controls |
| `whatsapp/baileys_client.js` | Receives and optionally sends WhatsApp messages |
| `config/settings.json` | Dry-run and delay configuration |
| `kill_switch.flag` | Emergency stop signal |

---

# 🏁 Definition of Done

The project is ready for a controlled demo when:

1. A known contact is resolved to the correct relationship.
2. Unknown contacts and groups are ignored.
3. Sensitive or ambiguous messages require human review.
4. Similar history is visible in the retrieval trace.
5. Generated replies match the persona rules.
6. Dry-run mode logs what would happen without sending.
7. The Streamlit console displays decisions and metrics.
8. The kill switch stops processing immediately.
9. Private data remains outside Git.
10. You can explain the purpose of every major file in the repository.

[⬅️ Return to the main README](README.md)
