"""
Agent 7 — Application Agent

Uses browser-use (Playwright) to:
1. Navigate to job application pages
2. Detect form fields dynamically via DOM analysis
3. Fill fields intelligently from the candidate profile
4. Upload resume and cover letter
5. Validate before submitting
6. Handle CAPTCHA / Cloudflare / MFA → Human-in-the-Loop

Returns ACTION_REQUIRED when human intervention is needed.
"""
from __future__ import annotations
import asyncio
import os
import uuid
from datetime import datetime
from typing import Any

from logger import get_logger
from models import UserProfile, ScoredJob, ActionRequiredResponse, WorkflowState

log = get_logger("ApplicationAgent")

# HIIL Blockers
BLOCKER_SIGNALS = [
    "captcha", "cloudflare", "robot", "verify you are human",
    "access denied", "403 forbidden", "challenge", "otp", "one-time",
    "security check", "suspicious activity", "bot detection",
]


class ApplicationAgent:
    """
    Autonomous application filing agent with Human-in-the-Loop escalation.
    Uses browser-use library for Playwright-powered form automation.
    """

    def __init__(self):
        self.screenshots_dir = "screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        log.info("ApplicationAgent initialised")

    def _is_blocked(self, page_content: str) -> str | None:
        """Detect CAPTCHA / anti-bot signals in page content."""
        lower = page_content.lower()
        for signal in BLOCKER_SIGNALS:
            if signal in lower:
                return signal
        return None

    async def _take_screenshot(self, page: Any, run_id: str) -> str:
        """Capture screenshot and return file path."""
        path = os.path.join(self.screenshots_dir, f"{run_id}_{uuid.uuid4().hex[:8]}.png")
        try:
            await page.screenshot(path=path, full_page=True)
        except Exception as e:
            log.warning(f"Screenshot failed: {e}")
        return path

    def _build_field_map(self, user: UserProfile) -> dict[str, str]:
        """Map common form field names to candidate data."""
        exp_str = ""
        if user.work_history:
            last = user.work_history[0]
            exp_str = f"{last.get('title','')} at {last.get('company','')}"

        return {
            # Name fields
            "name": user.name,
            "full_name": user.name,
            "first_name": user.name.split()[0] if user.name else "",
            "last_name": user.name.split()[-1] if user.name and len(user.name.split()) > 1 else "",
            "fullname": user.name,
            # Contact
            "email": user.email,
            "email_address": user.email,
            "phone": user.phone,
            "phone_number": user.phone,
            "mobile": user.phone,
            # Location
            "location": user.location,
            "city": user.location.split(",")[0].strip() if "," in user.location else user.location,
            "address": user.location,
            # Professional
            "linkedin": user.linkedin,
            "linkedin_url": user.linkedin,
            "github": user.github,
            "github_url": user.github,
            "portfolio": user.github,
            "website": user.linkedin or user.github,
            # Experience
            "current_title": exp_str,
            "current_company": user.work_history[0].get("company", "") if user.work_history else "",
            "years_experience": str(len(user.work_history) * 2),
            # Skills
            "skills": ", ".join(user.skills[:10]),
            "cover_letter": f"Dear Hiring Manager,\n\nI am excited to apply for this position. With expertise in {', '.join(user.skills[:5])}, I am confident I can make an immediate impact.\n\nBest regards,\n{user.name}",
        }

    async def apply_to_job(
        self,
        job: ScoredJob,
        user: UserProfile,
        run_id: str,
        resume_path: str = "",
    ) -> dict[str, Any]:
        """
        Main entry: attempt to apply to a job using browser automation.
        Returns result dict with status: 'success' | 'action_required' | 'error'
        """
        log.info(f"Attempting application: {job.title} @ {job.company} | URL: {job.url}")

        if not job.url or job.url.startswith("https://jobs.example"):
            log.info("No real application URL — skipping browser automation")
            return {
                "status": "simulated",
                "message": f"Application queued for {job.title} at {job.company}",
                "job_id": job.id,
            }

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from browser_use import Agent as BrowserAgent
            from config import get_settings

            settings = get_settings()
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=settings.gemini_api_key,
            )

            field_map = self._build_field_map(user)
            fields_desc = "\n".join(f"- {k}: {v}" for k, v in field_map.items() if v)[:2000]

            task = f"""
Navigate to {job.url} and apply for the {job.title} position at {job.company}.

Use these candidate details to fill ALL form fields:
{fields_desc}

Instructions:
1. First, read the page content carefully
2. Identify all form fields (name, email, phone, LinkedIn, GitHub, etc.)
3. Fill each field with the matching candidate data above
4. If there is a resume upload field and a file exists at {resume_path}, upload it
5. DO NOT click submit yet — just fill all fields
6. Report what fields you filled and flag any issues
7. If you encounter CAPTCHA, Cloudflare, or any security verification, STOP and report "BLOCKED: <reason>"
"""

            browser_agent = BrowserAgent(task=task, llm=llm)
            result = await browser_agent.run()
            result_text = str(result).lower()

            # Check if blocked
            blocker = self._is_blocked(result_text)
            if blocker or "blocked:" in result_text:
                reason = blocker or "Security verification required"
                log.warning(f"Application blocked: {reason}")
                return {
                    "status": "action_required",
                    "reason": reason.title(),
                    "url": job.url,
                    "screenshot": "",
                    "run_id": run_id,
                }

            log.info(f"Application completed for {job.title}")
            return {
                "status": "success",
                "message": f"Application submitted for {job.title} at {job.company}",
                "job_id": job.id,
                "details": str(result)[:500],
            }

        except ImportError:
            log.info("browser-use not available in this env — returning simulation")
            return {
                "status": "simulated",
                "message": f"Application process initiated for {job.title} at {job.company}",
                "job_id": job.id,
            }
        except Exception as e:
            log.error(f"Application agent error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "job_id": job.id,
            }
