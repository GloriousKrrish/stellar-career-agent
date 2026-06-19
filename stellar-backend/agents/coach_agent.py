"""
Agent 6 — Career Coach Agent

Provides personalized career guidance:
- Explains why a job is/isn't a good fit
- Identifies missing skills
- Creates a learning roadmap
- Answers career questions via chat
- Suggests career progression paths
"""
from __future__ import annotations
import google.generativeai as genai

from config import get_settings
from logger import get_logger
from models import UserProfile, CareerProfile, MarketReport, ScoredJob, ChatMessage

log = get_logger("CareerCoachAgent")
settings = get_settings()

COACH_SYSTEM_PROMPT = """
You are Aria, an elite AI career coach with expertise in:
- Technical hiring at top tech companies (FAANG, unicorns, startups)
- Resume and profile optimization
- Career strategy and progression
- Technical skill development roadmaps
- Salary negotiation
- Interview preparation

You have access to the candidate's full profile, market data, and matched jobs.
Be specific, actionable, and encouraging. Reference their actual skills and experience.
Keep responses concise (2-4 paragraphs max) unless they ask for detailed content.
"""

ROADMAP_PROMPT = """
Create a personalized learning roadmap for this candidate to fill their skill gaps.

Candidate: {name}
Current Skills: {skills}
Skill Gaps: {gaps}
Target Roles: {titles}
Seniority: {seniority}

Return a structured 90-day learning plan with:
1. Week 1-2: Quick wins (skills they're close to having)
2. Month 1: Core gaps to address
3. Month 2-3: Advanced skills for target roles

Be specific with resource recommendations (courses, projects, certifications).
"""


class CareerCoachAgent:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        log.info("CareerCoachAgent initialised")

    def _build_context(
        self,
        user: UserProfile,
        career: CareerProfile | None,
        market: MarketReport | None,
        top_jobs: list[ScoredJob],
    ) -> str:
        lines = [
            f"Candidate: {user.name}",
            f"Skills: {', '.join(user.skills[:15])}",
            f"Experience: {len(user.work_history)} roles",
            f"Resume Score: {user.resume_score}/100",
        ]
        if career:
            lines.append(f"Target Roles: {', '.join(career.ideal_titles[:4])}")
            lines.append(f"Seniority: {career.seniority_level}")
            lines.append(f"Salary Target: ${career.salary_min:,} – ${career.salary_max:,}")
        if market:
            lines.append(f"Skill Gaps: {', '.join(market.skill_gaps[:5])}")
            lines.append(f"Market Insights: {'; '.join(market.market_insights[:2])}")
        if top_jobs:
            lines.append(f"Top Match: {top_jobs[0].overall_match}% — {top_jobs[0].title} @ {top_jobs[0].company}")
        return "\n".join(lines)

    async def chat(
        self,
        user_message: str,
        history: list[ChatMessage],
        user: UserProfile | None = None,
        career: CareerProfile | None = None,
        market: MarketReport | None = None,
        top_jobs: list[ScoredJob] | None = None,
    ) -> tuple[str, list[str]]:
        """
        Process a career coaching conversation turn.
        Returns (reply, list_of_followup_suggestions).
        """
        context = ""
        if user:
            context = self._build_context(user, career, market, top_jobs or [])

        messages = [COACH_SYSTEM_PROMPT]
        if context:
            messages.append(f"\n[Candidate Context]\n{context}\n")

        for msg in history[-10:]:
            prefix = "User" if msg.role == "user" else "Aria"
            messages.append(f"{prefix}: {msg.content}")

        messages.append(f"User: {user_message}")
        messages.append("Aria:")

        full_prompt = "\n".join(messages)
        response = self.model.generate_content(full_prompt)
        reply = response.text.strip()

        # Generate follow-up suggestions
        suggestions = self._get_suggestions(user_message, reply)
        log.info(f"Coach responded to: '{user_message[:50]}...'")
        return reply, suggestions

    def _get_suggestions(self, user_message: str, reply: str) -> list[str]:
        """Generate 3 contextual follow-up question suggestions."""
        lower = user_message.lower()
        if "resume" in lower or "score" in lower:
            return [
                "How do I quantify my achievements?",
                "What skills should I add first?",
                "Can you review my summary section?",
            ]
        elif "salary" in lower or "negotiate" in lower:
            return [
                "What's the best time to negotiate?",
                "How do I handle a lowball offer?",
                "Should I give a salary range?",
            ]
        elif "interview" in lower:
            return [
                "Give me a practice technical question",
                "How do I answer behavioral questions?",
                "What questions should I ask the interviewer?",
            ]
        elif "job" in lower or "match" in lower:
            return [
                "Which job should I apply to first?",
                "How do I improve my match scores?",
                "What skills would unlock more roles?",
            ]
        else:
            return [
                "What's my biggest skill gap?",
                "How can I improve my resume score?",
                "Which roles should I target first?",
            ]

    async def generate_roadmap(
        self,
        user: UserProfile,
        career: CareerProfile,
        market: MarketReport,
    ) -> str:
        """Generate a 90-day personalized learning roadmap."""
        prompt = ROADMAP_PROMPT.format(
            name=user.name or "the candidate",
            skills=", ".join(user.skills[:15]),
            gaps=", ".join(market.skill_gaps[:8]),
            titles=", ".join(career.ideal_titles[:4]),
            seniority=career.seniority_level,
        )
        response = self.model.generate_content(prompt)
        return response.text.strip()

    async def explain_job_match(self, user: UserProfile, job: ScoredJob) -> str:
        """Explain in detail why a specific job is or isn't a match."""
        prompt = f"""
Explain to {user.name or 'this candidate'} why {job.title} at {job.company} is a {job.overall_match}% match.

Their skills: {', '.join(user.skills[:15])}
Job requires: {', '.join(job.requirements[:8])}
Missing skills: {', '.join(job.missing_skills[:5])}

Write 2-3 paragraphs that are encouraging, honest, and specific.
Include what they have, what's missing, and concrete next steps.
"""
        response = self.model.generate_content(prompt)
        return response.text.strip()
