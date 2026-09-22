const path = require("path");

const axios = require("axios");
const qrcode = require("qrcode-terminal");
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
} = require("@whiskeysockets/baileys");

// flip to false only for controlled testing against a known consenting contact — Session 4.2 replaces this with a proper toggle.
const DRY_RUN = true;

const AUTH_DIR = path.resolve(process.cwd(), "auth_info_baileys");
const BRIDGE_URL = "http://localhost:5001/process";


function randomDelay() {
  return Math.floor(Math.random() * 5000) + 3000;
}


function getMessageContent(message) {
  return message.message || {};
}


function extractMessageData(message) {
  const content = getMessageContent(message);
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

  const isForwarded =
    sourceMessage?.contextInfo?.isForwarded === true;

  return {
    jid: message.key.remoteJid || "",
    text,
    message_type: messageType,
    is_forwarded: isForwarded,
  };
}


async function processIncoming(sock, message) {
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

    if (DRY_RUN) {
      console.log(`[DRY_RUN] would reply to ${payload.jid}: ${reply}`);
      return;
    }

    const delay = randomDelay();
    console.log(`[SEND] waiting ${delay}ms before replying`);

    await new Promise((resolve) => setTimeout(resolve, delay));

    await sock.sendMessage(payload.jid, { text: reply });
    console.log(`[SEND] reply sent to ${payload.jid}`);
  } catch (error) {
    console.log(
      `[DECISION] bridge request failed: ${
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
      const statusCode =
        lastDisconnect?.error?.output?.statusCode;

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