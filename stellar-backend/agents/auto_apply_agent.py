"""
Agent 8 — AutoApply Agent
=========================
Autonomous browser-based job application worker.

Capabilities:
  - Navigates directly to scraped job deep-links
  - Uses Playwright with stealth evasion (randomized viewport, delays, UA rotation)
  - Detects and fills application forms dynamically from user profile
  - Uploads resume via file input selectors
  - Catches outbound ATS redirects (Workday, Greenhouse, Taleo, Lever)
  - Streams real-time progress events to the frontend live feed
  - Escalates to human-in-the-loop when blocked

Statuses written to DB:
  discovered → queued → applying → applied | requires_manual_intervention | failed
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
from models import UserProfile, ScoredJob

log = get_logger("AutoApplyAgent")

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


async def _human_delay(min_ms: int = 800, max_ms: int = 3000) -> None:
    """Randomized delay to simulate human interaction cadence."""
    await asyncio.sleep(random.randint(min_ms, max_ms) / 1000.0)


class AutoApplyAgent:
    """
    Production-grade autonomous job application agent.
    Operates as a background worker polled by the AgentOrchestrator.
    """

    def __init__(self):
        self.screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

    # ── Profile → Form Field Mapping ─────────────────────────────────────────

    def _build_field_map(self, user: UserProfile) -> dict[str, str]:
        """Map common form field names/labels to candidate data values."""
        exp_str = ""
        current_company = ""
        years_exp = "2"
        if user.work_history:
            last = user.work_history[0]
            exp_str = f"{last.get('title', '')} at {last.get('company', '')}"
            current_company = last.get("company", "")
            years_exp = str(max(1, len(user.work_history) * 2))

        return {
            # Name
            "name": user.name,
            "full_name": user.name,
            "full name": user.name,
            "first_name": user.name.split()[0] if user.name else "",
            "first name": user.name.split()[0] if user.name else "",
            "last_name": user.name.split()[-1] if user.name and len(user.name.split()) > 1 else "",
            "last name": user.name.split()[-1] if user.name and len(user.name.split()) > 1 else "",
            # Contact
            "email": user.email,
            "email_address": user.email,
            "email address": user.email,
            "phone": user.phone,
            "phone_number": user.phone,
            "phone number": user.phone,
            "mobile": user.phone,
            "mobile number": user.phone,
            "contact": user.phone,
            # Location
            "location": user.location,
            "city": user.location.split(",")[0].strip() if "," in user.location else user.location,
            "current location": user.location,
            "address": user.location,
            # Professional links
            "linkedin": user.linkedin,
            "linkedin_url": user.linkedin,
            "linkedin url": user.linkedin,
            "github": user.github,
            "github_url": user.github,
            "github url": user.github,
            "portfolio": user.github or user.linkedin,
            "website": user.linkedin or user.github,
            # Experience
            "current_title": exp_str,
            "current title": exp_str,
            "current_company": current_company,
            "current company": current_company,
            "years_experience": years_exp,
            "years of experience": years_exp,
            "experience": years_exp,
            "total experience": years_exp,
            # Skills
            "skills": ", ".join(user.skills[:10]),
            "key skills": ", ".join(user.skills[:10]),
            # Cover letter
            "cover_letter": self._generate_cover_letter(user),
            "cover letter": self._generate_cover_letter(user),
            "message": self._generate_cover_letter(user),
            "additional information": self._generate_cover_letter(user),
        }

    def _generate_cover_letter(self, user: UserProfile) -> str:
        """Generate a professional cover letter from user profile."""
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

    # ── ATS Redirect Detection ────────────────────────────────────────────────

    def _is_external_ats(self, url: str) -> str | None:
        """Check if URL redirects to a known external ATS platform."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            for ats in EXTERNAL_ATS_DOMAINS:
                if ats in domain:
                    return ats
        except Exception:
            pass
        return None

    def _is_blocked(self, page_content: str) -> str | None:
        """Detect CAPTCHA / anti-bot signals in page content."""
        lower = page_content.lower()
        for signal in BLOCKER_SIGNALS:
            if signal in lower:
                return signal
        return None

    # ── Screenshot Utility ────────────────────────────────────────────────────

    async def _take_screenshot(self, page: Any, task_id: str) -> str:
        """Capture a full-page screenshot for audit trail."""
        filename = f"autoapply_{task_id}_{uuid.uuid4().hex[:6]}.png"
        path = os.path.join(self.screenshots_dir, filename)
        try:
            await page.screenshot(path=path, full_page=True)
            log.info(f"Screenshot saved: {path}")
        except Exception as e:
            log.warning(f"Screenshot failed: {e}")
            path = ""
        return path

    # ── Core Application Logic ────────────────────────────────────────────────

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
        """
        Main entry: attempt autonomous application via headless browser.
        
        Returns dict with:
          status: 'applied' | 'requires_manual_intervention' | 'failed' | 'simulated'
          reason: Human-readable explanation
          screenshot: Path to screenshot if captured
        """
        log.info(f"[{task_id[:8]}] AutoApply starting: {job_title} @ {job_company}")
        log.info(f"[{task_id[:8]}] Target URL: {job_url}")

        if not job_url or job_url.startswith("https://jobs.example"):
            return {
                "status": "simulated",
                "reason": "No valid application URL available",
                "screenshot": "",
            }

        # Check for external ATS before launching browser
        ats_platform = self._is_external_ats(job_url)
        if ats_platform:
            log.info(f"[{task_id[:8]}] External ATS detected: {ats_platform}")
            if on_progress:
                await on_progress(f"External ATS detected ({ats_platform}) — marking for manual review")
            return {
                "status": "requires_manual_intervention",
                "reason": f"Redirects to external ATS platform: {ats_platform}. Manual application required.",
                "ats_platform": ats_platform,
                "screenshot": "",
            }

        # Try Playwright-based automation
        try:
            return await self._run_browser_application(
                task_id=task_id,
                job_url=job_url,
                job_title=job_title,
                job_company=job_company,
                user=user,
                resume_path=resume_path,
                on_progress=on_progress,
            )
        except ImportError as e:
            log.info(f"Playwright not available: {e} — falling back to simulation")
            return {
                "status": "simulated",
                "reason": "Browser automation not available in this environment",
                "screenshot": "",
            }
        except Exception as e:
            log.error(f"[{task_id[:8]}] AutoApply error: {e}", exc_info=True)
            return {
                "status": "failed",
                "reason": str(e)[:500],
                "screenshot": "",
            }

    async def _run_browser_application(
        self,
        task_id: str,
        job_url: str,
        job_title: str,
        job_company: str,
        user: UserProfile,
        resume_path: str,
        on_progress: Optional[Callable] = None,
    ) -> dict[str, Any]:
        """Execute the full browser automation pipeline using Playwright."""
        from playwright.async_api import async_playwright

        viewport = random.choice(VIEWPORT_POOL)
        user_agent = random.choice(UA_POOL)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            context = await browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                # Mask automation signals
                java_script_enabled=True,
            )

            # Inject stealth scripts to mask webdriver detection
            await context.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                // Override chrome.runtime to prevent detection
                window.chrome = { runtime: {} };
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) =>
                    parameters.name === 'notifications'
                        ? Promise.resolve({ state: Notification.permission })
                        : originalQuery(parameters);
                // Override plugins length
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en', 'hi'],
                });
            """)

            page = await context.new_page()

            try:
                if on_progress:
                    await on_progress(f"Navigating to {job_company} application page...")

                # ── Step 1: Navigate to job URL ───────────────────────────────
                response = await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
                await _human_delay(1500, 3000)

                # Check for redirect to external ATS
                current_url = page.url
                ats_platform = self._is_external_ats(current_url)
                if ats_platform:
                    screenshot = await self._take_screenshot(page, task_id)
                    log.info(f"[{task_id[:8]}] Redirected to ATS: {ats_platform}")
                    if on_progress:
                        await on_progress(f"Redirected to {ats_platform} — requires manual application")
                    return {
                        "status": "requires_manual_intervention",
                        "reason": f"Job redirected to external ATS: {ats_platform}",
                        "ats_platform": ats_platform,
                        "redirect_url": current_url,
                        "screenshot": screenshot,
                    }

                # ── Step 2: Check for anti-bot blocks ─────────────────────────
                page_text = await page.inner_text("body")
                blocker = self._is_blocked(page_text)
                if blocker:
                    screenshot = await self._take_screenshot(page, task_id)
                    log.warning(f"[{task_id[:8]}] Blocked by: {blocker}")
                    if on_progress:
                        await on_progress(f"Blocked by {blocker} — escalating to human review")
                    return {
                        "status": "requires_manual_intervention",
                        "reason": f"Anti-bot protection detected: {blocker}",
                        "screenshot": screenshot,
                    }

                if on_progress:
                    await on_progress(f"Page loaded. Scanning for application form elements...")

                # ── Step 3: Find and click Apply button ───────────────────────
                apply_clicked = await self._find_and_click_apply(page, task_id)
                if not apply_clicked:
                    screenshot = await self._take_screenshot(page, task_id)
                    log.info(f"[{task_id[:8]}] No Apply button found")
                    if on_progress:
                        await on_progress("No standard Apply button detected — marking for manual review")
                    return {
                        "status": "requires_manual_intervention",
                        "reason": "Could not locate an Apply button on the job page",
                        "screenshot": screenshot,
                    }

                await _human_delay(2000, 4000)

                # Re-check for ATS redirect after clicking Apply
                current_url = page.url
                ats_platform = self._is_external_ats(current_url)
                if ats_platform:
                    screenshot = await self._take_screenshot(page, task_id)
                    if on_progress:
                        await on_progress(f"Apply button redirected to {ats_platform}")
                    return {
                        "status": "requires_manual_intervention",
                        "reason": f"Apply redirected to external ATS: {ats_platform}",
                        "ats_platform": ats_platform,
                        "redirect_url": current_url,
                        "screenshot": screenshot,
                    }

                if on_progress:
                    await on_progress("Apply form detected. Filling candidate information...")

                # ── Step 4: Fill form fields ──────────────────────────────────
                field_map = self._build_field_map(user)
                fields_filled = await self._fill_form_fields(page, field_map, task_id)

                if on_progress:
                    await on_progress(f"Filled {fields_filled} form fields from profile data")

                # ── Step 5: Upload resume if file input exists ────────────────
                if resume_path and os.path.isfile(resume_path):
                    uploaded = await self._upload_resume(page, resume_path, task_id)
                    if uploaded and on_progress:
                        await on_progress("Resume file uploaded successfully")

                await _human_delay(1500, 3000)

                # ── Step 6: Take pre-submit screenshot ────────────────────────
                screenshot = await self._take_screenshot(page, task_id)

                if on_progress:
                    await on_progress(f"Application form populated for {job_title} @ {job_company}")

                # ── Step 7: Attempt submit ────────────────────────────────────
                submitted = await self._submit_form(page, task_id)
                
                if submitted:
                    await _human_delay(2000, 4000)
                    final_screenshot = await self._take_screenshot(page, task_id)
                    log.info(f"[{task_id[:8]}] Application submitted successfully")
                    if on_progress:
                        await on_progress(f"✅ Application submitted for {job_title} @ {job_company}")
                    return {
                        "status": "applied",
                        "reason": f"Successfully submitted application for {job_title} at {job_company}",
                        "fields_filled": fields_filled,
                        "screenshot": final_screenshot or screenshot,
                    }
                else:
                    log.info(f"[{task_id[:8]}] Form filled but submit button not found — manual review")
                    if on_progress:
                        await on_progress("Form filled but could not confirm submission — needs manual verification")
                    return {
                        "status": "requires_manual_intervention",
                        "reason": "Form populated but submit confirmation could not be verified",
                        "fields_filled": fields_filled,
                        "screenshot": screenshot,
                    }

            except Exception as e:
                screenshot = await self._take_screenshot(page, task_id)
                log.error(f"[{task_id[:8]}] Browser error: {e}")
                return {
                    "status": "failed",
                    "reason": str(e)[:500],
                    "screenshot": screenshot,
                }
            finally:
                await context.close()
                await browser.close()

    # ── DOM Interaction Helpers ────────────────────────────────────────────────

    async def _find_and_click_apply(self, page: Any, task_id: str) -> bool:
        """Locate and click the primary Apply / Apply Now button."""
        apply_selectors = [
            # Naukri-specific selectors
            'button:has-text("Apply")',
            'a:has-text("Apply Now")',
            'button:has-text("Apply Now")',
            'a:has-text("Apply on company site")',
            'button:has-text("Apply on company site")',
            # Glassdoor
            'button:has-text("Easy Apply")',
            'a:has-text("Easy Apply")',
            # Generic
            'input[type="submit"][value*="Apply" i]',
            'button[type="submit"]:has-text("Apply")',
            'a[class*="apply" i]',
            'button[class*="apply" i]',
            '[data-testid*="apply" i]',
            '[id*="apply" i]',
        ]

        for selector in apply_selectors:
            try:
                el = page.locator(selector).first
                if await el.is_visible(timeout=2000):
                    await _human_delay(500, 1500)
                    await el.click()
                    log.info(f"[{task_id[:8]}] Clicked apply: {selector}")
                    return True
            except Exception:
                continue

        return False

    async def _fill_form_fields(self, page: Any, field_map: dict[str, str], task_id: str) -> int:
        """Detect and fill all visible form fields using the user profile data."""
        filled_count = 0

        # Strategy 1: Match by input name, id, placeholder, aria-label
        inputs = await page.query_selector_all(
            "input[type='text'], input[type='email'], input[type='tel'], "
            "input[type='url'], input[type='number'], textarea"
        )

        for inp in inputs:
            try:
                if not await inp.is_visible():
                    continue

                # Gather all identifying attributes
                attrs = {}
                for attr in ["name", "id", "placeholder", "aria-label", "autocomplete"]:
                    val = await inp.get_attribute(attr)
                    if val:
                        attrs[attr] = val.lower().strip()

                # Try to match against field map
                matched_value = None
                for attr_val in attrs.values():
                    for field_key, field_val in field_map.items():
                        if field_key in attr_val or attr_val in field_key:
                            if field_val:
                                matched_value = field_val
                                break
                    if matched_value:
                        break

                # Also try matching by associated label
                if not matched_value:
                    inp_id = await inp.get_attribute("id")
                    if inp_id:
                        try:
                            label = await page.query_selector(f'label[for="{inp_id}"]')
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
                    # Type character-by-character for human-like behavior
                    await inp.type(matched_value, delay=random.randint(30, 80))
                    filled_count += 1
                    log.debug(f"[{task_id[:8]}] Filled field: {list(attrs.values())[:2]}")

            except Exception as e:
                log.debug(f"[{task_id[:8]}] Field fill error: {e}")
                continue

        # Strategy 2: Fill select dropdowns with best-guess values
        selects = await page.query_selector_all("select")
        for sel in selects:
            try:
                if not await sel.is_visible():
                    continue
                # Try selecting the first non-empty option (skip "Select..." placeholder)
                options = await sel.query_selector_all("option")
                for opt in options[1:]:  # Skip first (usually placeholder)
                    val = await opt.get_attribute("value")
                    if val and val.strip():
                        await sel.select_option(value=val)
                        filled_count += 1
                        break
            except Exception:
                continue

        log.info(f"[{task_id[:8]}] Filled {filled_count} form fields")
        return filled_count

    async def _upload_resume(self, page: Any, resume_path: str, task_id: str) -> bool:
        """Find file input and upload the user's resume."""
        file_inputs = await page.query_selector_all('input[type="file"]')
        for fi in file_inputs:
            try:
                await fi.set_input_files(resume_path)
                log.info(f"[{task_id[:8]}] Resume uploaded via file input")
                return True
            except Exception as e:
                log.debug(f"[{task_id[:8]}] File upload error: {e}")
                continue
        return False

    async def _submit_form(self, page: Any, task_id: str) -> bool:
        """Find and click the final submit button."""
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
                el = page.locator(selector).first
                if await el.is_visible(timeout=2000):
                    await _human_delay(1000, 2500)
                    await el.click()
                    log.info(f"[{task_id[:8]}] Clicked submit: {selector}")
                    return True
            except Exception:
                continue

        return False
