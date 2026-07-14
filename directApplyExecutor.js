/**
 * directApplyExecutor.js
 * Standalone Node.js Playwright browser automation worker.
 * Called by the Python backend as a subprocess:
 *   node directApplyExecutor.js <job_url>
 *
 * Logs all progress to stdout so the Python parent can stream it.
 */

import { chromium } from 'playwright';

const jobUrl = process.argv[2];

if (!jobUrl) {
    console.error("❌ Error: No job URL provided. Usage: node directApplyExecutor.js <url>");
    process.exit(1);
}

(async () => {
    console.log(`⏳ STEP 1: Starting browser automation for: ${jobUrl}`);

    let browser = null;
    try {
        console.log("⏳ STEP 2: Launching headful Chromium browser...");
        browser = await chromium.launch({
            headless: false,
            slowMo: 1200,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled',
                '--start-maximized',
            ]
        });
        console.log("✅ STEP 3: Browser launched successfully!");

        console.log("⏳ STEP 4: Creating browser context with stealth settings...");
        const context = await browser.newContext({
            viewport: { width: 1366, height: 768 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale: 'en-US',
        });

        // Inject stealth overrides
        await context.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        });

        const page = await context.newPage();
        console.log("✅ STEP 4 complete: New stealth page created.");

        console.log(`⏳ STEP 5: Navigating to job URL...`);
        try {
            await page.goto(jobUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
            console.log(`✅ STEP 5: Navigated to: ${page.url()}`);
        } catch (navErr) {
            console.error(`❌ Navigation failed: ${navErr.message}`);
            await browser.close();
            process.exit(1);
        }

        // Wait for page to settle
        await page.waitForTimeout(2500);

        // Try to find and click Apply button
        console.log("⏳ STEP 6: Scanning for Apply button...");
        const applySelectors = [
            'a:has-text("Apply Now")',
            'button:has-text("Apply Now")',
            'a:has-text("Apply")',
            'button:has-text("Apply")',
            '[data-testid*="apply" i]',
            'a[class*="apply" i]',
            'button[class*="apply" i]',
        ];

        let clicked = false;
        for (const selector of applySelectors) {
            try {
                const el = page.locator(selector).first();
                if (await el.isVisible({ timeout: 2000 })) {
                    console.log(`✅ Found Apply button: ${selector}`);
                    await el.click();
                    clicked = true;
                    console.log("✅ STEP 6: Apply button clicked!");
                    break;
                }
            } catch (_) {
                // Try next selector
            }
        }

        if (!clicked) {
            console.log("⚠️ STEP 6: No Apply button found — page may require manual review.");
        }

        // Wait briefly for any dialog/form to appear
        await page.waitForTimeout(3000);

        // Take a screenshot for audit
        const screenshotPath = `./screenshots/autoapply_node_${Date.now()}.png`;
        try {
            await page.screenshot({ path: screenshotPath, fullPage: true });
            console.log(`📸 Screenshot saved: ${screenshotPath}`);
        } catch (_) {}

        console.log("⏳ STEP 7: Closing browser...");
        await browser.close();
        console.log("✅ STEP 7: Browser closed cleanly. Automation complete.");
        process.exit(0);

    } catch (err) {
        console.error("\n❌ CRITICAL ERROR CAUGHT DURING RUNTIME:");
        console.error(err.stack || err.message || String(err));
        if (browser) {
            try { await browser.close(); } catch (_) {}
        }
        process.exit(1);
    }
})();
