const path = require('path');
const fs = require('fs');
const express = require('express');
const multer = require('multer');
const QRCode = require('qrcode');

const PORT = parseInt(process.env.BAILEYS_PORT || process.env.PORT || '3030', 10);
// En Docker, si se queda en 127.0.0.1 NO es accesible desde otros contenedores ni por el port mapping.
// Mantenemos 127.0.0.1 para dev local, y 0.0.0.0 para contenedor.
const DEFAULT_HOST = fs.existsSync('/.dockerenv') ? '0.0.0.0' : '127.0.0.1';
const HOST = process.env.BAILEYS_HOST || DEFAULT_HOST;
const AUTH_DIR = process.env.BAILEYS_AUTH_DIR || path.join(__dirname, 'auth');

const FIXED_MESSAGE =
  process.env.WHATSAPP_FIXED_MESSAGE ||
  'Hola buen dia, gracias por tu compra. Adjunto factura.';

const app = express();
app.use(express.json({ limit: '15mb' }));

const upload = multer({ dest: path.join(__dirname, 'uploads') });

const state = {
  connected: false,
  connection: 'init',
  lastQr: null,
  lastQrDataUrl: null,
  lastQrAt: null,
  user: null,
  startedAt: new Date().toISOString(),
};

let sock = null;
let starting = false;

function _resetStateForLogout() {
  state.connected = false;
  state.user = null;
  state.lastQr = null;
  state.lastQrDataUrl = null;
  state.lastQrAt = null;
  state.connection = 'logged_out';
}

function _clearAuthDir() {
  try {
    if (fs.existsSync(AUTH_DIR)) {
      fs.rmSync(AUTH_DIR, { recursive: true, force: true });
    }
  } catch (e) {
    console.warn('[baileys] Could not clear auth dir:', e);
  }
  try {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  } catch {
    // ignore
  }
}

function _digitsOnly(value) {
  return String(value || '').replace(/\D/g, '');
}

function _toJid(phoneDigits) {
  const digits = _digitsOnly(phoneDigits);
  if (!digits) return null;
  if (digits.includes('@s.whatsapp.net')) return digits;
  return `${digits}@s.whatsapp.net`;
}

async function startBaileys() {
  if (starting) return;
  starting = true;

  try {
    const baileys = await import('baileys');
    const boomMod = await import('@hapi/boom');

    const makeWASocket = baileys.default;
    const { DisconnectReason, useMultiFileAuthState, fetchLatestBaileysVersion } = baileys;
    const { Boom } = boomMod;

    fs.mkdirSync(AUTH_DIR, { recursive: true });

    const { state: authState, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const { version } = await fetchLatestBaileysVersion();

    sock = makeWASocket({
      version,
      auth: authState,
      printQRInTerminal: true,
      browser: ['VisualPos', 'Chrome', '1.0.0'],
      markOnlineOnConnect: true,
      syncFullHistory: false,
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        state.lastQr = qr;
        state.lastQrAt = new Date().toISOString();
        try {
          state.lastQrDataUrl = await QRCode.toDataURL(qr);
        } catch {
          state.lastQrDataUrl = null;
        }
      }

      if (connection) {
        state.connection = connection;
      }

      if (connection === 'open') {
        state.connected = true;
        state.lastQr = null;
        state.lastQrDataUrl = null;
        state.user = sock.user || null;
      }

      if (connection === 'close') {
        state.connected = false;
        state.user = null;

        const statusCode = new Boom(lastDisconnect?.error)?.output?.statusCode;
        const loggedOut = statusCode === DisconnectReason.loggedOut;

        if (loggedOut) {
          console.error('[baileys] Logged out. Delete auth folder to relink:', AUTH_DIR);
          return;
        }

        console.warn('[baileys] Connection closed. Reconnecting in 2s...');
        setTimeout(() => {
          startBaileys().catch((e) => console.error('[baileys] Reconnect failed:', e));
        }, 2000);
      }
    });

    console.log(`[baileys] started. authDir=${AUTH_DIR}`);
  } finally {
    starting = false;
  }
}

app.get('/health', (_req, res) => {
  res.json({ ok: true, ...state });
});

app.get('/api/qr', (_req, res) => {
  res.json({
    connected: state.connected,
    connection: state.connection,
    qr_data_url: state.lastQrDataUrl,
    qr_at: state.lastQrAt,
    user: state.user,
  });
});

app.post('/api/logout', async (_req, res) => {
  try {
    if (!sock) {
      _resetStateForLogout();
      _clearAuthDir();
      startBaileys().catch((e) => console.error('[baileys] restart after logout error:', e));
      return res.json({ ok: true, message: 'Baileys not started; auth cleared.' });
    }

    const current = sock;
    sock = null;
    _resetStateForLogout();

    try {
      await current.logout();
    } catch (e) {
      console.warn('[baileys] logout error:', e);
    }

    _clearAuthDir();
    startBaileys().catch((e) => console.error('[baileys] restart after logout error:', e));
    return res.json({ ok: true, message: 'WhatsApp disconnected. Please scan QR to reconnect.' });
  } catch (e) {
    console.error('[api/logout] error:', e);
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.post('/api/send', upload.single('file'), async (req, res) => {
  try {
    if (!sock) {
      return res.status(503).json({ ok: false, error: 'Baileys not started' });
    }
    if (!state.connected) {
      return res.status(409).json({ ok: false, error: 'WhatsApp not connected (scan QR)' });
    }

    const to = req.body.to;
    const jid = _toJid(to);
    if (!jid) return res.status(400).json({ ok: false, error: 'Missing/invalid `to`' });

    const file = req.file;
    if (!file) return res.status(400).json({ ok: false, error: 'Missing file (multipart field `file`)' });

    const filename = req.body.filename || file.originalname || 'Factura.pdf';
    const mimetype = file.mimetype || 'application/pdf';

    // 1) mensaje fijo
    await sock.sendMessage(jid, { text: FIXED_MESSAGE });

    // 2) documento
    const buffer = fs.readFileSync(file.path);
    await sock.sendMessage(jid, {
      document: buffer,
      mimetype,
      fileName: filename,
    });

    return res.json({ ok: true });
  } catch (e) {
    console.error('[api/send] error:', e);
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  } finally {
    try {
      if (req.file?.path && fs.existsSync(req.file.path)) fs.unlinkSync(req.file.path);
    } catch {
      // ignore
    }
  }
});

app.listen(PORT, HOST, () => {
  console.log(`[baileys] http://${HOST}:${PORT}`);
  startBaileys().catch((e) => console.error('[baileys] start error:', e));
});
