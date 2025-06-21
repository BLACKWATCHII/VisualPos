const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
    const args = process.argv.slice(2);
    const inputPath = args[0];  
    const outputPath = args[1];

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox']
    });

    const page = await browser.newPage();
    const html = fs.readFileSync(inputPath, 'utf8');
    await page.setContent(html, { waitUntil: 'networkidle0' });

    await page.pdf({
        path: outputPath,
        format: 'A4',
        printBackground: true,
        margin: { top: '20px', bottom: '20px', left: '20px', right: '20px' }
    });

    await browser.close();
})();
