/**
 * emergencyTest.js
 * Standalone Playwright diagnostic script.
 * Run with: node emergencyTest.js
 *
 * Fully isolated — no Express, no WebSocket, no Supabase, no internal agents.
 */

import { chromium } from 'playwright';

(async () => {
    console.log("⏳ STEP 1: Starting emergency script test...");
    try {
        console.log("⏳ STEP 2: Attempting browser launch in absolute headless mode...");
        const browser = await chromium.launch({
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-zygote',
            ]
        });
        console.log("✅ STEP 3: Browser launched successfully!");

        console.log("⏳ STEP 4: Opening a fresh browser page context...");
        const page = await browser.newPage();
        console.log("✅ STEP 4 complete: New page created.");

        console.log("⏳ STEP 5: Navigating to a stable baseline site (example.com)...");
        await page.goto('https://example.com', { waitUntil: 'networkidle', timeout: 15000 });
        console.log("✅ STEP 6: Target page loaded successfully!");

        const title = await page.title();
        console.log(`🎉 SUCCESS: Page title extracted -> "${title}"`);

        console.log("⏳ STEP 7: Closing browser...");
        await browser.close();
        console.log("✅ STEP 7: Browser closed cleanly. Test PASSED.");

    } catch (err) {
        console.error("\n❌ CRITICAL ERROR CAUGHT DURING RUNTIME:");
        console.error(err.stack || err.message || err);
        process.exit(1);
    }
})();
