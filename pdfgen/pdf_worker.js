// Worker persistente de PDF.
//
// Mantiene UN Chromium abierto y atiende trabajos por stdin (una línea JSON por
// trabajo) para no pagar ~2 s de arranque de Node + Chromium en cada descarga.
//
// Entrada  (stdin):  {"id": "abc", "html": "/ruta/archivo.html", "out": "/ruta/archivo.pdf"}
// Salida  (stdout):  {"id": "abc", "ok": true}  |  {"id": "abc", "ok": false, "error": "..."}
//
// Usa las mismas opciones de PDF que generate_pdf.js (el script de un solo uso,
// que se mantiene como respaldo).
const puppeteer = require('puppeteer');
const fs = require('fs');
const readline = require('readline');

const LAUNCH_ARGS = ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'];
const PDF_OPTIONS = {
    format: 'A4',
    printBackground: true,
    margin: { top: '20px', bottom: '20px', left: '20px', right: '20px' },
};

let browserPromise = null;

function getBrowser() {
    if (!browserPromise) {
        browserPromise = puppeteer.launch({ headless: true, args: LAUNCH_ARGS }).then((browser) => {
            // Si Chromium se cae, el siguiente trabajo lo vuelve a abrir
            browser.on('disconnected', () => { browserPromise = null; });
            return browser;
        }).catch((err) => { browserPromise = null; throw err; });
    }
    return browserPromise;
}

function reply(obj) {
    process.stdout.write(JSON.stringify(obj) + '\n');
}

async function handle(job) {
    let page;
    try {
        const browser = await getBrowser();
        page = await browser.newPage();
        const html = fs.readFileSync(job.html, 'utf8');
        await page.setContent(html, { waitUntil: 'load', timeout: 30000 });
        await page.pdf({ path: job.out, ...PDF_OPTIONS });
        reply({ id: job.id, ok: true });
    } catch (err) {
        reply({ id: job.id, ok: false, error: String((err && err.stack) || err) });
    } finally {
        if (page) { page.close().catch(() => {}); }
    }
}

// Calentar el navegador apenas arranca el worker
getBrowser().then(() => reply({ id: '__ready__', ok: true })).catch((err) => reply({ id: '__ready__', ok: false, error: String(err) }));

const rl = readline.createInterface({ input: process.stdin });
rl.on('line', (line) => {
    line = line.trim();
    if (!line) return;
    let job;
    try { job = JSON.parse(line); } catch (e) { return reply({ id: null, ok: false, error: 'JSON inválido' }); }
    handle(job);
});
// Si Django se cierra (stdin cerrado), cerrar Chromium y salir
rl.on('close', async () => {
    try { const b = await browserPromise; if (b) await b.close(); } catch (e) { /* nada */ }
    process.exit(0);
});
