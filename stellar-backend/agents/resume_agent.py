"""
Agent 1 — Resume Intelligence Agent

Responsibilities:
- Accept PDF / DOCX / TXT resume bytes
- Extract raw text
- Use Gemini to parse structured profile
- Score ATS compatibility and resume strength
- Detect missing skills
- Return a fully structured UserProfile
"""
from __future__ import annotations
import io
import os
import re
import json
from datetime import datetime
from typing import Any


import google.generativeai as genai

from config import get_settings
from logger import get_logger
from models import UserProfile

log = get_logger("ResumeAgent")
settings = get_settings()


def _extract_text_from_pdf(content: bytes) -> str:
    """Extract raw text from a PDF file."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages)
    except Exception as e:
        log.warning(f"PyPDF2 error: {e}")
        return content.decode("utf-8", errors="ignore")


def _extract_text_from_docx(content: bytes) -> str:
    """Extract raw text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        log.warning(f"python-docx error: {e}")
        return content.decode("utf-8", errors="ignore")


def _extract_text(content: bytes, filename: str) -> str:
    """Route to correct extractor based on file extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_text_from_pdf(content)
    elif lower.endswith(".docx"):
        return _extract_text_from_docx(content)
    else:
        return content.decode("utf-8", errors="ignore")


PARSE_PROMPT = """
You are an expert resume parser. Given the resume text below, extract a complete structured profile.

Return ONLY valid JSON (no markdown, no code fences) with this exact schema:
{{
  "name": "full name or empty string",
  "email": "email or empty",
  "phone": "phone or empty",
  "location": "city, state or country or empty",
  "linkedin": "linkedin URL or empty",
  "github": "github URL or empty",
  "summary": "professional summary or empty",
  "skills": ["skill1", "skill2"],
  "technologies": ["tech1", "tech2"],
  "education": [
    {{"degree": "", "institution": "", "year": "", "field": ""}}
  ],
  "certifications": ["cert1"],
  "work_history": [
    {{
      "title": "",
      "company": "",
      "start_date": "",
      "end_date": "",
      "description": "",
      "achievements": [""]
    }}
  ],
  "projects": [
    {{"name": "", "description": "", "tech_stack": [""], "url": ""}}
  ],
  "languages": ["English"],
  "keywords": ["keyword1", "keyword2"]
}}

Resume Text:
{resume_text}
"""

SCORE_PROMPT = """
You are a senior career coach and ATS expert.

Given this candidate profile JSON, return ONLY valid JSON with:
{{
  "resume_score": <integer 0-100>,
  "ats_score": <integer 0-100>,
  "missing_skills": ["skill1", "skill2"],
  "improvements": [
    "Specific actionable improvement 1",
    "Specific actionable improvement 2",
    "Specific actionable improvement 3"
  ]
}}

Rules:
- resume_score: overall quality, impact, clarity, quantified achievements
- ats_score: keyword density, formatting compatibility, section headers
- missing_skills: high-demand skills absent from the profile
- improvements: 3-5 concrete, specific actions

