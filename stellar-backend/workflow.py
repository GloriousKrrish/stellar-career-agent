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

    Each step emits progress events over WebSocket. Supports fault-tolerant resumption.
    """
    import db
    import json
    import re

    state = store.get_workflow(run_id)
    if not state:
        state = WorkflowState(run_id=run_id, user_id=user_profile.id)

    if request.role and request.role not in user_profile.skills:
        user_profile.skills = list(user_profile.skills) + [request.role]

    state.user_profile = user_profile
    state.status = "running"
    store.save_workflow(state)

    # Save progress to job_tasks
    db.db_save_job_task({
        "id": run_id,
        "user_id": user_profile.id,
        "run_id": run_id,
        "status": "processing",
        "current_page": 1,
        "target_platforms": "naukri,glassdoor,remoteok",
        "last_heartbeat": datetime.utcnow().isoformat(),
        "payload": json.dumps(request.model_dump())
    })

    try:
        # ── Step 1: Career Profiling ──────────────────────────────────────────
        if "career_profiling" not in state.steps_completed:
            await _emit(run_id, "progress", "CareerProfiler", "Analysing career trajectory...")
            state.current_step = "career_profiling"
            store.save_workflow(state)

            profiler = CareerProfilerAgent()
            career = await profiler.profile(user_profile)
            if request.role:
                career.ideal_titles = [request.role] + [t for t in career.ideal_titles if t.lower() != request.role.lower()]
            state.career_profile = career
            state.steps_completed.append("career_profiling")
            store.save_workflow(state)
        else:
            career = state.career_profile
            await _emit(run_id, "progress", "CareerProfiler", "Resumed: loaded career profile from previous run.")

        db.db_update_task_heartbeat(run_id, current_page=1, status="processing")

        await _emit(run_id, "agent_update", "CareerProfiler",
                    f"Career profile complete - targeting: {', '.join(career.ideal_titles[:3])}",
                    {"titles": career.ideal_titles, "seniority": career.seniority_level})

        # ── Step 2: Market Intelligence ───────────────────────────────────────
        if "market_intelligence" not in state.steps_completed:
            await _emit(run_id, "progress", "MarketIntel", "Scanning current job market...")
            state.current_step = "market_intelligence"
            store.save_workflow(state)

            market_agent = MarketIntelligenceAgent()
            market = await market_agent.analyze(user_profile, career)
            state.market_report = market
            state.steps_completed.append("market_intelligence")
            store.save_workflow(state)
        else:
            market = state.market_report
            await _emit(run_id, "progress", "MarketIntel", "Resumed: loaded market report from previous run.")

        db.db_update_task_heartbeat(run_id, current_page=2, status="processing")

        await _emit(run_id, "agent_update", "MarketIntel",
                    f"Market report ready - {len(market.skill_gaps)} skill gaps identified",
                    {"gaps": market.skill_gaps, "trending": market.trending_skills})

        # ── Step 3: Job Discovery ─────────────────────────────────────────────
        if "job_discovery" not in state.steps_completed:
            await _emit(run_id, "progress", "JobDiscovery", "Searching Greenhouse, Lever, RemoteOK, YC Jobs...")
            state.current_step = "job_discovery"
            store.save_workflow(state)

            discovery = JobDiscoveryAgent()
            async def on_discovery_progress(msg: str):
                await _emit(run_id, "progress", "JobDiscovery", msg)
                # Parse page if present in message and save chunk progress
                page_match = re.search(r"page\s+(\d+)", msg, re.IGNORECASE)
                page_val = int(page_match.group(1)) if page_match else None
                db.db_update_task_heartbeat(run_id, current_page=page_val, status="processing")

            salary_target_val = ""
            if request.salary_min:
                salary_target_val = f"₹{request.salary_min // 100000} LPA"

            raw_jobs = await discovery.discover(
                user_profile=user_profile,
                career=career,
                role=request.role,
                location=request.location,
                salary_target=salary_target_val,
                remote_preference=request.remote_preference,
                limit=25,
                on_progress=on_discovery_progress,
            )
            state.raw_jobs = raw_jobs
            state.steps_completed.append("job_discovery")
            store.save_workflow(state)
        else:
            raw_jobs = state.raw_jobs
            await _emit(run_id, "progress", "JobDiscovery", f"Resumed: loaded {len(raw_jobs)} discovered jobs.")

        db.db_update_task_heartbeat(run_id, current_page=3, status="processing")

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
        if "match_scoring" not in state.steps_completed:
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
        else:
            scored_jobs = state.scored_jobs
            await _emit(run_id, "progress", "MatchScoring", f"Resumed: loaded {len(scored_jobs)} scored jobs.")

        db.db_update_task_heartbeat(run_id, current_page=4, status="processing")

        if scored_jobs:
            top = scored_jobs[0]
            await _emit(run_id, "match_scored", "MatchScoring",
                        f"Top match: {top.overall_match}% - {top.title} at {top.company}",
                        {"top_matches": [j.model_dump(mode="json") for j in scored_jobs[:5]]})

        # ── Step 5: Enqueue for AutoApply ─────────────────────────────────────
        try:
            from agents.orchestrator import enqueue_discovered_jobs
            enqueued = enqueue_discovered_jobs(
                user_id=user_profile.id,
                run_id=run_id,
                scored_jobs=scored_jobs,
                auto_apply_threshold=70,
            )
            if enqueued > 0:
                await _emit(run_id, "agent_update", "AutoApply",
                            f"Queued {enqueued} high-match jobs for autonomous application",
                            {"enqueued": enqueued})
        except Exception as e:
            log.warning(f"AutoApply enqueue failed (non-fatal): {e}")

        # ── Step 6: Done ──────────────────────────────────────────────────────
        state.status = "completed"
        state.current_step = "completed"
        state.updated_at = datetime.utcnow()
        store.save_workflow(state)

        db.db_update_task_heartbeat(run_id, current_page=5, status="completed")

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

        db.db_update_task_heartbeat(run_id, status="failed")

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
    import db
    import json

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

    # Save to job_tasks
    db.db_save_job_task({
        "id": run_id,
        "user_id": dummy_profile.id,
        "run_id": run_id,
        "status": "processing",
        "current_page": 1,
        "target_platforms": "naukri,glassdoor,remoteok",
        "last_heartbeat": datetime.utcnow().isoformat(),
        "payload": json.dumps(request.model_dump())
    })

    await _emit(run_id, "progress", "Aria", f"Searching for {role} roles...")

    try:
        # Quick profile for search
        profiler = CareerProfilerAgent()
        career = await profiler.profile(dummy_profile)
        career.ideal_titles = [role] + career.ideal_titles[:3]

        db.db_update_task_heartbeat(run_id, current_page=1, status="processing")

        discovery = JobDiscoveryAgent()
        async def on_discovery_progress(msg: str):
            await _emit(run_id, "progress", "JobDiscovery", msg)
            import re
            page_match = re.search(r"page\s+(\d+)", msg, re.IGNORECASE)
            page_val = int(page_match.group(1)) if page_match else None
            db.db_update_task_heartbeat(run_id, current_page=page_val, status="processing")

        raw_jobs = await discovery.discover(
            user_profile=dummy_profile,
            career=career,
            role=role,
            location=location,
            remote_preference=remote_preference,
            limit=limit,
            on_progress=on_discovery_progress,
        )

        db.db_update_task_heartbeat(run_id, current_page=2, status="processing")

        await _emit(run_id, "job_found", "JobDiscovery", f"Found {len(raw_jobs)} roles")

        scorer = MatchScoringAgent()
        scored = await scorer.score_batch(dummy_profile, raw_jobs, career.seniority_level, top_n_ai=5)

        state.career_profile = career
        state.raw_jobs = raw_jobs
        state.scored_jobs = scored
        state.status = "completed"
        store.save_workflow(state) 

        db.db_update_task_heartbeat(run_id, current_page=3, status="completed")

        await _emit(run_id, "completed", "Aria", f"Found {len(scored)} matched roles for '{role}'",
                    {"jobs": [j.model_dump(mode="json") for j in scored[:10]]})

    except Exception as e:
        state.status = "failed"
        state.error = str(e)
        store.save_workflow(state)
        db.db_update_task_heartbeat(run_id, status="failed")
        await _emit(run_id, "error", "Aria", str(e)[:200])

    return state


async def resume_interrupted_workflows(background_tasks: Any = None) -> int:
    """
    Scan the database for pending or processing tasks that were interrupted.
    Resumes them by kicking off background tasks.
    """
    import db
    import json
    active_tasks = db.db_get_active_tasks()
    log.info(f"Crash Recovery: Found {len(active_tasks)} pending or interrupted tasks in database.")

    resumed_count = 0
    for task in active_tasks:
        run_id = task["run_id"]
        # Fetch matching workflow from DB
        state = store.get_workflow(run_id)
        if not state or not state.user_profile:
            log.warning(f"Crash Recovery: Workflow {run_id} has no stored profile or state. Marking as failed.")
            db.db_update_task_heartbeat(run_id, status="failed")
            continue

        try:
            payload_data = json.loads(task.get("payload", "{}"))
        except Exception:
            payload_data = {}

        req = StartWorkflowRequest(
            role=payload_data.get("role") or (state.career_profile.ideal_titles[0] if state.career_profile and state.career_profile.ideal_titles else "Software Engineer"),
            location=payload_data.get("location") or "India",
            remote_preference=payload_data.get("remote_preference") or "Remote",
        )

        log.info(f"Crash Recovery: Resuming workflow {run_id} for role '{req.role}'...")

        if background_tasks:
            background_tasks.add_task(run_full_workflow, run_id, state.user_profile, req, "")
        else:
            asyncio.create_task(run_full_workflow(run_id, state.user_profile, req, ""))

        resumed_count += 1

    return resumed_count


async def start_heartbeat_monitor():
    """
    Background worker that runs continuously.
    Checks the database for 'processing' tasks that haven't updated their heartbeat in >2 minutes.
    Attempts to resume them.
    """
    import db
    import json
    log.info("Starting heartbeat monitoring background loop...")
    while True:
        try:
            await asyncio.sleep(30)
            stale_tasks = db.db_get_stale_tasks(timeout_seconds=120)
            if stale_tasks:
                log.warning(f"Heartbeat Monitor: Found {len(stale_tasks)} stale tasks (no heartbeat for >2 minutes).")
                for task in stale_tasks:
                    run_id = task["run_id"]
                    log.warning(f"Heartbeat Monitor: Task {run_id} is stale. Attempting crash recovery...")
                    state = store.get_workflow(run_id)
                    if state and state.user_profile:
                        try:
                            payload_data = json.loads(task.get("payload", "{}"))
                        except Exception:
                            payload_data = {}
                        req = StartWorkflowRequest(
                            role=payload_data.get("role") or "Software Engineer",
                            location=payload_data.get("location") or "India",
                            remote_preference=payload_data.get("remote_preference") or "Remote",
                        )
                        asyncio.create_task(run_full_workflow(run_id, state.user_profile, req, ""))
                        log.info(f"Heartbeat Monitor: Resumed stale task {run_id}.")
                    else:
                        db.db_update_task_heartbeat(run_id, status="failed")
                        log.error(f"Heartbeat Monitor: Failed to resume stale task {run_id} (missing profile). Marked as failed.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error(f"Error in heartbeat monitor loop: {e}", exc_info=True)
