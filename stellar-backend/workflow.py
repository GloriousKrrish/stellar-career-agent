"""
Workflow Orchestrator

Coordinates all 7 agents in sequence, emitting real-time events
via WebSocket pub/sub at each step. Handles retries, state persistence,
and human-in-the-loop escalation.
"""
from __future__ import annotations
import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable

from agents.resume_agent import ResumeIntelligenceAgent
from agents.career_profiler_agent import CareerProfilerAgent
from agents.market_agent import MarketIntelligenceAgent
from agents.discovery_agent import JobDiscoveryAgent
from agents.scoring_agent import MatchScoringAgent
from agents.coach_agent import CareerCoachAgent
from agents.application_agent import ApplicationAgent

from models import (
    WorkflowState, LiveEvent, StartWorkflowRequest,
    UserProfile, ScoredJob,
)
import store
from logger import get_logger

log = get_logger("WorkflowOrchestrator")


async def _emit(run_id: str, event_type: str, agent: str, message: str, data: dict | None = None) -> None:
    """Publish a live event to all WebSocket subscribers of this run."""
    event = LiveEvent(
        run_id=run_id,
        event_type=event_type,
        agent=agent,
        message=message,
        data=data or {},
    )
    await store.publish(run_id, event.model_dump(mode="json"))
    log.info(f"[{run_id[:8]}] [{agent}] {message}")


async def run_full_workflow(
    run_id: str,
    user_profile: UserProfile,
    request: StartWorkflowRequest,
    resume_path: str = "",
) -> WorkflowState:
    """
    Execute the complete agentic pipeline:
      Resume → Career Profiler → Market Intel → Job Discovery → Scoring → Coach

    Each step emits progress events over WebSocket.
    """
    state = store.get_workflow(run_id)
    if not state:
        state = WorkflowState(run_id=run_id, user_id=user_profile.id)

    state.user_profile = user_profile
    state.status = "running"
    store.save_workflow(state)

    try:
        # ── Step 1: Career Profiling ──────────────────────────────────────────
        await _emit(run_id, "progress", "CareerProfiler", "Analysing career trajectory...")
        state.current_step = "career_profiling"
        store.save_workflow(state)

        profiler = CareerProfilerAgent()
        career = await profiler.profile(user_profile)
        state.career_profile = career
        state.steps_completed.append("career_profiling")
        store.save_workflow(state)

        await _emit(run_id, "agent_update", "CareerProfiler",
                    f"Career profile complete - targeting: {', '.join(career.ideal_titles[:3])}",
                    {"titles": career.ideal_titles, "seniority": career.seniority_level})

        # ── Step 2: Market Intelligence ───────────────────────────────────────
        await _emit(run_id, "progress", "MarketIntel", "Scanning current job market...")
        state.current_step = "market_intelligence"
        store.save_workflow(state)

        market_agent = MarketIntelligenceAgent()
        market = await market_agent.analyze(user_profile, career)
        state.market_report = market
        state.steps_completed.append("market_intelligence")
        store.save_workflow(state)

        await _emit(run_id, "agent_update", "MarketIntel",
                    f"Market report ready - {len(market.skill_gaps)} skill gaps identified",
                    {"gaps": market.skill_gaps, "trending": market.trending_skills})

        # ── Step 3: Job Discovery ─────────────────────────────────────────────
        await _emit(run_id, "progress", "JobDiscovery", "Searching Greenhouse, Lever, RemoteOK, YC Jobs...")
        state.current_step = "job_discovery"
        store.save_workflow(state)

        discovery = JobDiscoveryAgent()
        async def on_discovery_progress(msg: str):
            await _emit(run_id, "progress", "JobDiscovery", msg)

        raw_jobs = await discovery.discover(
            user_profile=user_profile,
            career=career,
            role=request.role,
            remote_preference=request.remote_preference,
            limit=25,
            on_progress=on_discovery_progress,
        )
        state.raw_jobs = raw_jobs
        state.steps_completed.append("job_discovery")
        store.save_workflow(state)

        await _emit(run_id, "agent_update", "JobDiscovery",
                    f"Discovered {len(raw_jobs)} job opportunities",
                    {"count": len(raw_jobs), "sources": list({j.source for j in raw_jobs})})

        # Emit individual job_found events
        for job in raw_jobs[:5]:
            await _emit(run_id, "job_found", "JobDiscovery",
                        f"Found: {job.title} at {job.company}",
                        {"title": job.title, "company": job.company, "source": job.source})
            await asyncio.sleep(0.1)

        # ── Step 4: Match Scoring ─────────────────────────────────────────────
        await _emit(run_id, "progress", "MatchScoring", f"Scoring {len(raw_jobs)} jobs against your profile...")
        state.current_step = "match_scoring"
        store.save_workflow(state)

        scorer = MatchScoringAgent()
        scored_jobs = await scorer.score_batch(
            user=user_profile,
            jobs=raw_jobs,
            seniority=career.seniority_level,
            top_n_ai=8,
        )
        state.scored_jobs = scored_jobs
        state.steps_completed.append("match_scoring")
        store.save_workflow(state)

        if scored_jobs:
            top = scored_jobs[0]
            await _emit(run_id, "match_scored", "MatchScoring",
                        f"Top match: {top.overall_match}% - {top.title} at {top.company}",
                        {"top_matches": [j.model_dump(mode="json") for j in scored_jobs[:5]]})

        # ── Step 5: Done ──────────────────────────────────────────────────────
        state.status = "completed"
        state.current_step = "completed"
        state.updated_at = datetime.utcnow()
        store.save_workflow(state)

        await _emit(run_id, "completed", "Aria",
                    f"Workflow complete! Found {len(scored_jobs)} matched roles.",
                    {
                        "total_jobs": len(scored_jobs),
                        "top_match": scored_jobs[0].overall_match if scored_jobs else 0,
                        "run_id": run_id,
                    })

    except Exception as e:
        log.error(f"Workflow {run_id} failed: {e}", exc_info=True)
        state.status = "failed"
        state.error = str(e)
        state.updated_at = datetime.utcnow()
        store.save_workflow(state)
        await _emit(run_id, "error", "Orchestrator", f"Workflow error: {str(e)[:200]}")

    return state


