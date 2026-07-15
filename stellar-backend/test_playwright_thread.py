import asyncio
import sys
import threading
import time

def run_playwright_in_thread():
    print("[Thread] Thread started")
    
    # 1. Set event loop policy to ProactorEventLoop for this thread
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            print("[Thread] ProactorEventLoop policy set successfully")
        except Exception as e:
            print(f"[Thread] Error setting policy: {e}")
            
    # 2. Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run_automation():
        from playwright.async_api import async_playwright
        print("[Thread] Launching Playwright chromium...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
            )
            print("[Thread] Browser launched successfully!")
            page = await browser.new_page()
            await page.goto("https://example.com", timeout=15000)
            title = await page.title()
            print(f"[Thread] Page loaded. Title: '{title}'")
            await browser.close()
            print("[Thread] Browser closed cleanly.")
            
    try:
        loop.run_until_complete(run_automation())
    finally:
        loop.close()
        print("[Thread] Loop closed")

if __name__ == "__main__":
    # Simulate a main event loop that uses SelectorEventLoop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("[Main] Set main policy to SelectorEventLoopPolicy")
        
    t = threading.Thread(target=run_playwright_in_thread)
    t.start()
    t.join()
    print("[Main] Thread joined. Success!")
