"""
Agent 2 — Career Profiler Agent

Infers career paths, seniority, salary expectations, and industry fit
from a UserProfile using Gemini.
"""
from __future__ import annotations
import json
import re
from typing import Any

import google.generativeai as genai

from config import get_settings
from logger import get_logger
from models import UserProfile, CareerProfile

log = get_logger("CareerProfilerAgent")
settings = get_settings()

PROFILER_PROMPT = """
You are a veteran career strategist with 20 years of experience placing engineers and designers at top tech companies.

Analyze this candidate profile and return ONLY valid JSON (no markdown):
{{
  "career_paths": ["path1", "path2", "path3"],
  "ideal_titles": ["title1", "title2", "title3", "title4"],
  "seniority_level": "Entry|Mid|Senior|Staff|Principal",
  "industries": ["industry1", "industry2"],
  "salary_min": <integer INR annual, e.g. 1200000 for 12 LPA>,
  "salary_max": <integer INR annual, e.g. 2500000 for 25 LPA>,
  "strengths": ["strength1", "strength2", "strength3"],
  "growth_areas": ["area1", "area2", "area3"]
}}

Candidate Profile:
{profile_json}
"""


class CareerProfilerAgent:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        log.info("CareerProfilerAgent initialised")

    def _safe_parse(self, text: str) -> dict[str, Any]:
        clean = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
        try:
            return json.loads(clean)
        except Exception:
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
            return {}

    async def profile(self, user_profile: UserProfile) -> CareerProfile:
        log.info(f"Profiling career for: {user_profile.name}")
        compact = {
            "skills": user_profile.skills,
            "technologies": user_profile.technologies,
            "work_history": user_profile.work_history,
            "education": user_profile.education,
            "certifications": user_profile.certifications,
            "summary": user_profile.summary,
        }
        prompt = PROFILER_PROMPT.format(profile_json=json.dumps(compact, indent=2)[:4000])
        try:
            response = await self.model.generate_content_async(prompt)
            data = self._safe_parse(response.text)
        except Exception as e:
            log.warning(f"CareerProfilerAgent Gemini call failed: {e}. Using rule-based fallback.")
            role_hint = user_profile.skills[0] if user_profile.skills else "Software Engineer"
            data = {
                "career_paths": ["Software Engineering", "Systems Development"],
                "ideal_titles": [role_hint, f"Senior {role_hint}", f"Lead {role_hint}"],
                "seniority_level": "Mid",
                "industries": ["Technology", "Internet"],
                "salary_min": 1000000,
                "salary_max": 2400000,
                "strengths": [f"Experience in {role_hint}", "Problem Solving", "Software Design"],
                "growth_areas": ["System Architecture", "Scale Operations"]
            }

        career = CareerProfile(
            user_id=user_profile.id,
            career_paths=data.get("career_paths") or ["Software Engineering"],
            ideal_titles=data.get("ideal_titles") or ["Software Engineer"],
            seniority_level=data.get("seniority_level") or "Mid",
            industries=data.get("industries") or ["Technology"],
            salary_min=data.get("salary_min") if data.get("salary_min") is not None else 800000,
            salary_max=data.get("salary_max") if data.get("salary_max") is not None else 1800000,
            salary_currency="INR",
            strengths=data.get("strengths") or [],
            growth_areas=data.get("growth_areas") or [],
        )
        log.info(f"Career profile complete: {career.ideal_titles[:2]} | {career.seniority_level} | {career.salary_min} - {career.salary_max} INR")
        return career