async def run_job_search_workflow(
    run_id: str,
    role: str,
    location: str,
    remote_preference: str,
    limit: int = 20,
) -> WorkflowState:
    """
    Lightweight workflow for quick job searches without a resume.
    Uses Gemini to create a generic career profile, then discovers and scores.
    """
    # Create a minimal profile for the search
    dummy_profile = UserProfile(
        name="Job Seeker",
        summary=f"Looking for {role} opportunities",
        skills=[role],
    )

    request = StartWorkflowRequest(
        role=role,
        location=location,
        remote_preference=remote_preference,
    )

    state = WorkflowState(run_id=run_id, user_id=dummy_profile.id, user_profile=dummy_profile)
    store.save_workflow(state)

    await _emit(run_id, "progress", "Aria", f"Searching for {role} roles...")

    try:
        # Quick profile for search
        profiler = CareerProfilerAgent()
        career = await profiler.profile(dummy_profile)
        career.ideal_titles = [role] + career.ideal_titles[:3]

        discovery = JobDiscoveryAgent()
        async def on_discovery_progress(msg: str):
            await _emit(run_id, "progress", "JobDiscovery", msg)

        raw_jobs = await discovery.discover(dummy_profile, career, role=role,
                                            remote_preference=remote_preference, limit=limit,
                                            on_progress=on_discovery_progress)

        await _emit(run_id, "job_found", "JobDiscovery", f"Found {len(raw_jobs)} roles")

        scorer = MatchScoringAgent()
        scored = await scorer.score_batch(dummy_profile, raw_jobs, career.seniority_level, top_n_ai=5)

        state.career_profile = career
        state.raw_jobs = raw_jobs
        state.scored_jobs = scored
        state.status = "completed"
        store.save_workflow(state)

        await _emit(run_id, "completed", "Aria", f"Found {len(scored)} matched roles for '{role}'",
                    {"jobs": [j.model_dump(mode="json") for j in scored[:10]]})

    except Exception as e:
        state.status = "failed"
        state.error = str(e)
        store.save_workflow(state)
        await _emit(run_id, "error", "Aria", str(e)[:200])

    return state
