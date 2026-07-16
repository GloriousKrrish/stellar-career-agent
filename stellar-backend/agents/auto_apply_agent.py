"""
Agent 8 — AutoApply Agent
=========================
Autonomous browser-based job application worker.

Refactored Modular Architecture:
  AutoApplyEngine -> Platform Adapter -> Playwright -> Application Executor -> Result Logger
"""
from __future__ import annotations
import asyncio
import os
import random
import uuid
from datetime import datetime
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from logger import get_logger
from models import UserProfile

log = get_logger("AutoApplyAgent")

# ── Operational Mode Configuration ───────────────────────────────────────────
FULLY_AUTONOMOUS = True

# ── Known ATS platforms that require manual intervention ──────────────────────
EXTERNAL_ATS_DOMAINS = [
    "myworkdayjobs.com", "workday.com",
    "greenhouse.io", "boards.greenhouse.io",
    "taleo.net", "oracle.com/taleo",
    "lever.co", "jobs.lever.co",
    "icims.com",
    "smartrecruiters.com",
    "bamboohr.com",
    "ashbyhq.com",
    "breezy.hr",
    "jobvite.com",
    "successfactors.com",
]

# ── Anti-bot blocker signals ──────────────────────────────────────────────────
BLOCKER_SIGNALS = [
    "captcha", "cloudflare", "robot", "verify you are human",
    "access denied", "403 forbidden", "challenge", "otp",
    "security check", "suspicious activity", "bot detection",
    "please complete the security check", "are you a human",
]

# ── Randomized viewport sizes for stealth ─────────────────────────────────────
VIEWPORT_POOL = [
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1920, "height": 1080},
    {"width": 1280, "height": 800},
    {"width": 1600, "height": 900},
]

# ── User agent rotation pool ─────────────────────────────────────────────────
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]

# ── Cookie file path for authenticated session injection ───────────────────
COOKIE_DIR = os.path.join(os.path.dirname(__file__), "..", "cookies")
os.makedirs(COOKIE_DIR, exist_ok=True)

import traceback
import sys

class TimeoutWatchdog:
    def __init__(self, logger: ResultLogger, timeout: float = 10.0):
        self.logger = logger
        self.timeout = timeout
        self.last_log_time = asyncio.get_event_loop().time()
        self.task = None
        self.current_func_getter = None

    def update_log_time(self):
        self.last_log_time = asyncio.get_event_loop().time()

    async def start(self, current_func_getter: Callable[[], str]):
        self.current_func_getter = current_func_getter
        self.task = asyncio.create_task(self._loop())

    async def _loop(self):
        try:
            while True:
                await asyncio.sleep(1.0)
                now = asyncio.get_event_loop().time()
                if now - self.last_log_time > self.timeout:
                    func_name = self.current_func_getter() if self.current_func_getter else "Unknown"
                    tb = "".join(traceback.format_stack())
                    await self.logger.log(
                        f"🚨 [WATCHDOG] Execution stalled! No log messages for {self.timeout} seconds.\n"
                        f"Current Function: '{func_name}'\n"
                        f"Stack trace:\n{tb}"
                    )
                    self.update_log_time()  # Prevent flooding
        except asyncio.CancelledError:
            pass

    def stop(self):
        if self.task:
            self.task.cancel()


async def _human_delay(min_ms: int = 800, max_ms: int = 3000) -> None:
    """Randomized delay to simulate human interaction cadence."""
    await asyncio.sleep(random.randint(min_ms, max_ms) / 1000.0)


class ResultLogger:
    """Handles step-by-step progress logging to both console and WebSocket stream."""
    def __init__(self, task_id: str, on_progress_callback: Optional[Callable] = None):
        self.task_id = task_id
        self.callback = on_progress_callback
        self.watchdog: Optional[TimeoutWatchdog] = None

    async def log(self, message: str) -> None:
        if self.watchdog:
            self.watchdog.update_log_time()
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        log.info(f"[{self.task_id[:8]}] {formatted}")
        if self.callback:
            try:
                await self.callback(formatted)
            except Exception as e:
                log.warning(f"Failed to execute on_progress callback: {e}")


class PlaywrightManager:
    """Manages the lifecycle of the native Playwright Chromium browser."""
    def __init__(self, logger: ResultLogger):
        self.logger = logger
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None

    def _kill_orphaned_browsers(self) -> None:
        """Force-kills orphaned Playwright Chromium processes to avoid memory leaks."""
        import psutil
        killed_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                name = (proc.info.get('name') or '').lower()
                exe = (proc.info.get('exe') or '').lower()
                if 'chrome' in name or 'chromium' in name or 'playwright' in name:
                    if 'ms-playwright' in exe:
                        proc.kill()
                        killed_count += 1
            except Exception:
                pass
        if killed_count > 0:
            log.info(f"Cleaned up {killed_count} lingering Playwright processes.")

    async def init_browser(self, headless: bool = False, slow_mo: int = 1500) -> tuple[Any, Any, Any]:
        await self.logger.log("🧹 Checking and cleaning lingering browser processes...")
        try:
            self._kill_orphaned_browsers()
        except Exception as e:
            log.warning(f"Lingering cleanup error: {e}")

        await self.logger.log("🔧 Initializing Playwright browser engine...")
        from playwright.async_api import async_playwright
        self.pw = await async_playwright().start()

        self.browser = await self.pw.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                "--start-maximized",
            ],
        )

        viewport = random.choice(VIEWPORT_POOL)
        user_agent = random.choice(UA_POOL)

        await self.logger.log("✅ Browser window opened — creating secure browsing context...")
        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            java_script_enabled=True,
        )

        # Inject stealth overrides
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            window.chrome = { runtime: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) =>
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters);
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'hi'] });
        """)

        self.page = await self.context.new_page()
        return self.browser, self.context, self.page

    async def cleanup(self) -> None:
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.pw:
                await self.pw.stop()
        except Exception:
            pass


class BasePlatformAdapter:
    """Base interface representing platform-specific automation adapters."""
    def __init__(self, page: Any, logger: ResultLogger, debug_mode: bool = False):
        self.page = page
        self.logger = logger
        self.debug_mode = debug_mode

    async def log_action(self, action_type: str, selector: str = "", extra: str = "") -> None:
        await self.logger.log(f"⚡ [PLAYWRIGHT ACTION] Action: {action_type} | Selector: '{selector}' | URL: {self.page.url} {extra}")

    async def _safe_await(self, coro, func_name: str, timeout: float = 15.0):
        start_time = asyncio.get_event_loop().time()
        try:
            task = asyncio.ensure_future(coro)
            try:
                return await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
            except asyncio.TimeoutError:
                url = "Unknown"
                title = "Unknown"
                playwright_state = "Disconnected/Closed"
                if self.page:
                    try:
                        url = self.page.url
                        title = await self.page.title()
                        playwright_state = f"Active (URL: {url}, Title: {title})"
                    except Exception as page_err:
                        playwright_state = f"Error querying page state: {page_err}"
                tb = "".join(traceback.format_stack())
                await self.logger.log(
                    f"⚠️ [WARNING] Await in '{func_name}' is taking longer than 5 seconds.\n"
                    f"Current URL: {url}\n"
                    f"Playwright Page State: {playwright_state}\n"
                    f"Stack Trace:\n{tb}"
                )
                remaining = max(1.0, timeout - 5.0)
                return await asyncio.wait_for(task, timeout=remaining)
        except asyncio.TimeoutError as te:
            await self.logger.log(f"❌ [TIMEOUT] Await in '{func_name}' timed out after {timeout} seconds.")
            raise te
        except Exception as e:
            raise e

    async def click_apply(self, task_id: str) -> bool:
        raise NotImplementedError()

    async def fill_form(self, task_id: str, field_map: dict[str, str]) -> int:
        raise NotImplementedError()

    async def upload_resume(self, task_id: str, resume_path: str) -> bool:
        raise NotImplementedError()

    async def submit_form(self, task_id: str) -> bool:
        raise NotImplementedError()


async def _generate_ai_answer(question: str, job_description: str, resume_text: str) -> str:
    """Generate contextual answer to a job application question using Gemini."""
    try:
        from config import get_settings
        import google.generativeai as genai
        settings = get_settings()
        if not settings.gemini_api_key:
            return ""
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
You are assisting a candidate in filling out a job application.
Generate a concise, professional, and truthful answer to the following application question.

CRITICAL INSTRUCTIONS:
1. Do NOT fabricate professional experience, degrees, certifications, or skills beyond what is explicitly stated in the candidate's resume.
2. If the answer is a yes/no, multiple choice, or numeric value, output exactly that value or select the best option.
3. Be professional and brief (1-3 sentences maximum for text questions).
4. Do NOT include any intro or outro text, only the direct answer.

Candidate Resume:
{resume_text}

Job Description / Context:
{job_description}

Question:
{question}
"""
        response = await model.generate_content_async(prompt)
        answer = response.text.strip()
        log.info(f"AI generated answer for '{question[:50]}...': {answer}")
        return answer
    except Exception as e:
        log.warning(f"AI answer generation failed: {e}")
        return ""


