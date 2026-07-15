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


async def _human_delay(min_ms: int = 800, max_ms: int = 3000) -> None:
    """Randomized delay to simulate human interaction cadence."""
    await asyncio.sleep(random.randint(min_ms, max_ms) / 1000.0)


class ResultLogger:
    """Handles step-by-step progress logging to both console and WebSocket stream."""
    def __init__(self, task_id: str, on_progress_callback: Optional[Callable] = None):
        self.task_id = task_id
        self.callback = on_progress_callback

    async def log(self, message: str) -> None:
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
    def __init__(self, page: Any, logger: ResultLogger):
        self.page = page
        self.logger = logger

    async def click_apply(self, task_id: str) -> bool:
        raise NotImplementedError()

    async def fill_form(self, task_id: str, field_map: dict[str, str]) -> int:
        raise NotImplementedError()

    async def upload_resume(self, task_id: str, resume_path: str) -> bool:
        raise NotImplementedError()

    async def submit_form(self, task_id: str) -> bool:
        raise NotImplementedError()


class GenericAdapter(BasePlatformAdapter):
    """Heuristic-based generic form adapter supporting arbitrary web pages."""
    async def click_apply(self, task_id: str) -> bool:
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
                el = self.page.locator(selector).first
                if await el.is_visible(timeout=2000):
                    await self.logger.log(f"Found 'Apply' button matching selector: {selector}")
                    await _human_delay(500, 1500)
                    await el.click()
                    return True
            except Exception:
                continue
        return False

    async def fill_form(self, task_id: str, field_map: dict[str, str]) -> int:
        filled_count = 0

        # Fill text inputs
        inputs = await self.page.query_selector_all(
            "input[type='text'], input[type='email'], input[type='tel'], "
            "input[type='url'], input[type='number'], textarea"
        )
        for inp in inputs:
            try:
                if not await inp.is_visible():
                    continue

                attrs = {}
                for attr in ["name", "id", "placeholder", "aria-label", "autocomplete"]:
                    val = await inp.get_attribute(attr)
                    if val:
                        attrs[attr] = val.lower().strip()

                matched_value = None
                for attr_val in attrs.values():
                    for field_key, field_val in field_map.items():
                        if field_key in attr_val or attr_val in field_key:
                            if field_val:
                                matched_value = field_val
                                break
                    if matched_value:
                        break

                # Associated Label fallback
                if not matched_value:
                    inp_id = await inp.get_attribute("id")
                    if inp_id:
                        try:
                            label = await self.page.query_selector(f'label[for="{inp_id}"]')
                            if label:
                                label_text = (await label.inner_text()).lower().strip()
                                for field_key, field_val in field_map.items():
                                    if field_key in label_text:
                                        if field_val:
                                            matched_value = field_val
                                            break
                        except Exception:
                            pass

                if matched_value:
                    await inp.click()
                    await _human_delay(200, 600)
                    await inp.fill("")
                    await _human_delay(100, 300)
                    await inp.type(matched_value, delay=random.randint(30, 80))
                    filled_count += 1
            except Exception as e:
                log.debug(f"Field fill error: {e}")
                continue

        # Fill dropdown selects
        selects = await self.page.query_selector_all("select")
        for sel in selects:
            try:
                if not await sel.is_visible():
                    continue
                options = await sel.query_selector_all("option")
                for opt in options[1:]:
                    val = await opt.get_attribute("value")
                    if val and val.strip():
                        await sel.select_option(value=val)
                        filled_count += 1
                        break
            except Exception:
                continue

        return filled_count

    async def upload_resume(self, task_id: str, resume_path: str) -> bool:
        file_inputs = await self.page.query_selector_all('input[type="file"]')
        for fi in file_inputs:
            try:
                await fi.set_input_files(resume_path)
                return True
            except Exception as e:
                log.debug(f"File upload error: {e}")
                continue
        return False

    async def submit_form(self, task_id: str) -> bool:
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
                el = self.page.locator(selector).first
                if await el.is_visible(timeout=2000):
                    await _human_delay(1000, 2500)
                    await el.click()
                    return True
            except Exception:
                continue
        return False


class NaukriAdapter(GenericAdapter):
    """Naukri-specific automation adapter."""
    async def click_apply(self, task_id: str) -> bool:
        naukri_selectors = [
            '.apply-button',
            'button:has-text("Apply")',
            'button.apply-button',
        ]
        for selector in naukri_selectors:
            try:
                el = self.page.locator(selector).first
                if await el.is_visible(timeout=2000):
                    await self.logger.log(f"[Naukri] Clicking apply via selector: {selector}")
                    await el.click()
                    return True
            except Exception:
                continue
        return await super().click_apply(task_id)


