"""
All Pydantic V2 data models for the Stellar Career Agent platform.
These models are shared between agents, services, and API layer.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from uuid import uuid4


# ─── Core identity ────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    """Structured output of the Resume Intelligence Agent."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    summary: str = ""
    skills: list[str] = []
    technologies: list[str] = []
    education: list[dict[str, str]] = []
    certifications: list[str] = []
    work_history: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    languages: list[str] = []
    keywords: list[str] = []
    resume_score: int = 0
    ats_score: int = 0
    missing_skills: list[str] = []
    improvements: list[str] = []
    raw_text: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CareerProfile(BaseModel):
    """Structured output of the Career Profiler Agent."""
    user_id: str
    career_paths: list[str] = []
    ideal_titles: list[str] = []
    seniority_level: str = "Mid"
    industries: list[str] = []
    salary_min: int = 0
    salary_max: int = 0
    salary_currency: str = "INR"
    strengths: list[str] = []
    growth_areas: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MarketReport(BaseModel):
    """Structured output of the Market Intelligence Agent."""
    user_id: str
    trending_skills: list[str] = []
    in_demand_roles: list[str] = []
    skill_gaps: list[str] = []
    recommended_certifications: list[str] = []
    market_insights: list[str] = []
    avg_salary_range: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Jobs ─────────────────────────────────────────────────────────────────────

class RawJob(BaseModel):
    """A job as discovered from the web by the Job Discovery Agent."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    company: str
    location: str = ""
    remote: Literal["Remote", "Hybrid", "Onsite"] = "Onsite"
    salary: str = ""
    salary_min: int = 0
    salary_max: int = 0
    experience: Literal["Entry", "Mid", "Senior", "Staff", "Principal"] = "Mid"
    description: str = ""
    requirements: list[str] = []
    responsibilities: list[str] = []
    nice_to_have: list[str] = []
    benefits: list[str] = []
    skills: list[str] = []
    url: str = ""
    source: str = ""
    posted_at: str = ""
    industry: str = ""
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


class ScoredJob(RawJob):
    """A job enriched with match scores from the Match Scoring Agent."""
    semantic_score: float = 0.0
    skill_overlap_score: float = 0.0
    experience_score: float = 0.0
    overall_match: int = 0
    match_reasons: list[str] = []
    missing_skills: list[str] = []
    ai_recommendation: str = ""
    company_logo: str = ""


# ─── Workflow / Agent State ────────────────────────────────────────────────────

class AgentStatus(BaseModel):
    agent_id: str
    name: str
    status: Literal["idle", "active", "thinking", "paused", "error", "done"] = "idle"
    progress: int = 0
    tasks_today: int = 0
    tasks_total: int = 0
    current_task: str = ""
    recent_actions: list[dict[str, str]] = []
    error_message: str = ""


class WorkflowState(BaseModel):
    """Persisted state for long-running agentic workflows."""
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    status: Literal["pending", "running", "paused", "completed", "failed", "action_required"] = "pending"
    current_step: str = ""
    steps_completed: list[str] = []
    user_profile: Optional[UserProfile] = None
    career_profile: Optional[CareerProfile] = None
    market_report: Optional[MarketReport] = None
    raw_jobs: list[RawJob] = []
    scored_jobs: list[ScoredJob] = []
    error: str = ""
    # Human-in-the-loop
    action_required: Optional[ActionRequiredResponse] = None
    action_required_reason: str = ""
    action_required_url: str = ""
    action_required_screenshot: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LiveEvent(BaseModel):
    """Real-time event emitted over WebSocket."""
    run_id: str
    event_type: Literal["progress", "agent_update", "job_found", "match_scored",
                        "action_required", "completed", "error", "log"]
    agent: str = ""
    message: str = ""
    data: dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── API Request / Response Schemas ───────────────────────────────────────────

class StartWorkflowRequest(BaseModel):
    role: str = ""
    location: str = ""
    remote_preference: str = "Remote"
    experience_level: str = "Mid"
    salary_min: int = 0
    salary_max: int = 500000


class WorkflowResponse(BaseModel):
    run_id: str
    status: str
    message: str
    data: dict[str, Any] = {}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    run_id: Optional[str] = None
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    suggestions: list[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ActionRequiredResponse(BaseModel):
    status: Literal["ACTION_REQUIRED"] = "ACTION_REQUIRED"
    reason: str
    url: str
    screenshot: str
    run_id: str = ""


class JobSearchRequest(BaseModel):
    role: str
    location: str = ""
    remote_preference: str = "Remote"
    limit: int = 20


class DirectJobSearchRequest(BaseModel):
    role: str
    location: str = ""
    salary_target: str = ""

