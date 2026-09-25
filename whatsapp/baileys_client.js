const fs = require("fs");
const path = require("path");

const axios = require("axios");
const qrcode = require("qrcode-terminal");
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
} = require("@whiskeysockets/baileys");

const PROJECT_ROOT = path.resolve(__dirname, "..");
const AUTH_DIR = path.join(PROJECT_ROOT, "auth_info_baileys");
const SETTINGS_FILE = path.join(PROJECT_ROOT, "config", "settings.json");
const RELATIONSHIP_MAP_FILE = path.join(
  PROJECT_ROOT,
  "config",
  "relationship_map.json"
);
const KILL_SWITCH_FILE = path.join(PROJECT_ROOT, "kill_switch.flag");
const BRIDGE_URL = "http://localhost:5001/process";

const DEFAULT_SETTINGS = {
  dry_run: true,
  min_delay_seconds: 3,
  max_delay_seconds: 12,
};

function readSettings() {
  try {
    const settings = JSON.parse(
      fs.readFileSync(SETTINGS_FILE, "utf8")
    );

    return {
      ...DEFAULT_SETTINGS,
      ...settings,
    };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

function enforceAllowlist(jid) {
  if (typeof jid !== "string" || !jid.trim()) {
    return false;
  }

  const number = jid.split("@", 1)[0].trim();

  try {
    const relationshipMap = JSON.parse(
      fs.readFileSync(RELATIONSHIP_MAP_FILE, "utf8")
    );

    return (
      Boolean(number) &&
      Object.prototype.hasOwnProperty.call(
        relationshipMap,
        number
      ) &&
      relationshipMap[number] !== "unknown"
    );
  } catch {
    return false;
  }
}

function randomDelay(minSeconds, maxSeconds) {
  const min = Number(minSeconds);
  const max = Number(maxSeconds);

  if (
    !Number.isFinite(min) ||
    !Number.isFinite(max) ||
    min < 0 ||
    max < min
  ) {
    return randomDelay(
      DEFAULT_SETTINGS.min_delay_seconds,
      DEFAULT_SETTINGS.max_delay_seconds
    );
  }

  return Math.floor(
    Math.random() * ((max - min) * 1000 + 1)
  ) + min * 1000;
}

function extractMessageData(message) {
  const content = message.message || {};
  const extended = content.extendedTextMessage;
  const mediaType = ["image", "video", "audio"].find(
    (type) => content[`${type}Message`]
  );

  let text = "";
  let messageType = "other";

  if (typeof content.conversation === "string") {
    text = content.conversation;
    messageType = "text";
  } else if (typeof extended?.text === "string") {
    text = extended.text;
    messageType = "text";
  } else if (mediaType) {
    text = content[`${mediaType}Message`].caption || "";
    messageType = mediaType;
  }

  const sourceMessage =
    extended ||
    (mediaType ? content[`${mediaType}Message`] : null) ||
    content;

  return {
    jid: message.key.remoteJid || "",
    text,
    message_type: messageType,
    is_forwarded: sourceMessage?.contextInfo?.isForwarded === true,
  };
}

async function processIncoming(sock, message) {
  const settings = readSettings();

  if (fs.existsSync(KILL_SWITCH_FILE)) {
    console.log("[KILL SWITCH] active, skipping all processing");
    return;
  }

  if (message.key?.fromMe) {
    console.log("[SKIP] own message");
    return;
  }

  const payload = extractMessageData(message);

  if (!payload.jid) {
    console.log("[SKIP] message has no remote JID");
    return;
  }

  console.log(`[ROUTE] ${payload.jid} -> bridge`);

  try {
    const response = await axios.post(BRIDGE_URL, payload);
    const result = response.data;

    console.log(
      `[DECISION] ${payload.jid}: ` +
        `${result.should_reply ? "reply" : "ignore"} — ${result.reason}`
    );

    if (
      result.should_reply !== true ||
      typeof result.reply !== "string" ||
      !result.reply.trim()
    ) {
      console.log("[REPLY] no reply generated");
      return;
    }

    const reply = result.reply.trim();

    if (settings.dry_run === true) {
      console.log(`[DRY_RUN] would reply to ${payload.jid}: ${reply}`);
      return;
    }

    const delay = randomDelay(
      settings.min_delay_seconds,
      settings.max_delay_seconds
    );

    console.log(`[SEND] waiting ${delay}ms before replying`);
    await new Promise((resolve) => setTimeout(resolve, delay));

    if (!enforceAllowlist(payload.jid)) {
      console.log("[BLOCKED] failed independent allowlist check");
      return;
    }

    await sock.sendMessage(payload.jid, { text: reply });
    console.log(`[SEND] reply sent to ${payload.jid}`);
  } catch (error) {
    console.log(
      `[ROUTE] bridge request failed: ${
        error.response?.data || error.message
      }`
    );
  }
}

async function startWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  const sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log("[ROUTE] Scan this QR code with WhatsApp:");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "open") {
      console.log("[ROUTE] WhatsApp connection established");
    }

    if (connection === "close") {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect =
        statusCode !== DisconnectReason.loggedOut;

      console.log(
        `[ROUTE] connection closed; reconnect=${shouldReconnect}`
      );

      if (shouldReconnect) {
        startWhatsApp().catch((error) => {
          console.error("[ROUTE] reconnect failed:", error);
        });
      }
    }
  });

  sock.ev.on("messages.upsert", async ({ type, messages }) => {
    if (type !== "notify") {
      console.log("[SKIP] history sync message, ignoring");
      return;
    }

    for (const message of messages || []) {
      await processIncoming(sock, message);
    }
  });
}

startWhatsApp().catch((error) => {
  console.error("[ROUTE] WhatsApp startup failed:", error);
  process.exitCode = 1;
});

const mockSock = {
  sendMessage: async (jid, message) => {
    console.log("[MOCK SEND]", jid, message);
  },
};