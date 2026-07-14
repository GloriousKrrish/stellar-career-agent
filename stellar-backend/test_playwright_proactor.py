"""
Quick proof test: Playwright launch with Windows ProactorEventLoop.
Run: venv\\Scripts\\python test_playwright_proactor.py
"""
import asyncio
import sys

# Apply the exact same fix as main.py
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print("[OK] ProactorEventLoop policy set")
    except AttributeError:
        print("[INFO] Python 3.14+: ProactorEventLoop is already default")


async def test():
    from playwright.async_api import async_playwright
    print("[...] Launching Playwright chromium (headless)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
        )
        print("[OK] Browser launched!")
        page = await browser.new_page()
        await page.goto("https://example.com", timeout=15000)
        title = await page.title()
        print(f"[OK] Page loaded. Title: '{title}'")
        await browser.close()
        print("[OK] Browser closed. PLAYWRIGHT WORKS CORRECTLY UNDER PROACTOR LOOP.")


if __name__ == "__main__":
    asyncio.run(test())