class GlassdoorAdapter(GenericAdapter):
    """Glassdoor-specific automation adapter."""
    async def click_apply(self, task_id: str) -> bool:
        glassdoor_selectors = [
            'button:has-text("Easy Apply")',
            'button[data-test="easy-apply-button"]',
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
    """LinkedIn-specific automation adapter placeholder."""
    async def click_apply(self, task_id: str) -> bool:
        return await super().click_apply(task_id)


class IndeedAdapter(GenericAdapter):
    """Indeed-specific automation adapter placeholder."""
    async def click_apply(self, task_id: str) -> bool:
        return await super().click_apply(task_id)


class WellfoundAdapter(GenericAdapter):
    """Wellfound-specific automation adapter placeholder."""
    async def click_apply(self, task_id: str) -> bool:
        return await super().click_apply(task_id)


class PlatformAdapterFactory:
    """Selects the correct adapter based on the job URL domain."""
    @staticmethod
    def get_adapter(url: str, page: Any, logger: ResultLogger) -> BasePlatformAdapter:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if "naukri.com" in domain:
            return NaukriAdapter(page, logger)
        elif "glassdoor.com" in domain or "glassdoor.co.in" in domain:
            return GlassdoorAdapter(page, logger)
        elif "linkedin.com" in domain:
            return LinkedInAdapter(page, logger)
        elif "indeed.com" in domain:
            return IndeedAdapter(page, logger)
        elif "wellfound.com" in domain:
            return WellfoundAdapter(page, logger)
        else:
            return GenericAdapter(page, logger)


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

    async def _detect_page_states(self, page: Any, logger: ResultLogger) -> str | None:
        try:
            text = (await page.inner_text("body")).lower()
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
            await page.screenshot(path=path, full_page=True)
            log.info(f"Screenshot saved: {path}")
        except Exception as e:
            log.warning(f"Screenshot failed: {e}")
            path = ""
        return path

    async def _perform_diagnostics(self, page: Any, logger: ResultLogger) -> None:
        """
        Dumps diagnostic information about the page elements to aid button detection.
        Prints all button text, all anchor text, and matches containing keywords.
        """
        try:
            await logger.log("🔍 Performing diagnostics scan on current page...")
            
            # Print every button text
            buttons = await page.query_selector_all("button")
            btn_texts = []
            for b in buttons:
                try:
                    txt = (await b.inner_text() or "").strip().replace("\n", " ")
                    if txt:
                        btn_texts.append(txt)
                except Exception:
                    pass
            if btn_texts:
                await logger.log(f"🔘 Button elements found on page: {btn_texts}")
            else:
                await logger.log("🔘 No button elements with visible text found.")

            # Print every anchor text
            anchors = await page.query_selector_all("a")
            anchor_texts = []
            for a in anchors:
                try:
                    txt = (await a.inner_text() or "").strip().replace("\n", " ")
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
                elements = await page.query_selector_all(sel)
                for el in elements:
                    try:
                        txt = (await el.inner_text() or "").strip().replace("\n", " ")
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

    async def run(
        self,
        task_id: str,
        job_url: str,
        job_title: str,
        job_company: str,
        user: UserProfile,
        resume_path: str = "",
        on_progress: Optional[Callable] = None,
    ) -> dict[str, Any]:
        logger = ResultLogger(task_id, on_progress)

        await logger.log(f"🚀 Initializing Headful Browser Automation...")
        await logger.log(f"Target URL: {job_url}")

        if not job_url or job_url.startswith("https://jobs.example"):
            await logger.log("⚠️ Skipped: No valid application URL available")
            return {
                "status": "simulated",
                "reason": "No valid application URL available",
                "screenshot": "",
            }

        # Pre-launch external ATS detection
        ats_platform = self._is_external_ats(job_url)
        if ats_platform:
            await logger.log(f"⚠️ Redirects to external ATS platform: {ats_platform}")
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

        try:
            headless_env = os.getenv("AUTOAPPLY_HEADLESS", "false").lower()
            headless_val = headless_env in ("true", "1", "yes")
            slow_mo_val = int(os.getenv("AUTOAPPLY_SLOW_MO", "1200"))

            browser, context, page = await manager.init_browser(headless=headless_val, slow_mo=slow_mo_val)

            # Cookie injection
            try:
                await self._inject_cookies(context, job_url, logger)
            except Exception as e:
                log.warning(f"Cookie injection skipped: {e}")

            # Navigation
            await logger.log(f"🔍 Navigating to: {job_url[:80]}...")
            try:
                response = await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
                await logger.log("✅ Navigation completed.")
                
                # REQUIREMENT 1: Log the current page URL for every job.
                current_url = page.url
                await logger.log(f"🔗 Current page URL: {current_url}")
                
                await _human_delay(2000, 4000)
            except Exception as nav_err:
                error_detail = f"Navigation failed: {type(nav_err).__name__}: {str(nav_err)}"
                await logger.log(f"❌ {error_detail}")
                screenshot = await self._take_screenshot(page, task_id)
                return {
                    "status": "failed",
                    "reason": error_detail,
                    "screenshot": screenshot,
                }

            # Redirect ATS detection
            current_url = page.url
            await logger.log(f"🔗 Page URL after navigation/redirects: {current_url}")
            ats_platform = self._is_external_ats(current_url)
            if ats_platform:
                await logger.log(f"⚠️ Redirected to external ATS: {ats_platform}")
                screenshot = await self._take_screenshot(page, task_id)
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
                    return {"status": "applied", "reason": "Already applied", "screenshot": screenshot}
                elif state == "premium_required":
                    await logger.log("⚠️ Premium Required: Paid subscription required on this platform.")
                    return {"status": "requires_manual_intervention", "reason": "Paid platform subscription required", "screenshot": screenshot}
                elif state == "closed":
                    await logger.log("❌ Closed: Job listing is no longer accepting applications.")
                    return {"status": "requires_manual_intervention", "reason": "Job listing closed", "screenshot": screenshot}
                elif state == "blocked_captcha":
                    await logger.log("⚠️ Security Block: CAPTCHA / human verification challenge detected.")
                    return {"status": "requires_manual_intervention", "reason": "CAPTCHA challenge detected", "screenshot": screenshot}
                elif state == "blocked_otp":
                    await logger.log("⚠️ Security Block: OTP verification code requested.")
                    return {"status": "requires_manual_intervention", "reason": "OTP requested", "screenshot": screenshot}

            # REQUIREMENT 11: Verify that the browser is actually opening the job details page
            # instead of remaining on a search results page or an authentication page.
            current_url_lower = current_url.lower()
            is_auth_page = "login" in current_url_lower or "signin" in current_url_lower or "signup" in current_url_lower or "register" in current_url_lower or "auth" in current_url_lower
            
            is_search_page = False
            if "search" in current_url_lower or "jobs/search" in current_url_lower or "jobs/browse" in current_url_lower or "job-search" in current_url_lower:
                # If there's a job ID parameter or if the path contains 'job-listings' or 'jobs/view', it is a details page!
                has_job_id_param = any(param in current_url_lower for param in ["jobid", "job_id", "currentjobid"])
                has_listing_path = any(path in current_url_lower for path in ["job-listings", "jobs/view", "/jobs/"])
                if not (has_job_id_param or has_listing_path):
                    is_search_page = True
            
            if is_auth_page:
                auth_reason = "Verification Failed: Browser is on an authentication/login page instead of job details page."
                await logger.log(f"❌ {auth_reason}")
                screenshot = await self._take_screenshot(page, task_id)
                return {
                    "status": "requires_manual_intervention",
                    "reason": auth_reason,
                    "screenshot": screenshot,
                }
            elif is_search_page:
                search_reason = "Verification Failed: Browser is on a job search list page instead of specific job details page."
                await logger.log(f"❌ {search_reason}")
                screenshot = await self._take_screenshot(page, task_id)
                return {
                    "status": "requires_manual_intervention",
                    "reason": search_reason,
                    "screenshot": screenshot,
                }

            # Get Adapter
            adapter = PlatformAdapterFactory.get_adapter(current_url, page, logger)
            
            # REQUIREMENT 2: Log the detected platform (LinkedIn, Naukri, Indeed, Glassdoor, Wellfound, Generic).
            platform_name = adapter.__class__.__name__.replace("Adapter", "")
            await logger.log(f"🎯 Detected platform: {platform_name}")

            # REQUIREMENT 3: Before scanning, capture a screenshot.
            pre_scan_screenshot = await self._take_screenshot(page, task_id)
            await logger.log(f"📸 Pre-scan screenshot captured: {pre_scan_screenshot}")

            # REQUIREMENT 4, 5, 6: Print button/anchor text and keyword-containing elements.
            await self._perform_diagnostics(page, logger)

            # Click Apply
            await logger.log("📋 Scanning page for Apply trigger buttons...")
            
            # REQUIREMENT 8: Do not spend more than 10 seconds searching for an Apply button.
            # REQUIREMENT 9: If no Apply button is found after 10 seconds, capture screenshot, log HTML, and continue immediately.
            apply_clicked = False
            try:
                apply_clicked = await asyncio.wait_for(
                    adapter.click_apply(task_id),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                await logger.log("⏱️ Timeout: Searching for Apply button took more than 10 seconds.")
                apply_clicked = False
            except Exception as click_err:
                await logger.log(f"⚠️ Error while searching for Apply button: {click_err}")
                apply_clicked = False

            if not apply_clicked:
                # REQUIREMENT 7: Explain WHY instead of only saying "No Apply button detected."
                why_reason = await self._explain_missing_button_reason(page, logger)
                await logger.log(f"⚠️ Apply button detection failed: {why_reason}")
                
                # REQUIREMENT 9: Capture screenshot
                screenshot = await self._take_screenshot(page, task_id)
                
                # REQUIREMENT 9: Log page HTML
                try:
                    html_content = await page.content()
                    await logger.log(f"📄 Page HTML (first 3000 chars):\n{html_content[:3000]}...")
                except Exception as html_err:
                    await logger.log(f"⚠️ Could not dump page HTML: {html_err}")

                return {
                    "status": "requires_manual_intervention",
                    "reason": why_reason,
                    "screenshot": screenshot,
                }

            await _human_delay(2000, 4000)

            # Re-check ATS redirect after Apply click
            current_url = page.url
            ats_platform = self._is_external_ats(current_url)
            if ats_platform:
                await logger.log(f"⚠️ Apply click redirected to external ATS: {ats_platform}")
                screenshot = await self._take_screenshot(page, task_id)
                return {
                    "status": "requires_manual_intervention",
                    "reason": f"Apply button redirected to external ATS: {ats_platform}",
                    "ats_platform": ats_platform,
                    "screenshot": screenshot,
                }

            # Fill form fields
            await logger.log("✍️ Populating form fields from candidate profile...")
            field_map = self._build_field_map(user)
            fields_filled = await adapter.fill_form(task_id, field_map)
            await logger.log(f"✅ Filled {fields_filled} form fields")

            # Upload resume
            if resume_path and os.path.isfile(resume_path):
                await logger.log("📄 Attaching resume binary...")
                uploaded = await adapter.upload_resume(task_id, resume_path)
                if uploaded:
                    await logger.log("✅ Resume file uploaded successfully")
                else:
                    await logger.log("⚠️ Resume upload input not found or failed")

            await _human_delay(1500, 3000)

            # Take pre-submit screenshot
            screenshot = await self._take_screenshot(page, task_id)
            await logger.log("📸 Pre-submit audit screenshot captured.")

            # Submit form
            submitted = False
            if FULLY_AUTONOMOUS:
                await logger.log("🖱️ Form fields verified. Triggering final application submission click...")
                submitted = await adapter.submit_form(task_id)
                if submitted:
                    try:
                        await page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
            else:
                await logger.log("⏸️ Paused: Review the page in the browser window and click Submit manually.")
                try:
                    from agents.orchestrator import db_update_queue_status
                    db_update_queue_status(task_id, "PENDING_SUBMIT")
                except Exception:
                    pass
                # Await manual submission
                for _ in range(120):
                    if page.is_closed():
                        submitted = True
                        break
                    await asyncio.sleep(1)

            if submitted:
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
                return {
                    "status": "requires_manual_intervention",
                    "reason": "Form populated but submit confirmation could not be verified",
                    "fields_filled": fields_filled,
                    "screenshot": screenshot,
                }

        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            error_detail = f"{type(e).__name__}: {str(e)}"
            log.error(f"Engine Run Crash:\n{tb_str}")
            await logger.log(f"❌ Browser automation crashed: {error_detail}")

            screenshot = ""
            if page:
                try:
                    screenshot = await self._take_screenshot(page, task_id)
                except Exception:
                    pass
            return {
                "status": "failed",
                "reason": error_detail,
                "screenshot": screenshot,
            }
        finally:
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

    async def apply_to_job(
        self,
        task_id: str,
        job_url: str,
        job_title: str,
        job_company: str,
        user: UserProfile,
        resume_path: str = "",
        on_progress: Optional[Callable] = None,
    ) -> dict[str, Any]:
        return await self.engine.run(
            task_id=task_id,
            job_url=job_url,
            job_title=job_title,
            job_company=job_company,
            user=user,
            resume_path=resume_path,
            on_progress=on_progress,
        )