async def _select_ai_option(question: str, options: list[str], job_description: str, resume_text: str) -> int:
    """Choose the best index from a list of select/radio options using Gemini."""
    try:
        from config import get_settings
        import google.generativeai as genai
        import re
        
        settings = get_settings()
        if not settings.gemini_api_key:
            return 0
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        options_list = "\n".join([f"{i}: {opt}" for i, opt in enumerate(options)])
        
        prompt = f"""
You are assisting a candidate in filling out a job application.
Select the index of the option that best answers the question truthfully based on the candidate's resume.

Candidate Resume:
{resume_text}

Job Description / Context:
{job_description}

Question:
{question}

Options:
{options_list}

Return ONLY the selected option index as a single integer, with no other text.
"""
        response = await model.generate_content_async(prompt)
        clean = response.text.strip()
        match = re.search(r"\d+", clean)
        if match:
            idx = int(match.group())
            if 0 <= idx < len(options):
                return idx
        return 0
    except Exception as e:
        log.warning(f"AI option selection failed: {e}")
        return 0


class GenericAdapter(BasePlatformAdapter):
    """Heuristic-based generic form adapter supporting arbitrary web pages."""
    async def click_apply(self, task_id: str) -> bool:
        await self.logger.log("Entering GenericAdapter.click_apply")
        apply_selectors = [
            'button:has-text("Apply")',
            'a:has-text("Apply Now")',
            'button:has-text("Apply Now")',
            'a:has-text("Apply on company site")',
            'button:has-text("Apply on company site")',
            'button:has-text("Easy Apply")',
            'a:has-text("Easy Apply")',
            'input[type="submit"][value*="Apply" i]',
            'button[type="submit"]:has-text("Apply")',
            'a[class*="apply" i]',
            'button[class*="apply" i]',
            '[data-testid*="apply" i]',
            '[id*="apply" i]',
        ]
        for selector in apply_selectors:
            try:
                await self.log_action("locator", selector, "Find apply button")
                el = self.page.locator(selector).first
                is_vis = await self._safe_await(el.is_visible(), f"is_visible('{selector}')", timeout=3.0)
                if is_vis:
                    await self.logger.log(f"Found 'Apply' button matching selector: {selector}")
                    await self.log_action("click", selector, "Apply button")
                    await _human_delay(500, 1500)
                    await self._safe_await(el.click(), f"click('{selector}')", timeout=5.0)
                    await self.logger.log("Leaving GenericAdapter.click_apply (success)")
                    return True
            except Exception as e:
                log.debug(f"Selector {selector} check failed: {e}")
                continue
        await self.logger.log("Leaving GenericAdapter.click_apply (not found)")
        return False

    async def fill_form(self, task_id: str, field_map: dict[str, str], job_description: str = "", resume_text: str = "") -> int:
        await self.logger.log("Entering GenericAdapter.fill_form")
        filled_count = 0
        step = 0
        max_steps = 5
        
        while step < max_steps:
            await self.logger.log(f"📝 Filling form fields on step {step + 1}...")
            step_filled = 0
            
            # A. Text/Textarea inputs
            await self.log_action("locator", "text inputs", "Find all text input fields")
            inputs = await self._safe_await(
                self.page.query_selector_all(
                    "input[type='text'], input[type='email'], input[type='tel'], "
                    "input[type='url'], input[type='number'], textarea"
                ),
                "query_selector_all(inputs)",
                timeout=5.0
            )
            for inp in inputs:
                try:
                    is_vis = await self._safe_await(inp.is_visible(), "inp.is_visible", timeout=3.0)
                    is_dis = await self._safe_await(inp.is_disabled(), "inp.is_disabled", timeout=3.0)
                    if not is_vis or is_dis:
                        continue
                        
                    # Check if already filled
                    curr_val = await self._safe_await(inp.input_value(), "inp.input_value", timeout=3.0)
                    if curr_val and len(curr_val.strip()) > 0:
                        continue

                    # Get label text
                    label_text = ""
                    inp_id = await self._safe_await(inp.get_attribute("id"), "inp.get_attribute('id')", timeout=3.0)
                    if inp_id:
                        lbl = await self._safe_await(self.page.query_selector(f'label[for="{inp_id}"]'), "query_selector(label)", timeout=3.0)
                        if lbl:
                            label_text = await self._safe_await(lbl.inner_text(), "lbl.inner_text", timeout=3.0)
                    if not label_text:
                        placeholder = await self._safe_await(inp.get_attribute("placeholder"), "inp.get_attribute('placeholder')", timeout=3.0)
                        if placeholder:
                            label_text = placeholder
                    if not label_text:
                        aria = await self._safe_await(inp.get_attribute("aria-label"), "inp.get_attribute('aria-label')", timeout=3.0)
                        if aria:
                            label_text = aria
                            
                    label_text_lower = label_text.lower().strip()
                    matched_value = None
                    
                    # 1. Check standard fields
                    for field_key, field_val in field_map.items():
                        if field_key in label_text_lower:
                            matched_value = field_val
                            break
                            
                    # 2. If it's a custom question and we have Gemini context
                    if not matched_value and label_text and job_description and resume_text:
                        matched_value = await _generate_ai_answer(label_text, job_description, resume_text)
                        
                    if matched_value:
                        await self.log_action("click", f"input[id='{inp_id}']", f"Focus input: Label='{label_text}'")
                        await self._safe_await(inp.click(), "inp.click", timeout=4.0)
                        await _human_delay(200, 500)
                        await self._safe_await(inp.fill(""), "inp.fill", timeout=4.0)
                        await _human_delay(100, 300)
                        await self.log_action("type", f"input[id='{inp_id}']", f"Type text='{matched_value}' Label='{label_text}'")
                        await self._safe_await(inp.type(str(matched_value), delay=random.randint(30, 80)), "inp.type", timeout=8.0)
                        step_filled += 1
                        filled_count += 1
                except Exception as e:
                    log.debug(f"Error filling input: {e}")
                    continue

            # B. Select Dropdowns
            await self.log_action("locator", "select", "Find all dropdown selectors")
            selects = await self._safe_await(self.page.query_selector_all("select"), "query_selector_all(selects)", timeout=5.0)
            for sel in selects:
                try:
                    is_vis = await self._safe_await(sel.is_visible(), "sel.is_visible", timeout=3.0)
                    is_dis = await self._safe_await(sel.is_disabled(), "sel.is_disabled", timeout=3.0)
                    if not is_vis or is_dis:
                        continue
                        
                    label_text = ""
                    sel_id = await self._safe_await(sel.get_attribute("id"), "sel.get_attribute('id')", timeout=3.0)
                    if sel_id:
                        lbl = await self._safe_await(self.page.query_selector(f'label[for="{sel_id}"]'), "query_selector(label)", timeout=3.0)
                        if lbl:
                            label_text = await self._safe_await(lbl.inner_text(), "lbl.inner_text", timeout=3.0)
                    if not label_text:
                        aria = await self._safe_await(sel.get_attribute("aria-label"), "sel.get_attribute('aria-label')", timeout=3.0)
                        if aria:
                            label_text = aria
                            
                    options_elements = await self._safe_await(sel.query_selector_all("option"), "sel.query_selector_all(option)", timeout=5.0)
                    options = []
                    for opt in options_elements:
                        txt = await self._safe_await(opt.inner_text(), "opt.inner_text", timeout=3.0)
                        options.append(txt.strip() if txt else "")
                        
                    valid_options = [o for o in options if o and not any(x in o.lower() for x in ["select", "choose", "---"])]
                    if not valid_options:
                        continue
                        
                    if label_text and job_description and resume_text:
                        selected_idx = await _select_ai_option(label_text, valid_options, job_description, resume_text)
                        chosen_opt = valid_options[selected_idx]
                        for opt in options_elements:
                            opt_txt = await self._safe_await(opt.inner_text(), "opt.inner_text", timeout=3.0)
                            if opt_txt and chosen_opt in opt_txt:
                                val = await self._safe_await(opt.get_attribute("value"), "opt.get_attribute('value')", timeout=3.0)
                                if val:
                                    await self.log_action("select_option", f"select[id='{sel_id}']", f"Select='{chosen_opt}' Label='{label_text}'")
                                    await self._safe_await(sel.select_option(value=val), "sel.select_option", timeout=5.0)
                                    step_filled += 1
                                    filled_count += 1
                                    break
                except Exception as e:
                    log.debug(f"Error filling select: {e}")
                    continue

            # C. Checkboxes / Radio buttons
            await self.log_action("locator", "radio", "Find all radio input buttons")
            radios = await self._safe_await(self.page.query_selector_all("input[type='radio']"), "query_selector_all(radios)", timeout=5.0)
            radio_groups = {}
            for r in radios:
                name = await self._safe_await(r.get_attribute("name"), "r.get_attribute('name')", timeout=3.0)
                if name:
                    if name not in radio_groups:
                        radio_groups[name] = []
                    radio_groups[name].append(r)
            
            for name, r_list in radio_groups.items():
                try:
                    checked = False
                    for r in r_list:
                        is_chk = await self._safe_await(r.is_checked(), "r.is_checked", timeout=3.0)
                        if is_chk:
                            checked = True
                            break
                    if checked:
                        continue
                        
                    question_text = ""
                    parent = await self._safe_await(r_list[0].query_selector("xpath=.."), "radio.query_selector(parent)", timeout=3.0)
                    if parent:
                        question_text = await self._safe_await(parent.inner_text(), "parent.inner_text", timeout=3.0)
                        
                    options_text = []
                    for r in r_list:
                        r_id = await self._safe_await(r.get_attribute("id"), "r.get_attribute('id')", timeout=3.0)
                        lbl_text = ""
                        if r_id:
                            lbl = await self._safe_await(self.page.query_selector(f'label[for="{r_id}"]'), "query_selector(label)", timeout=3.0)
                            if lbl:
                                lbl_text = await self._safe_await(lbl.inner_text(), "lbl.inner_text", timeout=3.0)
                        if not lbl_text:
                            lbl_text = await self._safe_await(r.evaluate("el => el.nextSibling ? el.nextSibling.textContent : ''"), "r.evaluate(nextSibling)", timeout=3.0)
                        options_text.append(lbl_text.strip() if lbl_text else f"Option {r_list.index(r)}")
                        
                    if question_text and options_text and job_description and resume_text:
                        selected_idx = await _select_ai_option(question_text, options_text, job_description, resume_text)
                        target_radio = r_list[selected_idx]
                        is_vis = await self._safe_await(target_radio.is_visible(), "target_radio.is_visible", timeout=3.0)
                        is_dis = await self._safe_await(target_radio.is_disabled(), "target_radio.is_disabled", timeout=3.0)
                        if is_vis and not is_dis:
                            r_id = await self._safe_await(target_radio.get_attribute("id"), "target_radio.get_attribute('id')", timeout=3.0) or ""
                            await self.log_action("click", f"radio[id='{r_id}']", f"Select option='{options_text[selected_idx]}' for Question='{question_text}'")
                            await self._safe_await(target_radio.click(), "target_radio.click", timeout=4.0)
                            step_filled += 1
                            filled_count += 1
                except Exception as e:
                    log.debug(f"Error filling radio group: {e}")
                    continue

            # Search for Next / Continue / Proceed buttons
            next_selectors = [
                'button:has-text("Next")',
                'button:has-text("Continue")',
                'button:has-text("Save and continue")',
                'button:has-text("Save & continue")',
                'button:has-text("Proceed")',
                'input[type="button"][value*="Next" i]',
                'input[type="button"][value*="Continue" i]',
                'button[class*="next" i]',
                'button[class*="continue" i]',
                'a:has-text("Next")',
                'a:has-text("Continue")',
            ]
            next_button = None
            matched_next_sel = ""
            for sel in next_selectors:
                try:
                    await self.log_action("locator", sel, "Check next button")
                    el = self.page.locator(sel).first
                    is_vis = await self._safe_await(el.is_visible(), f"is_visible('{sel}')", timeout=2.0)
                    is_dis = await self._safe_await(el.is_disabled(), f"is_disabled('{sel}')", timeout=2.0)
                    if is_vis and not is_dis:
                        next_button = el
                        matched_next_sel = sel
                        break
                except Exception:
                    continue
                    
            if next_button:
                await self.logger.log("➡️ Clicking 'Next' / 'Continue' to advance form step...")
                await self.log_action("click", matched_next_sel, "Next/Continue button")
                await self._safe_await(next_button.click(), f"click('{matched_next_sel}')", timeout=5.0)
                await _human_delay(2000, 3500)
                step += 1
            else:
                await self.logger.log("🏁 No visible 'Next' or 'Continue' button. Assuming final step reached.")
                break
                
        await self.logger.log("Leaving GenericAdapter.fill_form")
        return filled_count

    async def upload_resume(self, task_id: str, resume_path: str) -> bool:
        await self.logger.log("Entering GenericAdapter.upload_resume")
        await self.logger.log("⏳ Waiting up to 20 seconds for resume upload input...")
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < 20.0:
            await self.log_action("locator", "file input", "Check file input elements")
            file_inputs = await self._safe_await(self.page.query_selector_all('input[type="file"]'), "query_selector_all(file_inputs)", timeout=5.0)
            for fi in file_inputs:
                try:
                    is_vis = await self._safe_await(fi.is_visible(), "fi.is_visible", timeout=3.0)
                    if is_vis:
                        fi_id = await self._safe_await(fi.get_attribute("id"), "fi.get_attribute('id')", timeout=3.0) or ""
                        await self.log_action("upload", f"input[id='{fi_id}']", f"Resume path: {resume_path}")
                        await self._safe_await(fi.set_input_files(resume_path), "fi.set_input_files", timeout=10.0)
                        await self.logger.log("✅ Resume file attached to file input field.")
                        await self.logger.log("Leaving GenericAdapter.upload_resume (success)")
                        return True
                except Exception as e:
                    log.debug(f"File upload error: {e}")
                    continue
            await asyncio.sleep(1.0)
        await self.logger.log("⚠️ Resume upload field not found or not visible after 20 seconds.")
        await self.logger.log("Leaving GenericAdapter.upload_resume (failed)")
        return False

    async def submit_form(self, task_id: str) -> bool:
        await self.logger.log("Entering GenericAdapter.submit_form")
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Submit Application")',
            'button:has-text("Send Application")',
            'button:has-text("Confirm")',
            'a:has-text("Submit")',
        ]
        for selector in submit_selectors:
            try:
                await self.log_action("locator", selector, "Find submit button")
                el = self.page.locator(selector).first
                is_vis = await self._safe_await(el.is_visible(), f"is_visible('{selector}')", timeout=2.0)
                if is_vis:
                    await self.log_action("click", selector, "Submit Form Button")
                    await _human_delay(1000, 2500)
                    await self._safe_await(el.click(), f"click('{selector}')", timeout=5.0)
                    await self.logger.log("Leaving GenericAdapter.submit_form (success)")
                    return True
            except Exception:
                continue
        await self.logger.log("Leaving GenericAdapter.submit_form (failed)")
        return False


