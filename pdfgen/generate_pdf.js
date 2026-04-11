const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
    const args = process.argv.slice(2);
    const inputPath = args[0];
    const outputPath = args[1];

    const browser = await puppeteer.launch({
        headless: true,
        args: [
            '--no-sandbox', 
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',  // Mejora rendimiento en Linux
            '--disable-gpu',             // Mejora rendimiento general
        ],
    });

    const page = await browser.newPage();
    const html = fs.readFileSync(inputPath, 'utf8');
    // Usar 'load' en lugar de 'networkidle0' para ser más rápido
    await page.setContent(html, { waitUntil: 'load' });

    await page.pdf({
        path: outputPath,
        format: 'A4',
        printBackground: true,
        margin: { top: '20px', bottom: '20px', left: '20px', right: '20px' },
    });

    await browser.close();
})();
