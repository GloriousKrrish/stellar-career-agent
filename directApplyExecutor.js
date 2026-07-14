import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Intercept console.log and console.error to write synchronously to stdout/stderr.
// This bypasses stream buffering and ensures the Python subprocess receives the logs instantly.
const originalLog = console.log;
const originalError = console.error;

console.log = function (...args) {
    const msg = args.join(' ');
    try {
        fs.writeSync(1, msg + '\n');
    } catch (e) {
        originalLog.apply(console, args);
    }
};

console.error = function (...args) {
    const msg = args.join(' ');
    try {
        fs.writeSync(2, msg + '\n');
    } catch (e) {
        originalError.apply(console, args);
    }
};

const jobUrl = process.argv[2];
if (!jobUrl) {
    console.error("[directApplyExecutor] Error: No job URL provided.");
    process.exit(1);
}

console.log(`[directApplyExecutor] Target URL: ${jobUrl}`);

let browser;
let page;

function findCookieFile(domain) {
    const filenames = {
        'naukri.com': 'naukri.json',
        'glassdoor.com': 'glassdoor.json',
        'glassdoor.co.in': 'glassdoor.json',
        'linkedin.com': 'linkedin.json',
        'indeed.com': 'indeed.json'
    };
    
    let targetFile = null;
    for (const [key, val] of Object.entries(filenames)) {
        if (domain.includes(key)) {
            targetFile = val;
            break;
        }
    }
    
    if (!targetFile) return null;
    
    const paths = [
        path.join(__dirname, 'stellar-backend', 'cookies', targetFile),
        path.join(__dirname, 'cookies', targetFile),
        path.join(process.cwd(), 'stellar-backend', 'cookies', targetFile),
        path.join(process.cwd(), 'cookies', targetFile)
    ];
    
    for (const p of paths) {
        if (fs.existsSync(p)) {
            return p;
        }
    }
    return null;
}

async function injectCookiesPlaywright(context, url) {
    try {
        const domain = new URL(url).hostname;
        const cookiePath = findCookieFile(domain);
        if (!cookiePath) {
            console.log(`[directApplyExecutor] No active session cookies found for domain: ${domain}`);
            return;
        }
        
        const cookiesRaw = fs.readFileSync(cookiePath, 'utf8');
        const cookies = JSON.parse(cookiesRaw);
        if (Array.isArray(cookies)) {
            const formatted = cookies.map(c => ({
                name: c.name,
                value: c.value,
                domain: c.domain || `.${domain}`,
                path: c.path || '/'
            }));
            await context.addCookies(formatted);
            console.log(`[directApplyExecutor] Injected ${formatted.length} cookies from ${path.basename(cookiePath)}`);
        }
    } catch (err) {
        console.error(`[directApplyExecutor] Cookie injection failed: ${err.message}`);
    }
}

async function injectCookiesPuppeteer(page, url) {
    try {
        const domain = new URL(url).hostname;
        const cookiePath = findCookieFile(domain);
        if (!cookiePath) {
            console.log(`[directApplyExecutor] No active session cookies found for domain: ${domain}`);
            return;
        }
        
        const cookiesRaw = fs.readFileSync(cookiePath, 'utf8');
        const cookies = JSON.parse(cookiesRaw);
        if (Array.isArray(cookies)) {
            const formatted = cookies.map(c => ({
                name: c.name,
                value: c.value,
                domain: c.domain || `.${domain}`,
                path: c.path || '/'
            }));
            await page.setCookie(...formatted);
            console.log(`[directApplyExecutor] Injected ${formatted.length} cookies from ${path.basename(cookiePath)}`);
        }
    } catch (err) {
        console.error(`[directApplyExecutor] Cookie injection failed: ${err.message}`);
    }
}

async function launchBrowser() {
    const launchPromise = (async () => {
        try {
            console.log("[directApplyExecutor] Attempting to launch Playwright...");
            const { chromium } = await import('playwright');
            const pwBrowser = await chromium.launch({
                headless: false,
                timeout: 15000,
                args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-extensions']
            });
            const context = await pwBrowser.newContext();
            await injectCookiesPlaywright(context, jobUrl);
            const pwPage = await context.newPage();
            console.log("[directApplyExecutor] Playwright initialized successfully.");
            return { browser: pwBrowser, page: pwPage, type: 'playwright' };
        } catch (pwError) {
            console.log(`[directApplyExecutor] Playwright initialization failed/skipped: ${pwError.message}`);
            console.log("[directApplyExecutor] Attempting fallback to Puppeteer...");
            
            const puppeteer = (await import('puppeteer')).default;
            const pupBrowser = await puppeteer.launch({
                headless: false,
                timeout: 15000,
                args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-extensions']
            });
            const pupPage = await pupBrowser.newPage();
            await injectCookiesPuppeteer(pupPage, jobUrl);
            console.log("[directApplyExecutor] Puppeteer initialized successfully.");
            return { browser: pupBrowser, page: pupPage, type: 'puppeteer' };
        }
    })();

    // Race with a strict 20-second global timeout
    return Promise.race([
        launchPromise,
        new Promise((_, reject) => 
            setTimeout(() => reject(new Error("Browser instantiation timed out.")), 20000)
        )
    ]);
}

async function run() {
    try {
        if (process.platform === 'win32') {
            try {
                console.log("[directApplyExecutor] Cleaning up any lingering chromium/chrome processes on Windows...");
                execSync('taskkill /F /IM chrome.exe /FI "WINDOWTITLE eq about:blank" /T 2>NUL', { stdio: 'ignore' });
                execSync('taskkill /F /IM chromium.exe /T 2>NUL', { stdio: 'ignore' });
            } catch (e) {
                // Ignore process-not-found errors
            }
        }
        
        const result = await launchBrowser();
        browser = result.browser;
        page = result.page;
    } catch (err) {
        console.error(`[directApplyExecutor] ❌ Failed: ${err.message}`);
        if (browser) {
            try {
                await browser.close();
            } catch (e) {}
        }
        process.exit(1);
    }

    try {
        console.log(`[directApplyExecutor] Navigating straight to: ${jobUrl}`);
        await page.goto(jobUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
        console.log("[directApplyExecutor] Page loaded successfully. Browser window is active.");
        console.log("[directApplyExecutor] Direct hit path successful. Complete your application manually.");
        
        // Keep browser open indefinitely for manual action
        await new Promise(() => {});
    } catch (err) {
        console.error(`[directApplyExecutor] ❌ Failed: Page navigation failed - ${err.message}`);
        if (browser) {
            try {
                await browser.close();
            } catch (e) {}
        }
        process.exit(1);
    }
}

run();