Profile:
{profile_json}
"""


class ResumeIntelligenceAgent:
    """
    Parses a resume file and returns a fully structured UserProfile.
    Uses Gemini 1.5 Flash for fast, accurate extraction.
    """

    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        log.info("ResumeIntelligenceAgent initialised")

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini and return the raw text response."""
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def _safe_parse_json(self, text: str) -> dict[str, Any]:
        """Strip markdown fences and parse JSON robustly."""
        # Remove ```json ... ``` or ``` ... ```
        clean = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # Try to find first { ... } block
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {}

    def _fallback_parse_text(self, text: str, filename: str) -> dict[str, Any]:
        """Rule-based fallback parser for when Gemini API is rate-limited/down."""
        log.info("Running local rule-based fallback resume parser")
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        email = email_match.group(0) if email_match else ""

        phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        phone = phone_match.group(0) if phone_match else ""

        name = ""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line) < 50 and not "@" in first_line:
                name = first_line
        if not name:
            name = os.path.splitext(filename)[0].replace("-", " ").replace("_", " ").title()

        common_skills = [
            "python", "javascript", "typescript", "react", "node", "express",
            "vue", "angular", "html", "css", "docker", "kubernetes", "aws", "gcp",
            "azure", "sql", "postgresql", "mysql", "mongodb", "redis", "git",
            "java", "c++", "c#", "golang", "rust", "php", "ruby", "django", "fastapi"
        ]
        found_skills = []
        for skill in common_skills:
            pattern = rf"\b{skill}\b"
            if skill == "c++":
                pattern = r"c\+\+"
            if re.search(pattern, text, re.IGNORECASE):
                found_skills.append(skill.title())

        summary = ""
        if len(lines) > 1:
            summary_lines = []
            for line in lines[1:4]:
                if len(line) > 30 and not any(k in line.lower() for k in ["email", "phone", "github", "linkedin"]):
                    summary_lines.append(line)
            summary = " ".join(summary_lines)
        if not summary:
            summary = "Experienced professional with background in technology and software development."

        return {
            "name": name,
            "email": email,
            "phone": phone,
            "location": "Remote",
            "linkedin": "",
            "github": "",
            "summary": summary,
            "skills": found_skills,
            "technologies": found_skills,
            "education": [],
            "certifications": [],
            "work_history": [],
            "projects": [],
            "languages": ["English"],
            "keywords": found_skills
        }

    def _fallback_score_profile(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Generate static scoring when Gemini is rate-limited/down."""
        skills = parsed.get("skills", [])
        resume_score = min(70 + len(skills) * 2, 92)
        ats_score = min(65 + len(skills) * 2, 88)
        
        all_demand = ["System Design", "CI/CD", "Unit Testing", "Microservices", "Cloud Architecture"]
        missing_skills = [s for s in all_demand if s not in skills][:3]
        if not missing_skills:
            missing_skills = ["System Design", "CI/CD"]

        return {
            "resume_score": resume_score,
            "ats_score": ats_score,
            "missing_skills": missing_skills,
            "improvements": [
                "Add quantified impact metrics (e.g. 'improved latency by 20%') to work experience bullets.",
                "Include a dedicated section highlighting core technologies and languages.",
                "Ensure resume layout uses standard machine-readable fonts and section headers."
            ]
        }

    async def parse(self, content: bytes, filename: str) -> UserProfile:
        """Main entry: extract text → parse → score → return UserProfile."""
        log.info(f"Parsing resume: {filename}")
        raw_text = _extract_text(content, filename)

        if not raw_text.strip():
            raise ValueError("Empty resume text extracted. Please upload a valid document.")

        # Step 1: Parse structured profile
        parse_prompt = PARSE_PROMPT.format(resume_text=raw_text[:8000])
        try:
            parse_response = self._call_gemini(parse_prompt)
            parsed = self._safe_parse_json(parse_response)
        except Exception as e:
            log.error(f"Gemini parse failed: {e}")
            raise ValueError(f"Resume analysis failed during Gemini extraction: {str(e)}")

        if not parsed or not parsed.get("name") or not parsed.get("skills"):
            raise ValueError("Failed to extract structural profile details from resume using Gemini.")

        # Step 2: Score and identify gaps
        score_prompt = SCORE_PROMPT.format(profile_json=json.dumps(parsed, indent=2)[:4000])
        try:
            score_response = self._call_gemini(score_prompt)
            scored = self._safe_parse_json(score_response)
        except Exception as e:
            log.error(f"Gemini score failed: {e}")
            raise ValueError(f"Resume scoring failed during Gemini evaluation: {str(e)}")

        if not scored or "resume_score" not in scored or "ats_score" not in scored:
            raise ValueError("Failed to score candidate profile using Gemini.")

        profile = UserProfile(
            name=parsed.get("name", ""),
            email=parsed.get("email", ""),
            phone=parsed.get("phone", ""),
            location=parsed.get("location", ""),
            linkedin=parsed.get("linkedin", ""),
            github=parsed.get("github", ""),
            summary=parsed.get("summary", ""),
            skills=parsed.get("skills", []),
            technologies=parsed.get("technologies", []),
            education=parsed.get("education", []),
            certifications=parsed.get("certifications", []),
            work_history=parsed.get("work_history", []),
            projects=parsed.get("projects", []),
            languages=parsed.get("languages", ["English"]),
            keywords=parsed.get("keywords", []),
            resume_score=scored.get("resume_score", 0),
            ats_score=scored.get("ats_score", 0),
            missing_skills=scored.get("missing_skills", []),
            improvements=scored.get("improvements", []),
            raw_text=raw_text,
        )

        log.info(f"Resume parsed successfully: {profile.name} | score={profile.resume_score} | skills={len(profile.skills)}")
        return profile
