"""
Agent 5 — Match Scoring Agent

Compares the candidate's profile against each discovered job.
Generates:
  - Semantic similarity score (skills overlap)
  - Experience alignment score
  - Overall match percentage
  - AI-written recommendation text
  - List of missing skills for each role
"""
from __future__ import annotations
import json
import re
import asyncio
from typing import Any

import google.generativeai as genai

from config import get_settings
from logger import get_logger
from models import UserProfile, RawJob, ScoredJob

log = get_logger("MatchScoringAgent")
settings = get_settings()

MATCH_PROMPT = """
You are a precision job-candidate matching AI. Score this candidate against this job.

Return ONLY valid JSON (no markdown):
{{
  "semantic_score": <float 0-100>,
  "skill_overlap_score": <float 0-100>,
  "experience_score": <float 0-100>,
  "overall_match": <integer 0-100>,
  "match_reasons": ["reason1", "reason2", "reason3"],
  "missing_skills": ["skill1", "skill2"],
  "ai_recommendation": "1-2 sentence personalised recommendation explaining the fit"
}}

Be precise and realistic. A score above 90 means near-perfect fit.

Candidate Skills: {candidate_skills}
Candidate Experience: {candidate_experience}
Candidate Seniority: {seniority}

Job Title: {job_title}
Job Company: {company}
Job Requirements: {requirements}
Job Skills: {job_skills}
Job Experience Level: {job_experience}
"""

SENIORITY_MAP = {
    "Entry": 0, "Mid": 1, "Senior": 2, "Staff": 3, "Principal": 4
}


def _experience_alignment(candidate_seniority: str, job_experience: str) -> float:
    """Score how well seniority levels align (0-100)."""
    c = SENIORITY_MAP.get(candidate_seniority, 1)
    j = SENIORITY_MAP.get(job_experience, 1)
    diff = abs(c - j)
    if diff == 0:
        return 100.0
    elif diff == 1:
        return 75.0
    elif diff == 2:
        return 50.0
    return 25.0


def _skill_overlap(candidate_skills: list[str], job_skills: list[str]) -> float:
    """Calculate jaccard-like skill overlap."""
    if not job_skills:
        return 70.0
    c_lower = {s.lower() for s in candidate_skills}
    j_lower = {s.lower() for s in job_skills}
    intersection = len(c_lower & j_lower)
    union = len(c_lower | j_lower)
    return round((intersection / union) * 100, 1) if union > 0 else 0.0


class MatchScoringAgent:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        log.info("MatchScoringAgent initialised")

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

    def _score_fast(self, user: UserProfile, job: RawJob, seniority: str) -> dict[str, Any]:
        """Fast local scoring without an LLM call — used for batch pre-filtering."""
        skill_score = _skill_overlap(user.skills + user.technologies, job.skills + job.requirements)
        exp_score = _experience_alignment(seniority, job.experience)
        overall = int((skill_score * 0.6 + exp_score * 0.4))
        return {
            "skill_overlap_score": skill_score,
            "experience_score": exp_score,
            "semantic_score": skill_score,
            "overall_match": min(overall, 98),
        }

    async def _score_with_ai(self, user: UserProfile, job: RawJob, seniority: str) -> dict[str, Any]:
        """Deep AI scoring using Gemini for top candidates."""
        try:
            prompt = MATCH_PROMPT.format(
                candidate_skills=", ".join(user.skills[:20]),
                candidate_experience="; ".join(
                    [f"{w.get('title','')} at {w.get('company','')}" for w in user.work_history[:3]]
                ),
                seniority=seniority,
                job_title=job.title,
                company=job.company,
                requirements=", ".join(job.requirements[:10]),
                job_skills=", ".join(job.skills[:15]),
                job_experience=job.experience,
            )
            response = await self.model.generate_content_async(prompt)
            return self._safe_parse(response.text)
        except Exception as e:
            log.warning(f"AI scoring failed for {job.title}: {e}")
            return {}

    async def score_batch(
        self,
        user: UserProfile,
        jobs: list[RawJob],
        seniority: str = "Mid",
        top_n_ai: int = 10,
    ) -> list[ScoredJob]:
        """
        Score all jobs. Use fast local scoring first, then AI for top matches.
        Returns jobs sorted by overall_match descending.
        """
        log.info(f"Scoring {len(jobs)} jobs for {user.name}")

        # Phase 1: fast local scoring
        fast_scored = []
        for job in jobs:
            scores = self._score_fast(user, job, seniority)
            fast_scored.append((job, scores))

        # Sort by overall_match — best first
        fast_scored.sort(key=lambda x: x[1]["overall_match"], reverse=True)

        # Phase 2: AI deep scoring for top candidates in parallel
        tasks = []
        ai_jobs = []
        for i, (job, fast_scores) in enumerate(fast_scored):
            if i < top_n_ai:
                tasks.append(self._score_with_ai(user, job, seniority))
                ai_jobs.append((job, fast_scores))

        # Gather AI scores concurrently
        ai_results = await asyncio.gather(*tasks) if tasks else []

        scored_jobs: list[ScoredJob] = []

        # Process the AI-scored jobs
        for (job, fast_scores), ai_scores in zip(ai_jobs, ai_results):
            final_scores = {
                "semantic_score": ai_scores.get("semantic_score", fast_scores["semantic_score"]),
                "skill_overlap_score": ai_scores.get("skill_overlap_score", fast_scores["skill_overlap_score"]),
                "experience_score": ai_scores.get("experience_score", fast_scores["experience_score"]),
                "overall_match": ai_scores.get("overall_match", fast_scores["overall_match"]),
                "match_reasons": ai_scores.get("match_reasons", []),
                "missing_skills": ai_scores.get("missing_skills", []),
                "ai_recommendation": ai_scores.get("ai_recommendation", f"Strong fit for {job.title} at {job.company}."),
            }
            company_logo = job.company[0].upper() if job.company else "?"
            scored_jobs.append(ScoredJob(
                **job.model_dump(),
                semantic_score=final_scores["semantic_score"],
                skill_overlap_score=final_scores["skill_overlap_score"],
                experience_score=final_scores["experience_score"],
                overall_match=final_scores["overall_match"],
                match_reasons=final_scores["match_reasons"],
                missing_skills=final_scores["missing_skills"],
                ai_recommendation=final_scores["ai_recommendation"],
                company_logo=company_logo,
            ))

        # Process the remaining fast-scored jobs
        for job, fast_scores in fast_scored[len(ai_jobs):]:
            final_scores = {
                **fast_scores,
                "match_reasons": [],
                "missing_skills": [],
                "ai_recommendation": f"Good potential match for {job.title} at {job.company}."
            }
            company_logo = job.company[0].upper() if job.company else "?"
            scored_jobs.append(ScoredJob(
                **job.model_dump(),
                semantic_score=final_scores["semantic_score"],
                skill_overlap_score=final_scores["skill_overlap_score"],
                experience_score=final_scores["experience_score"],
                overall_match=final_scores["overall_match"],
                match_reasons=final_scores["match_reasons"],
                missing_skills=final_scores["missing_skills"],
                ai_recommendation=final_scores["ai_recommendation"],
                company_logo=company_logo,
            ))

        scored_jobs.sort(key=lambda j: j.overall_match, reverse=True)
        log.info(f"Scoring complete. Top match: {scored_jobs[0].overall_match}% — {scored_jobs[0].title} @ {scored_jobs[0].company}" if scored_jobs else "No jobs scored")
        return scored_jobs