class NaukriAdapter(GenericAdapter):
    """Naukri-specific automation adapter."""
    async def click_apply(self, task_id: str) -> bool:
        await self.logger.log("Entering NaukriAdapter.click_apply")
        naukri_selectors = [
            '.apply-button',
            'button:has-text("Apply")',
            'button.apply-button',
            'button:has-text("Apply on Company Site")',
        ]
        for selector in naukri_selectors:
            try:
                await self.log_action("locator", selector, "Find Naukri apply button")
                el = self.page.locator(selector).first
                is_vis = await self._safe_await(el.is_visible(), f"is_visible('{selector}')", timeout=3.0)
                if is_vis:
                    await self.logger.log(f"[Naukri] Clicking apply via selector: {selector}")
                    await self.log_action("click", selector, "Naukri Apply button")
                    await self._safe_await(el.click(), f"click('{selector}')", timeout=5.0)
                    await self.logger.log("Leaving NaukriAdapter.click_apply (success)")
                    return True
            except Exception as e:
                log.debug(f"[Naukri] selector check failed: {e}")
                continue
        await self.logger.log("[Naukri] Specific selectors not found, falling back to generic click_apply")
        result = await super().click_apply(task_id)
        await self.logger.log("Leaving NaukriAdapter.click_apply")
        return result


class GlassdoorAdapter(GenericAdapter):
    """Glassdoor-specific automation adapter."""
    async def click_apply(self, task_id: str) -> bool:
        glassdoor_selectors = [
            'button:has-text("Easy Apply")',
            'button[data-test="easy-apply-button"]',
            'button:has-text("Apply Now")',
        ]
        for selector in glassdoor_selectors:
            try:
                el = self.page.locator(selector).first
                if await el.is_visible(timeout=2000):
                    await self.logger.log(f"[Glassdoor] Clicking Easy Apply via selector: {selector}")
                    await el.click()
                    return True
            except Exception:
                continue
        return await super().click_apply(task_id)


class LinkedInAdapter(GenericAdapter):
    """LinkedIn-specific automation adapter."""
    async def click_apply(self, task_id: str) -> bool:
        linkedin_selectors = [
            'button.jobs-apply-button',
            'button:has-text("Easy Apply")',
            '.jobs-s-apply button',
            'button:has-text("Apply")',
        ]
        for selector in linkedin_selectors:
            try:
                el = self.page.locator(selector).first
                if await el.is_visible(timeout=2000):
                    await self.logger.log(f"[LinkedIn] Clicking Easy Apply via selector: {selector}")
                    await el.click()
                    return True
            except Exception:
                continue
        return await super().click_apply(task_id)


