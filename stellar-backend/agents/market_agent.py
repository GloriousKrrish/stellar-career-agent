"""
Agent 3 — Market Intelligence Agent

Analyzes current hiring trends, identifies in-demand skills,
detects skill gaps relative to the candidate, and recommends certifications.
"""
from __future__ import annotations
import json
import re
from typing import Any

import google.generativeai as genai

from config import get_settings
from logger import get_logger
from models import UserProfile, CareerProfile, MarketReport

log = get_logger("MarketIntelligenceAgent")
settings = get_settings()

MARKET_PROMPT = """
You are a labor market analyst with real-time knowledge of the tech job market in 2025-2026.

Given the candidate profile below, generate a market intelligence report.

Return ONLY valid JSON (no markdown):
{{
  "trending_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "in_demand_roles": ["role1", "role2", "role3"],
  "skill_gaps": ["gap1", "gap2", "gap3"],
  "recommended_certifications": ["cert1", "cert2"],
  "market_insights": [
    "Insight 1 about current market for this candidate",
    "Insight 2 about salary trends",
    "Insight 3 about remote opportunities"
  ],
  "avg_salary_range": "$120,000 – $200,000"
}}

Candidate:
- Skills: {skills}
- Titles targeting: {titles}
- Seniority: {seniority}
- Industry: {industries}
"""


class MarketIntelligenceAgent:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        log.info("MarketIntelligenceAgent initialised")

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

    async def analyze(self, user_profile: UserProfile, career_profile: CareerProfile) -> MarketReport:
        log.info(f"Running market analysis for: {user_profile.name}")
        prompt = MARKET_PROMPT.format(
            skills=", ".join(user_profile.skills[:20]),
            titles=", ".join(career_profile.ideal_titles[:5]),
            seniority=career_profile.seniority_level,
            industries=", ".join(career_profile.industries),
        )
        response = await self.model.generate_content_async(prompt)
        data = self._safe_parse(response.text)

        report = MarketReport(
            user_id=user_profile.id,
            trending_skills=data.get("trending_skills", []),
            in_demand_roles=data.get("in_demand_roles", []),
            skill_gaps=data.get("skill_gaps", []),
            recommended_certifications=data.get("recommended_certifications", []),
            market_insights=data.get("market_insights", []),
            avg_salary_range=data.get("avg_salary_range", ""),
        )
        log.info(f"Market report complete: {len(report.trending_skills)} trending skills, {len(report.skill_gaps)} gaps")
        return report