class IndeedAdapter(GenericAdapter):
    """Indeed-specific automation adapter."""
    async def click_apply(self, task_id: str) -> bool:
        indeed_selectors = [
            'button.indeed-apply-button',
            '#indeedApplyButton',
            'a.indeed-apply-button',
            'button:has-text("Apply Now")',
            'button:has-text("Apply")',
        ]
        for selector in indeed_selectors:
            try:
                el = self.page.locator(selector).first
                if await el.is_visible(timeout=2000):
                    await self.logger.log(f"[Indeed] Clicking Apply via selector: {selector}")
                    await el.click()
                    return True
            except Exception:
                continue
        return await super().click_apply(task_id)


class WellfoundAdapter(GenericAdapter):
    """Wellfound-specific automation adapter."""
    async def click_apply(self, task_id: str) -> bool:
        wellfound_selectors = [
            'button:has-text("Apply")',
            '.styles_applyButton__',
            'button:has-text("Quick Apply")',
            'button:has-text("Apply Now")',
        ]
        for selector in wellfound_selectors:
            try:
                el = self.page.locator(selector).first
                if await el.is_visible(timeout=2000):
                    await self.logger.log(f"[Wellfound] Clicking Apply via selector: {selector}")
                    await el.click()
                    return True
            except Exception:
                continue
        return await super().click_apply(task_id)


class PlatformAdapterFactory:
    """Selects the correct adapter based on the job URL domain."""
    @staticmethod
    def get_adapter(url: str, page: Any, logger: ResultLogger, debug_mode: bool = False) -> BasePlatformAdapter:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if "naukri.com" in domain:
            return NaukriAdapter(page, logger, debug_mode)
        elif "glassdoor.com" in domain or "glassdoor.co.in" in domain:
            return GlassdoorAdapter(page, logger, debug_mode)
        elif "linkedin.com" in domain:
            return LinkedInAdapter(page, logger, debug_mode)
        elif "indeed.com" in domain:
            return IndeedAdapter(page, logger, debug_mode)
        elif "wellfound.com" in domain:
            return WellfoundAdapter(page, logger, debug_mode)
        else:
            return GenericAdapter(page, logger, debug_mode)


class AutoApplyEngine:
    """
    Modular execution engine for AutoApply job automation.
    Integrates cookies injection, page analysis, and adapters.
    """
    def __init__(self):
        self.screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def _is_external_ats(self, url: str) -> str | None:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            for ats in EXTERNAL_ATS_DOMAINS:
                if ats in domain:
                    return ats
        except Exception:
            pass
        return None

    async def _safe_await(self, coro, func_name: str, page: Any, logger: ResultLogger, timeout: float = 15.0):
        start_time = asyncio.get_event_loop().time()
        try:
            task = asyncio.ensure_future(coro)
            try:
                return await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
            except asyncio.TimeoutError:
                url = "Unknown"
                title = "Unknown"
                playwright_state = "Disconnected/Closed"
                if page:
                    try:
                        url = page.url
                        title = await page.title()
                        playwright_state = f"Active (URL: {url}, Title: {title})"
                    except Exception as page_err:
                        playwright_state = f"Error querying page state: {page_err}"
                tb = "".join(traceback.format_stack())
                await logger.log(
                    f"⚠️ [WARNING] Await in '{func_name}' is taking longer than 5 seconds.\n"
                    f"Current URL: {url}\n"
                    f"Playwright Page State: {playwright_state}\n"
                    f"Stack Trace:\n{tb}"
                )
                remaining = max(1.0, timeout - 5.0)
                return await asyncio.wait_for(task, timeout=remaining)
        except asyncio.TimeoutError as te:
            await logger.log(f"❌ [TIMEOUT] Await in '{func_name}' timed out after {timeout} seconds.")
            raise te
        except Exception as e:
            raise e

    async def _detect_page_states(self, page: Any, logger: ResultLogger) -> str | None:
        try:
            text = (await self._safe_await(page.inner_text("body"), "page.inner_text('body')", page, logger, timeout=5.0)).lower()
        except Exception:
            return None

        if any(term in text for term in ["already applied", "you've applied", "applied on"]):
            return "already_applied"
        if any(term in text for term in ["premium required", "gold membership", "upgrade to apply"]):
            return "premium_required"
        if any(term in text for term in ["no longer accepting applications", "job has expired", "position closed"]):
            return "closed"
        if any(term in text for term in ["captcha", "cloudflare", "verify you are human", "challenge-form"]):
            return "blocked_captcha"
        if any(term in text for term in ["enter otp", "one-time password", "verification code"]):
            return "blocked_otp"

        return None

    async def _take_screenshot(self, page: Any, task_id: str) -> str:
        filename = f"autoapply_{task_id}_{uuid.uuid4().hex[:6]}.png"
        path = os.path.join(self.screenshots_dir, filename)
        try:
            # Using full_page=False to prevent infinite height scroll calculations from blocking
            await self._safe_await(page.screenshot(path=path, full_page=False), "page.screenshot", page, self.logger, timeout=5.0)
            log.info(f"Screenshot saved: {path}")
        except Exception as e:
            log.warning(f"Screenshot failed: {e}")
            path = ""
        return path

    async def _wait_for_page_render(self, page: Any, logger: ResultLogger, timeout: float = 15.0) -> None:
        """
        Waits for the page to finish rendering dynamic JavaScript content.
        Checks if visible buttons or links are present, indicating the page loader has finished.
        """
        await logger.log("⏳ Waiting for page elements to render...")
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # Check if there is any visible text or if loader spinner is gone
                buttons = await self._safe_await(page.query_selector_all("button"), "page.query_selector_all('button')", page, logger, timeout=5.0)
                anchors = await self._safe_await(page.query_selector_all("a"), "page.query_selector_all('a')", page, logger, timeout=5.0)
                
                has_visible_content = False
                for b in buttons:
                    txt = await self._safe_await(b.inner_text(), "button.inner_text", page, logger, timeout=3.0)
                    if (txt or "").strip():
                        has_visible_content = True
                        break
                if not has_visible_content:
                    for a in anchors:
                        txt = await self._safe_await(a.inner_text(), "anchor.inner_text", page, logger, timeout=3.0)
                        if (txt or "").strip():
                            has_visible_content = True
                            break
                
                if has_visible_content:
                    await logger.log("✨ Page content rendering detected.")
                    return
            except Exception:
                pass
            await asyncio.sleep(1.0)
        await logger.log("⚠️ Page render wait timed out. Content might be slow or blocked.")

    async def _perform_diagnostics(self, page: Any, logger: ResultLogger) -> None:
        """
        Dumps diagnostic information about the page elements to aid button detection.
        Prints all button text, all anchor text, and matches containing keywords.
        """
        try:
            await logger.log("🔍 Performing diagnostics scan on current page...")
            
            # Print every button text
            buttons = await self._safe_await(page.query_selector_all("button"), "page.query_selector_all('button')", page, logger, timeout=5.0)
            btn_texts = []
            for b in buttons:
                try:
                    txt = await self._safe_await(b.inner_text(), "button.inner_text", page, logger, timeout=3.0)
                    txt = (txt or "").strip().replace("\n", " ")
                    if txt:
                        btn_texts.append(txt)
                except Exception:
                    pass
            if btn_texts:
                await logger.log(f"🔘 Button elements found on page: {btn_texts}")
            else:
                await logger.log("🔘 No button elements with visible text found.")

            # Print every anchor text
            anchors = await self._safe_await(page.query_selector_all("a"), "page.query_selector_all('a')", page, logger, timeout=5.0)
            anchor_texts = []
            for a in anchors:
                try:
                    txt = await self._safe_await(a.inner_text(), "anchor.inner_text", page, logger, timeout=3.0)
                    txt = (txt or "").strip().replace("\n", " ")
                    if txt:
                        anchor_texts.append(txt)
                except Exception:
                    pass
            if anchor_texts:
                await logger.log(f"⚓ Anchor elements (links) found on page: {anchor_texts}")
            else:
                await logger.log("⚓ No anchor elements with visible text found.")

            # Print elements with key text: Apply, Easy Apply, Apply Now, Continue, Submit
            keywords = ["apply", "easy apply", "apply now", "continue", "submit"]
            matching_selectors = ["button", "a", "input[type='button']", "input[type='submit']", "div[role='button']", "span"]
            matches_found = []
            for sel in matching_selectors:
                elements = await self._safe_await(page.query_selector_all(sel), f"page.query_selector_all('{sel}')", page, logger, timeout=5.0)
                if sel == "span":
                    elements = elements[:30]  # Avoid massive loops on generic span tags
                for el in elements:
                    try:
                        txt = await self._safe_await(el.inner_text(), "el.inner_text", page, logger, timeout=2.0)
                        txt = (txt or "").strip().replace("\n", " ")
                        if txt and any(kw in txt.lower() for kw in keywords):
                            matches_found.append(f"<{sel}>: '{txt}'")
                    except Exception:
                        pass
            if matches_found:
                await logger.log(f"🔎 Keyword matches found on page: {matches_found}")
            else:
                await logger.log("🔎 No keyword matching elements found on page.")
        except Exception as e:
            await logger.log(f"⚠️ Diagnostics scan failed: {e}")

    async def _explain_missing_button_reason(self, page: Any, logger: ResultLogger) -> str:
        """
        Inspects the page to explain WHY an apply button is missing
        (e.g., login pages, search results listing pages, captchas, blocked views, etc.)
        """
        try:
            url = page.url.lower()
            text = (await page.inner_text("body")).lower()
            
            # Check if we are on a login or register page
            if "login" in url or "signin" in url or "register" in url or "signup" in url or "auth" in url:
                return "The browser is locked on an authentication/login page. Session credentials or cookies are required."
            
            # Check for Google login button only (typical for login gates)
            if "continue with google" in text and not any(kw in text for kw in ["easy apply", "apply now", "apply for this job"]):
                return "The page is a login gate prompting 'Continue with Google'. Active session cookies or credentials are required."
            
            # Check if we are stuck on a search results page
            if "search" in url or "jobs/search" in url or "jobs/browse" in url or "job-search" in url:
                return "The browser is on a job search/browse results list page instead of the specific job details page."
            
            # Check for CAPTCHA/Challenge
            if any(term in text for term in ["captcha", "cloudflare", "verify you are human", "challenge-form"]):
                return "The page is blocked by a CAPTCHA or Cloudflare security challenge."
            
            # Check for expired/closed job
            if any(term in text for term in ["no longer accepting applications", "job has expired", "position closed", "not accepting"]):
                return "The job listing has expired or is no longer accepting applications."
                
            return "No matching button text or interactive element could be located on this job page layout."
        except Exception as e:
            return f"Failed to analyze page structure: {e}"

    async def _inject_or_update_debug_overlay(self, page: Any, step_name: str) -> None:
        """Injects or updates a floating debug controller overlay in the automated browser."""
        try:
            if page.is_closed():
                return

            friendly_names = {
                "browser_launch": "1. Browser Launched",
                "job_page_opened": "2. Job Page Loaded",
                "apply_button_detection": "3. Apply Button Triggered",
                "resume_upload": "4. Resume Uploaded",
                "form_completion": "5. Form Populated",
                "review_page": "6. Form Review",
                "submit": "7. Application Submitted",
                "failure": "❌ Process Failed/Paused",
            }
            display_step = friendly_names.get(step_name, step_name.replace("_", " ").title())

            script = f"""
            (() => {{
                let overlay = document.getElementById('stellar-debug-overlay');
                if (!overlay) {{
                    overlay = document.createElement('div');
                    overlay.id = 'stellar-debug-overlay';
                    overlay.style.position = 'fixed';
                    overlay.style.bottom = '20px';
                    overlay.style.right = '20px';
                    overlay.style.zIndex = '9999999';
                    overlay.style.background = 'rgba(15, 23, 42, 0.95)';
                    overlay.style.color = '#f8fafc';
                    overlay.style.padding = '20px';
                    overlay.style.borderRadius = '16px';
                    overlay.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)';
                    overlay.style.border = '1px solid rgba(99, 102, 241, 0.3)';
                    overlay.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
                    overlay.style.width = '300px';
                    overlay.style.backdropFilter = 'blur(12px)';
                    overlay.style.transition = 'all 0.3s ease';
                    overlay.style.userSelect = 'none';

                    // Dragging support
                    let isDragging = false;
                    let offsetX, offsetY;
                    overlay.addEventListener('mousedown', (e) => {{
                        if (e.target.tagName === 'BUTTON') return;
                        isDragging = true;
                        offsetX = e.clientX - overlay.getBoundingClientRect().left;
                        offsetY = e.clientY - overlay.getBoundingClientRect().top;
                    }});
                    document.addEventListener('mousemove', (e) => {{
                        if (!isDragging) return;
                        overlay.style.bottom = 'auto';
                        overlay.style.right = 'auto';
                        overlay.style.left = (e.clientX - offsetX) + 'px';
                        overlay.style.top = (e.clientY - offsetY) + 'px';
                    }});
                    document.addEventListener('mouseup', () => isDragging = false);

                    document.body.appendChild(overlay);
                }}

                overlay.innerHTML = `
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:8px;">
                        <span style="font-weight:700; color:#818cf8; font-size:14px; letter-spacing:0.5px;">STELLAR DEBUG MODE</span>
                        <div style="width:8px; height:8px; border-radius:50%; background:#10b981; box-shadow:0 0 8px #10b981;"></div>
                    </div>
                    <div style="margin-bottom:16px;">
                        <div style="font-size:11px; color:#94a3b8; text-transform:uppercase; font-weight:600; margin-bottom:2px;">Current Step</div>
                        <div style="font-size:16px; font-weight:600; color:#f1f5f9;">{display_step}</div>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <button id="stellar-debug-continue-btn" style="width:100%; padding:10px; border-radius:8px; border:none; background:#4f46e5; color:#fff; font-weight:600; cursor:pointer; font-size:13px; transition:background 0.2s;">
                            Continue to Next Step &rarr;
                        </button>
                        <button id="stellar-debug-finish-btn" style="width:100%; padding:10px; border-radius:8px; border:1px solid rgba(239,68,68,0.5); background:rgba(239,68,68,0.1); color:#ef4444; font-weight:600; cursor:pointer; font-size:13px; transition:all 0.2s;">
                            Finish Debug Session
                        </button>
                    </div>
                    <div style="margin-top:12px; font-size:10px; color:#64748b; text-align:center;">
                        You can also control this session from the Stellar UI
                    </div>
                `;

                // Add Hover Effects
                const cBtn = document.getElementById('stellar-debug-continue-btn');
                const fBtn = document.getElementById('stellar-debug-finish-btn');
                if (cBtn) {{
                    cBtn.onmouseenter = () => cBtn.style.background = '#4338ca';
                    cBtn.onmouseleave = () => cBtn.style.background = '#4f46e5';
                    cBtn.onclick = () => {{
                        window.stellarDebugAction = 'continue';
                        cBtn.disabled = true;
                        cBtn.innerText = 'Processing...';
                    }};
                }}
                if (fBtn) {{
                    fBtn.onmouseenter = () => {{
                        fBtn.style.background = '#ef4444';
                        fBtn.style.color = '#fff';
                    }};
                    fBtn.onmouseleave = () => {{
                        fBtn.style.background = 'rgba(239,68,68,0.1)';
                        fBtn.style.color = '#ef4444';
                    }};
                    fBtn.onclick = () => {{
                        window.stellarDebugAction = 'finish';
                        fBtn.disabled = true;
                    }};
                }}
            }})();
            """
            await page.evaluate(script)
        except Exception as overlay_err:
            log.warning(f"Failed to inject debug overlay: {overlay_err}")

    async def _pause_and_screenshot(
        self,
        step_name: str,
        page: Any,
        logger: ResultLogger,
        task_id: str,
        debug_mode: bool
    ) -> None:
        if not debug_mode:
            return

        # Take screenshot with timestamp
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"debug_{step_name}_{ts}_{task_id[:8]}.png"
        path = os.path.join(self.screenshots_dir, filename)
        try:
            await page.screenshot(path=path, full_page=True)
            await logger.log(f"📸 [DEBUG] Screenshot captured: {filename} (Step: {step_name})")
        except Exception as e:
            await logger.log(f"⚠️ [DEBUG] Screenshot failed: {e}")

        # Inject/update overlay
        await self._inject_or_update_debug_overlay(page, step_name)

        await logger.log(f"⏸️ [DEBUG PAUSE] Current Step: '{step_name}'. Waiting for your action in the browser...")
        
        while True:
            # Check if page is closed/destroyed
            try:
                if page.is_closed():
                    await logger.log("🚪 [DEBUG] Browser tab was closed by user. Terminating debug session.")
                    break
            except Exception:
                await logger.log("🚪 [DEBUG] Browser was closed. Terminating debug session.")
                break

            # Check if finished from store
            import store
            if store.is_debug_session_finished(task_id):
                await logger.log("⏹️ [DEBUG] Session marked as completed/finished via UI.")
                break

            # Evaluate control action in browser page context
            try:
                action = await page.evaluate("window.stellarDebugAction")
                if action == "continue":
                    await page.evaluate("window.stellarDebugAction = null")
                    await logger.log(f"▶️ [DEBUG] Advancing past step: '{step_name}'")
                    break
                elif action == "finish":
                    await logger.log("⏹️ [DEBUG] Session terminated via overlay button.")
                    store.finish_debug_session(task_id)
                    break
            except Exception:
                # E.g. during page loads, the script environment might not be ready
                pass

            await asyncio.sleep(0.5)

    async def evaluate_job_match(
        self,
        user: UserProfile,
        job_title: str,
        job_company: str,
        job_url: str,
        resume_text: str,
        threshold: int = 70
    ) -> dict[str, Any]:
        """Evaluates the match relevance between candidate's resume and target job details using Gemini."""
        try:
            from config import get_settings
            import google.generativeai as genai
            import json
            import re
            
            settings = get_settings()
            if not settings.gemini_api_key:
                # Default match if no API key is set
                return {
                    "match_score": 85,
                    "explanation": "Simulated match evaluation (no Gemini API Key configured)",
                    "recommendation": "apply"
                }
                
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            prompt = f"""
You are an expert AI recruiting and job matching agent.
Evaluate the candidate's resume against the target job details. Determine:
1. Match Score (an integer from 0 to 100).
2. Explanation of the score.
3. Recommendation ("apply" if the Match Score is {threshold} or higher, otherwise "skip").

Candidate Details:
- Name: {user.name}
- Target Title: {user.summary}
- Skills: {', '.join(user.skills)}

Candidate Resume Text:
{resume_text}

Target Job Details:
- Title: {job_title}
- Company: {job_company}
- URL: {job_url}

Provide the response in raw JSON format with exactly three keys: "match_score", "explanation", and "recommendation".
Do not include any markdown wrappers or surrounding text.
"""
            response = await model.generate_content_async(prompt)
            clean_res = response.text.strip()
            clean_res = re.sub(r"^```json\s*", "", clean_res, flags=re.MULTILINE)
            clean_res = re.sub(r"\s*```$", "", clean_res, flags=re.MULTILINE)
            
            res_dict = json.loads(clean_res)
            return {
                "match_score": int(res_dict.get("match_score", 0)),
                "explanation": str(res_dict.get("explanation", "")),
                "recommendation": str(res_dict.get("recommendation", "skip")).strip().lower()
            }
        except Exception as e:
            log.error(f"Job match evaluation failed: {e}", exc_info=True)
            return {
                "match_score": 0,
                "explanation": f"Evaluation error: {str(e)}",
                "recommendation": "skip"
            }

    async def run(
        self,
        task_id: str,
        job_url: str,
        job_title: str,
        job_company: str,
        user: UserProfile,
        resume_path: str = "",
        on_progress: Optional[Callable] = None,
        job_description: str = "",
        resume_text: str = "",
        debug_mode: bool = False,
    ) -> dict[str, Any]:
        logger = ResultLogger(task_id, on_progress)
        
        current_func = "Initialization"
        timeline = []
        watchdog = None

        def log_timeline_entry(func_name: str, status: str):
            timeline.append((asyncio.get_event_loop().time(), func_name, status))

        def get_current_func():
            return current_func

        try:
            # Initialize and start watchdog
            watchdog = TimeoutWatchdog(logger, timeout=10.0)
            logger.watchdog = watchdog
            await watchdog.start(get_current_func)

            await logger.log(f"🚀 Initializing Headful Browser Automation...")
            await logger.log(f"Target URL: {job_url}")

            if not job_url or job_url.startswith("https://jobs.example"):
                await logger.log("⚠️ Skipped: No valid application URL available")
                await logger.log("Explanation: adapter.click_apply was never reached because the job URL was invalid or simulated.")
                return {
                    "status": "simulated",
                    "reason": "No valid application URL available",
                    "screenshot": "",
                }

            # Pre-launch external ATS detection
            ats_platform = self._is_external_ats(job_url)
            if ats_platform:
                await logger.log(f"⚠️ Redirects to external ATS platform: {ats_platform}")
                await logger.log("Explanation: adapter.click_apply was never reached because an external ATS domain was detected pre-launch.")
                return {
                    "status": "requires_manual_intervention",
                    "reason": f"Redirects to external ATS platform: {ats_platform}. Manual application required.",
                    "ats_platform": ats_platform,
                    "screenshot": "",
                }

            manager = PlaywrightManager(logger)
            browser = None
            context = None
            page = None

            async def run_internal():
                nonlocal browser, context, page, current_func
                headless_env = os.getenv("AUTOAPPLY_HEADLESS", "false").lower()
                headless_val = headless_env in ("true", "1", "yes")
                if debug_mode:
                    headless_val = False  # Debug mode must run headful
                slow_mo_val = int(os.getenv("AUTOAPPLY_SLOW_MO", "1200"))

                browser, context, page = await manager.init_browser(headless=headless_val, slow_mo=slow_mo_val)

                # Step 1: Browser Launch Pause
                await self._pause_and_screenshot("browser_launch", page, logger, task_id, debug_mode)

                # Cookie injection
                try:
                    await self._inject_cookies(context, job_url, logger)
                except Exception as e:
                    log.warning(f"Cookie injection skipped: {e}")

                # Navigation
                await logger.log(f"🔍 Navigating to: {job_url[:80]}...")
                try:
                    response = await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
                    await logger.log("✅ Navigation completed.")
                    
                    # REQUIREMENT 1: Log the current page URL for every job.
                    current_url = page.url
                    await logger.log(f"🔗 Current page URL: {current_url}")
                    
                    # Wait for dynamic JS content rendering!
                    await self._wait_for_page_render(page, logger)
                    
                    await _human_delay(2000, 4000)
                except Exception as nav_err:
                    error_detail = f"Navigation failed: {type(nav_err).__name__}: {nav_err}"
                    await logger.log(f"❌ {error_detail}")
                    await logger.log("Explanation: adapter.click_apply was never reached because page navigation failed.")
                    screenshot = await self._take_screenshot(page, task_id)
                    await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
                    return {
                        "status": "failed",
                        "reason": error_detail,
                        "screenshot": screenshot,
                    }

                # Step 2: Job Page Opened Pause
                await self._pause_and_screenshot("job_page_opened", page, logger, task_id, debug_mode)

                # Redirect ATS detection
                current_url = page.url
                await logger.log(f"🔗 Page URL after navigation/redirects: {current_url}")
                ats_platform = self._is_external_ats(current_url)
                if ats_platform:
                    await logger.log(f"⚠️ Redirected to external ATS: {ats_platform}")
                    await logger.log("Explanation: adapter.click_apply was never reached because a redirect to an external ATS was detected post-navigation.")
                    screenshot = await self._take_screenshot(page, task_id)
                    await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
                    return {
                        "status": "requires_manual_intervention",
                        "reason": f"Redirected to external ATS platform: {ats_platform}",
                        "ats_platform": ats_platform,
                        "screenshot": screenshot,
                    }

                # Detect special page states (Already Applied, Closed, Captcha, OTP)
                state = await self._detect_page_states(page, logger)
                if state:
                    screenshot = await self._take_screenshot(page, task_id)
                    if state == "already_applied":
                        await logger.log("ℹ️ Already Applied: You have already completed this application.")
                        await logger.log(f"Explanation: adapter.click_apply was never reached because page state was 'already_applied'.")
                        return {"status": "applied", "reason": "Already applied", "screenshot": screenshot}
                    elif state == "premium_required":
                        await logger.log("⚠️ Premium Required: Paid subscription required on this platform.")
                        await logger.log(f"Explanation: adapter.click_apply was never reached because page state was 'premium_required'.")
                        return {"status": "requires_manual_intervention", "reason": "Paid platform subscription required", "screenshot": screenshot}
                    elif state == "closed":
                        await logger.log("❌ Closed: Job listing is no longer accepting applications.")
                        await logger.log(f"Explanation: adapter.click_apply was never reached because page state was 'closed'.")
                        return {"status": "requires_manual_intervention", "reason": "Job listing closed", "screenshot": screenshot}
                    elif state == "blocked_captcha":
                        await logger.log("⚠️ Security Block: CAPTCHA / human verification challenge detected.")
                        await logger.log(f"Explanation: adapter.click_apply was never reached because page state was 'blocked_captcha'.")
                        await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
                        return {"status": "requires_manual_intervention", "reason": "CAPTCHA challenge detected", "screenshot": screenshot}
                    elif state == "blocked_otp":
                        await logger.log("⚠️ Security Block: OTP verification code requested.")
                        await logger.log(f"Explanation: adapter.click_apply was never reached because page state was 'blocked_otp'.")
                        await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
                        return {"status": "requires_manual_intervention", "reason": "OTP requested", "screenshot": screenshot}

                # REQUIREMENT 11: Verify that the browser is actually opening the job details page
                # instead of remaining on a search results page or an authentication page.
                current_url_lower = current_url.lower()
                is_auth_page = "login" in current_url_lower or "signin" in current_url_lower or "signup" in current_url_lower or "register" in current_url_lower or "auth" in current_url_lower
                
                is_search_page = False
                if "search" in current_url_lower or "jobs/search" in current_url_lower or "jobs/browse" in current_url_lower or "job-search" in current_url_lower:
                    has_job_id_param = any(param in current_url_lower for param in ["jobid", "job_id", "currentjobid"])
                    has_listing_path = any(path in current_url_lower for path in ["job-listings", "jobs/view", "/jobs/"])
                    if not (has_job_id_param or has_listing_path):
                        is_search_page = True
                
                if is_auth_page:
                    auth_reason = "Verification Failed: Browser is on an authentication/login page instead of job details page."
                    await logger.log(f"❌ {auth_reason}")
                    await logger.log("Explanation: adapter.click_apply was never reached because browser redirected to an authentication page.")
                    screenshot = await self._take_screenshot(page, task_id)
                    await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
                    return {
                        "status": "requires_manual_intervention",
                        "reason": auth_reason,
                        "screenshot": screenshot,
                    }
                elif is_search_page:
                    search_reason = "Verification Failed: Browser is on a job search list page instead of specific job details page."
                    await logger.log(f"❌ {search_reason}")
                    await logger.log("Explanation: adapter.click_apply was never reached because browser redirected to a search results page instead of specific job details page.")
                    screenshot = await self._take_screenshot(page, task_id)
                    await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
                    return {
                        "status": "requires_manual_intervention",
                        "reason": search_reason,
                        "screenshot": screenshot,
                    }

                # Get Adapter
                current_func = "PlatformAdapterFactory.get_adapter"
                log_timeline_entry(current_func, "started")
                await logger.log("Entering PlatformAdapterFactory.get_adapter")
                adapter = PlatformAdapterFactory.get_adapter(current_url, page, logger, debug_mode)
                await logger.log("Leaving PlatformAdapterFactory.get_adapter")
                log_timeline_entry(current_func, "completed")
                
                platform_name = adapter.__class__.__name__.replace("Adapter", "")
                await logger.log(f"🎯 Detected platform: {platform_name}")

                # REQUIREMENT 3: Before scanning, capture a screenshot.
                current_func = "_take_screenshot (pre-scan)"
                log_timeline_entry(current_func, "started")
                await logger.log("Entering _take_screenshot")
                pre_scan_screenshot = await self._take_screenshot(page, task_id)
                await logger.log("Leaving _take_screenshot")
                log_timeline_entry(current_func, "completed")
                await logger.log(f"📸 Pre-scan screenshot captured: {pre_scan_screenshot}")

                # REQUIREMENT 4, 5, 6: Print button/anchor text and keyword-containing elements.
                current_func = "_perform_diagnostics"
                log_timeline_entry(current_func, "started")
                await logger.log("Entering _perform_diagnostics")
                await self._perform_diagnostics(page, logger)
                await logger.log("Leaving _perform_diagnostics")
                log_timeline_entry(current_func, "completed")

                # Click Apply
                current_func = "adapter.click_apply"
                log_timeline_entry(current_func, "started")
                await logger.log("Entering adapter.click_apply")
                await logger.log("📋 Scanning page for Apply trigger buttons...")
                
                apply_clicked = False
                try:
                    apply_clicked = await self._safe_await(
                        adapter.click_apply(task_id),
                        "adapter.click_apply",
                        page,
                        logger,
                        timeout=15.0
                    )
                except asyncio.TimeoutError:
                    await logger.log("⏱️ Timeout: Searching for Apply button took more than 15 seconds.")
                    apply_clicked = False
                except Exception as click_err:
                    await logger.log(f"⚠️ Error while searching for Apply button: {click_err}")
                    apply_clicked = False

                await logger.log("Leaving adapter.click_apply")
                log_timeline_entry(current_func, "completed" if apply_clicked else "failed")

                if not apply_clicked:
                    why_reason = await self._explain_missing_button_reason(page, logger)
                    await logger.log(f"⚠️ Apply button detection failed: {why_reason}")
                    
                    # Highlight and print every button for manual inspection
                    if debug_mode:
                        await logger.log("🔍 [DEBUG] Highlighting all buttons on page for inspection...")
                        try:
                            buttons = await page.query_selector_all("button, a, [role='button'], input[type='button'], input[type='submit']")
                            button_details = []
                            for idx, btn in enumerate(buttons):
                                try:
                                    text = (await btn.inner_text() or "").strip().replace("\n", " ")
                                    tag = await btn.evaluate("el => el.tagName")
                                    cls = await btn.get_attribute("class") or ""
                                    if text:
                                        button_details.append(f"Button {idx+1}: <{tag}> Text: '{text}' | Class: '{cls}'")
                                        await btn.evaluate("el => el.style.border = '3px dashed red'")
                                        await btn.evaluate("el => el.style.backgroundColor = 'yellow'")
                                        await btn.evaluate("el => el.style.color = 'black'")
                                except Exception:
                                    pass
                            if button_details:
                                await logger.log("📋 Page Buttons Text Content:\n" + "\n".join(button_details))
                        except Exception as highlight_err:
                            await logger.log(f"⚠️ Failed to highlight buttons: {highlight_err}")

                    screenshot = await self._take_screenshot(page, task_id)
                    
                    try:
                        html_content = await page.content()
                        await logger.log(f"📄 Page HTML (first 3000 chars):\n{html_content[:3000]}...")
                    except Exception as html_err:
                        await logger.log(f"⚠️ Could not dump page HTML: {html_err}")

                    await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
                    return {
                        "status": "requires_manual_intervention",
                        "reason": why_reason,
                        "screenshot": screenshot,
                    }

                # Step 3: Apply Button Detection Pause
                await self._pause_and_screenshot("apply_button_detection", page, logger, task_id, debug_mode)

                await _human_delay(2000, 4000)

                # Re-check ATS redirect after Apply click
                current_url = page.url
                ats_platform = self._is_external_ats(current_url)
                if ats_platform:
                    await logger.log(f"⚠️ Apply click redirected to external ATS: {ats_platform}")
                    screenshot = await self._take_screenshot(page, task_id)
                    await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
                    return {
                        "status": "requires_manual_intervention",
                        "reason": f"Apply button redirected to external ATS: {ats_platform}",
                        "ats_platform": ats_platform,
                        "screenshot": screenshot,
                    }

                # Fill form fields
                current_func = "adapter.fill_form"
                log_timeline_entry(current_func, "started")
                await logger.log("Entering adapter.fill_form")
                await logger.log("✍️ Populating form fields from candidate profile...")
                field_map = self._build_field_map(user)
                fields_filled = await self._safe_await(
                    adapter.fill_form(task_id, field_map, job_description=job_description, resume_text=resume_text),
                    "adapter.fill_form",
                    page,
                    logger,
                    timeout=60.0
                )
                await logger.log(f"✅ Filled {fields_filled} form fields")
                await logger.log("Leaving adapter.fill_form")
                log_timeline_entry(current_func, "completed")

                # Step 5: Form Completion Pause
                await self._pause_and_screenshot("form_completion", page, logger, task_id, debug_mode)

                # Upload resume
                if resume_path and os.path.isfile(resume_path):
                    current_func = "adapter.upload_resume"
                    log_timeline_entry(current_func, "started")
                    await logger.log("Entering adapter.upload_resume")
                    await logger.log("📄 Attaching resume binary...")
                    uploaded = await self._safe_await(
                        adapter.upload_resume(task_id, resume_path),
                        "adapter.upload_resume",
                        page,
                        logger,
                        timeout=30.0
                    )
                    if uploaded:
                        await logger.log("✅ Resume file uploaded successfully")
                    else:
                        await logger.log("⚠️ Resume upload input not found or failed")
                    await logger.log("Leaving adapter.upload_resume")
                    log_timeline_entry(current_func, "completed" if uploaded else "failed")

                    # Step 4: Resume Upload Pause
                    await self._pause_and_screenshot("resume_upload", page, logger, task_id, debug_mode)

                await _human_delay(1500, 3000)

                # Take pre-submit screenshot
                screenshot = await self._take_screenshot(page, task_id)
                await logger.log("📸 Pre-submit audit screenshot captured.")

                # Step 6: Review Page Pause (right before submit click)
                await self._pause_and_screenshot("review_page", page, logger, task_id, debug_mode)

                # Submit form
                submitted = False
                if FULLY_AUTONOMOUS:
                    current_func = "adapter.submit_form"
                    log_timeline_entry(current_func, "started")
                    await logger.log("Entering adapter.submit_form")
                    await logger.log("🖱️ Form fields verified. Triggering final application submission click...")
                    submitted = await self._safe_await(
                        adapter.submit_form(task_id),
                        "adapter.submit_form",
                        page,
                        logger,
                        timeout=20.0
                    )
                    if submitted:
                        try:
                            await self._safe_await(page.wait_for_load_state("networkidle", timeout=5000), "page.wait_for_load_state", page, logger, timeout=6.0)
                        except Exception:
                            pass
                    await logger.log("Leaving adapter.submit_form")
                    log_timeline_entry(current_func, "completed" if submitted else "failed")
                else:
                    await logger.log("⏸️ Paused: Review the page in the browser window and click Submit manually.")
                    # db_update_queue_status is defined in orchestrator.py, NOT in db.py.
                    try:
                        from agents.orchestrator import db_update_queue_status
                        db_update_queue_status(task_id, "requires_manual_intervention",
                                               failure_reason="Manual submission requested — user must click Submit")
                    except Exception as db_err:
                        log.warning(f"Could not update queue status to pending_submit: {db_err}")
                    for _ in range(120):
                        if page.is_closed():
                            submitted = True
                            break
                        await asyncio.sleep(1)

                if submitted:
                    # Step 7: Submit Click Pause
                    await self._pause_and_screenshot("submit", page, logger, task_id, debug_mode)

                    await _human_delay(2000, 4000)
                    final_screenshot = await self._take_screenshot(page, task_id)
                    await logger.log(f"✅ Application successfully submitted automatically!")
                    return {
                        "status": "applied",
                        "reason": f"Successfully submitted application for {job_title} at {job_company}",
                        "fields_filled": fields_filled,
                        "screenshot": final_screenshot or screenshot,
                    }
                else:
                    await logger.log("⚠️ Form filled but submit confirmation could not be verified")
                    await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
                    return {
                        "status": "requires_manual_intervention",
                        "reason": "Form populated but submit confirmation could not be verified",
                        "fields_filled": fields_filled,
                        "screenshot": screenshot,
                    }

            timeout_val = 3600.0 if debug_mode else 90.0
            return await asyncio.wait_for(run_internal(), timeout=timeout_val)
        except asyncio.TimeoutError:
            timeout_msg = "⏱️ Timeout: Job application process exceeded maximum duration."
            await logger.log(f"❌ {timeout_msg}")
            screenshot_path = ""
            if page:
                try:
                    screenshot_path = await self._take_screenshot(page, task_id)
                    html_content = await page.content()
                    await logger.log(f"📄 Page HTML (first 3000 chars on timeout):\n{html_content[:3000]}...")
                except Exception as clean_err:
                    log.warning(f"Failed to capture state on timeout: {clean_err}")
            await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
            return {
                "status": "failed",
                "reason": timeout_msg,
                "screenshot": screenshot_path,
            }
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            error_detail = f"{type(e).__name__}: {e}"
            log.error(f"Engine Run Crash:\n{tb_str}")
            await logger.log(f"❌ Browser automation crashed: {error_detail}")

            screenshot = ""
            if page:
                try:
                    screenshot = await self._take_screenshot(page, task_id)
                except Exception:
                    pass
            await self._pause_and_screenshot("failure", page, logger, task_id, debug_mode)
            return {
                "status": "failed",
                "reason": error_detail,
                "screenshot": screenshot,
            }
        finally:
            # Stop watchdog if running
            if watchdog:
                watchdog.stop()

            # Output final execution timeline
            await logger.log("=== FINAL AUTOMATION TIMELINE ===")
            for t_time, name, status in timeline:
                dt_str = datetime.fromtimestamp(t_time).strftime("%H:%M:%S.%f")[:-3]
                await logger.log(f"[{dt_str}] {name} -> {status}")
            
            # Identify last successful and first failed/stuck function
            started_funcs = [name for _, name, status in timeline if status == "started"]
            completed_funcs = [name for _, name, status in timeline if status == "completed"]
            never_returned = [f for f in started_funcs if f not in completed_funcs]
            
            if completed_funcs:
                await logger.log(f"📋 LAST SUCCESSFUL FUNCTION: {completed_funcs[-1]}")
            else:
                await logger.log("📋 LAST SUCCESSFUL FUNCTION: None")
                
            if never_returned:
                await logger.log(f"📋 FIRST FUNCTION THAT BLOCKED / NEVER RETURNED: {never_returned[0]}")
            else:
                await logger.log("📋 FIRST FUNCTION THAT BLOCKED / NEVER RETURNED: None (all completed or exited)")

            if not debug_mode:
                if 'manager' in locals() and manager:
                    await manager.cleanup()
            else:
                await logger.log("ℹ️ [DEBUG] Browser left open for manual inspection.")
                while True:
                    try:
                        if page is None or page.is_closed():
                            break
                    except Exception:
                        break
                    
                    import store
                    if store.is_debug_session_finished(task_id):
                        break
                        
                    await asyncio.sleep(1.0)
                
                await logger.log("🧹 [DEBUG] Cleaning up debug browser instance...")
                if 'manager' in locals() and manager:
                    await manager.cleanup()

    def _build_field_map(self, user: UserProfile) -> dict[str, str]:
        exp_str = ""
        current_company = ""
        years_exp = "2"
        if user.work_history:
            last = user.work_history[0]
            exp_str = f"{last.get('title', '')} at {last.get('company', '')}"
            current_company = last.get("company", "")
            years_exp = str(max(1, len(user.work_history) * 2))

        return {
            "name": user.name,
            "full_name": user.name,
            "full name": user.name,
            "first_name": user.name.split()[0] if user.name else "",
            "first name": user.name.split()[0] if user.name else "",
            "last_name": user.name.split()[-1] if user.name and len(user.name.split()) > 1 else "",
            "last name": user.name.split()[-1] if user.name and len(user.name.split()) > 1 else "",
            "email": user.email,
            "email_address": user.email,
            "email address": user.email,
            "phone": user.phone,
            "phone_number": user.phone,
            "phone number": user.phone,
            "mobile": user.phone,
            "mobile number": user.phone,
            "contact": user.phone,
            "location": user.location,
            "city": user.location.split(",")[0].strip() if "," in user.location else user.location,
            "current location": user.location,
            "address": user.location,
            "linkedin": user.linkedin,
            "linkedin_url": user.linkedin,
            "linkedin url": user.linkedin,
            "github": user.github,
            "github_url": user.github,
            "github url": user.github,
            "portfolio": user.github or user.linkedin,
            "website": user.linkedin or user.github,
            "current_title": exp_str,
            "current title": exp_str,
            "current_company": current_company,
            "current company": current_company,
            "years_experience": years_exp,
            "years of experience": years_exp,
            "experience": years_exp,
            "total experience": years_exp,
            "skills": ", ".join(user.skills[:10]),
            "key skills": ", ".join(user.skills[:10]),
            "cover_letter": self._generate_cover_letter(user),
            "cover letter": self._generate_cover_letter(user),
            "message": self._generate_cover_letter(user),
            "additional information": self._generate_cover_letter(user),
        }

    def _generate_cover_letter(self, user: UserProfile) -> str:
        skills_str = ", ".join(user.skills[:5]) if user.skills else "relevant technologies"
        return (
            f"Dear Hiring Manager,\n\n"
            f"I am writing to express my strong interest in this position. "
            f"With hands-on experience in {skills_str}, I am confident in my ability "
            f"to contribute meaningfully to your team from day one.\n\n"
            f"My background includes {user.summary[:200] if user.summary else 'progressive experience in software development'}. "
            f"I would welcome the opportunity to discuss how my skills align with your requirements.\n\n"
            f"Best regards,\n{user.name}"
        )

    async def _inject_cookies(self, context: Any, job_url: str, logger: ResultLogger) -> None:
        import json
        from urllib.parse import urlparse

        parsed = urlparse(job_url)
        domain = parsed.netloc.lower()

        domain_map = {
            "naukri.com": "naukri.json",
            "glassdoor.com": "glassdoor.json",
            "glassdoor.co.in": "glassdoor.json",
            "linkedin.com": "linkedin.json",
            "indeed.com": "indeed.json",
        }

        cookie_file = None
        for domain_key, filename in domain_map.items():
            if domain_key in domain:
                cookie_path = os.path.join(COOKIE_DIR, filename)
                if os.path.isfile(cookie_path):
                    cookie_file = cookie_path
                break

        if not cookie_file:
            log.debug(f"No cookie file found for domain: {domain}")
            return

        try:
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            if not isinstance(cookies, list):
                log.warning(f"Cookie file {cookie_file} is not a JSON array — skipping")
                return

            playwright_cookies = []
            for c in cookies:
                if not c.get("name") or not c.get("value"):
                    continue
                cookie_obj = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", f".{domain}"),
                    "path": c.get("path", "/"),
                }
                if c.get("httpOnly") is not None:
                    cookie_obj["httpOnly"] = bool(c["httpOnly"])
                if c.get("secure") is not None:
                    cookie_obj["secure"] = bool(c["secure"])
                if c.get("sameSite"):
                    ss = str(c["sameSite"]).capitalize()
                    if ss in ("Strict", "Lax", "None"):
                        cookie_obj["sameSite"] = ss

                playwright_cookies.append(cookie_obj)

            if playwright_cookies:
                await context.add_cookies(playwright_cookies)
                await logger.log(f"🔑 Injected {len(playwright_cookies)} active session cookies for {domain} to bypass login barrier")
        except Exception as e:
            log.warning(f"Cookie injection failed for {domain}: {e}")


class AutoApplyAgent:
    """Wrapper class kept for compatibility in the multi-agent system."""
    def __init__(self):
        self.engine = AutoApplyEngine()

    async def evaluate_job_match(
        self,
        user: UserProfile,
        job_title: str,
        job_company: str,
        job_url: str,
        resume_text: str,
        threshold: int = 70
    ) -> dict[str, Any]:
        return await self.engine.evaluate_job_match(
            user=user,
            job_title=job_title,
            job_company=job_company,
            job_url=job_url,
            resume_text=resume_text,
            threshold=threshold
        )

    async def apply_to_job(
        self,
        task_id: str,
        job_url: str,
        job_title: str,
        job_company: str,
        user: UserProfile,
        resume_path: str = "",
        on_progress: Optional[Callable] = None,
        job_description: str = "",
        resume_text: str = "",
        debug_mode: bool = False,
    ) -> dict[str, Any]:
        return await self.engine.run(
            task_id=task_id,
            job_url=job_url,
            job_title=job_title,
            job_company=job_company,
            user=user,
            resume_path=resume_path,
            on_progress=on_progress,
            job_description=job_description,
            resume_text=resume_text,
            debug_mode=debug_mode,
        )
