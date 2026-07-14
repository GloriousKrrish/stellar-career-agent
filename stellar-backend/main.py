"""
Stellar Career Agent — Production FastAPI Backend
=================================================
Enterprise-grade Agentic AI Job Finder Platform

Endpoints:
  POST /api/resume/upload          — Upload & parse resume
  GET  /api/resume/{run_id}        — Get parsed profile
  POST /api/workflow/start         — Start full agentic workflow
  GET  /api/workflow/{run_id}      — Get workflow state
  GET  /api/workflow/{run_id}/jobs — Get scored jobs
  POST /api/jobs/search            — Quick job search (no resume)
  GET  /api/jobs/{job_id}/explain  — AI explanation for a specific job match
  POST /api/chat                   — Career coach chat
  POST /api/apply/{job_id}         — Trigger application agent
  GET  /api/agents/status          — Live agent status board
  WS   /ws/{run_id}               — Real-time event stream

Author: Stellar Career Agent Platform
Version: 2.0.0
"""
from __future__ import annotations
import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Optional

from fastapi import (
    FastAPI, File, Form, HTTPException, UploadFile,
    WebSocket, WebSocketDisconnect, BackgroundTasks, Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import aiofiles
from pydantic import BaseModel

from config import get_settings
from logger import get_logger
from models import (
    ChatRequest, ChatResponse, JobSearchRequest,
    LiveEvent, StartWorkflowRequest, UserProfile,
    WorkflowResponse, AgentStatus, DirectJobSearchRequest,
)
import store
from workflow import run_full_workflow, run_job_search_workflow
from agents.resume_agent import ResumeIntelligenceAgent
from agents.coach_agent import CareerCoachAgent
from agents.scoring_agent import MatchScoringAgent
from agents.application_agent import ApplicationAgent
from fastapi import Header
from auth import RegisterRequest, LoginRequest, register_user, login_user, get_user_by_token, GoogleLoginRequest, google_auth_user


log = get_logger("API")
settings = get_settings()


async def directApplyExecutor(job_url: str, run_id: str, user_id: str):
    import asyncio
    import os
    import sys
    
    async def emit_log(msg: str, event_type: str = "log"):
        from models import LiveEvent
        import store
        import db
        print(f"[directApplyExecutor] {msg}")
        event = LiveEvent(
            run_id=run_id,
            event_type=event_type,
            agent="AutoApplyAgent",
            message=msg,
            data={},
        )
        await store.publish(run_id, event.model_dump(mode="json"))
        if user_id:
            try:
                db.db_save_agent_log(user_id, "autoapply", msg, "info")
            except Exception:
                pass

    await emit_log("🚀 Launching headful browser automation...")
    
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    js_path = os.path.join(root_dir, "directApplyExecutor.js")
    
    if not os.path.exists(js_path):
        js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "directApplyExecutor.js")
        
    cmd = ["node", js_path, job_url]
    await emit_log("Spawning direct hit execution subprocess...")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=os.path.dirname(js_path)
        )
        
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode('utf-8', errors='replace').strip()
            if text:
                if "❌ Failed:" in text or "❌ Error:" in text or "❌" in text:
                    await emit_log(text, "error")
                else:
                    await emit_log(text)
                
        await process.wait()
        if process.returncode == 0:
            await emit_log("✅ Browser automation finished successfully.", "completed")
        else:
            await emit_log(f"❌ Browser automation finished with exit code {process.returncode}.", "error")
            
    except Exception as e:
        await emit_log(f"❌ Error executing browser automation: {str(e)}", "error")


async def get_current_user(authorization: str = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: No Bearer token provided")
    token = authorization.split(" ", 1)[1]
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token or expired session")
    return user


async def get_current_user_optional(authorization: str = Header(None)) -> dict[str, Any] | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        user = get_user_by_token(token)
        return user
    except Exception:
        return None

# ─── Startup / Shutdown ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs("screenshots", exist_ok=True)
    log.info("[Start] Stellar Career Agent API starting up")
    log.info(f"   Environment : {settings.app_env}")
    log.info(f"   Gemini Key  : {'set' if settings.gemini_api_key else 'missing'}")
    log.info(f"   Frontend URL: {settings.frontend_url}")

    # Seed agent statuses
    for agent_def in [
        ("resume", "Resume Intelligence", "idle"),
        ("profiler", "Career Profiler", "idle"),
        ("market", "Market Intelligence", "idle"),
        ("discovery", "Job Discovery", "idle"),
        ("scoring", "Match Scoring", "idle"),
        ("coach", "Career Coach", "active"),
        ("application", "Application Agent", "idle"),
        ("autoapply", "AutoApply Agent", "idle"),
    ]:
        store.update_agent_status(AgentStatus(
            agent_id=agent_def[0],
            name=agent_def[1],
            status=agent_def[2],
        ))

    # Crash recovery: Resume any pending/interrupted workflows on boot
    from workflow import resume_interrupted_workflows, start_heartbeat_monitor
    try:
        await resume_interrupted_workflows()
    except Exception as e:
        log.error(f"Error resuming interrupted workflows on startup: {e}", exc_info=True)

    # Start the periodic heartbeat monitor background worker task
    app.state.heartbeat_monitor_task = asyncio.create_task(start_heartbeat_monitor())

    # Start the AutoApply orchestrator background loop
    from agents.orchestrator import run_orchestrator_loop
    app.state.orchestrator_task = asyncio.create_task(run_orchestrator_loop())
    log.info("AutoApply orchestrator background loop started")

    yield

    # Cancel heartbeat monitor on shutdown
    if hasattr(app.state, "heartbeat_monitor_task"):
        app.state.heartbeat_monitor_task.cancel()

    # Cancel orchestrator on shutdown
    if hasattr(app.state, "orchestrator_task"):
        app.state.orchestrator_task.cancel()

    log.info("Stellar Career Agent API shutting down")


# ─── App Init ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Stellar Career Agent API",
    version="2.0.0",
    description="Production-grade Agentic AI Job Finder Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://stellar-career-agent-main.vercel.app",
        "https://stellar-career-agent-main-git-main-gloriouskrrishs-projects.vercel.app",
        settings.frontend_url,
        # Allow all Vercel preview URLs
        *([s.strip() for s in os.environ.get("EXTRA_CORS_ORIGINS", "").split(",") if s.strip()]),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Stellar Career Agent API",
        "version": "3.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "agents": 8,
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ─── Resume ───────────────────────────────────────────────────────────────────

@app.post("/api/resume/upload", tags=["Resume"])
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_start_workflow: bool = Form(default=False),
    role: str = Form(default=""),
    remote_preference: str = Form(default="Remote"),
    current_user: dict[str, Any] | None = Depends(get_current_user_optional)
):
    """
    Upload a resume (PDF/DOCX/TXT) and trigger AI parsing.
    Optionally start the full agentic workflow automatically.
    """
    allowed = {".pdf", ".docx", ".doc", ".txt"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not supported. Use PDF, DOCX, or TXT.")

    # Save file
    run_id = str(uuid.uuid4())
    save_path = os.path.join(settings.upload_dir, f"{run_id}{ext}")

    content = await file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.max_file_size_mb}MB.")

    async with aiofiles.open(save_path, "wb") as f:
        await f.write(content)

    log.info(f"Resume uploaded: {file.filename} → {save_path} ({len(content):,} bytes)")

    # Parse resume
    try:
        agent = ResumeIntelligenceAgent()
        profile = await agent.parse(content, file.filename or "resume.pdf")
    except Exception as e:
        log.error(f"Resume parsing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resume parsing failed: {str(e)}")

    if current_user:
        profile.id = current_user["id"]

    # Run Career Profiler Agent immediately to generate role suggestions, location defaults, and salary ranges
    career = None
    try:
        from agents.career_profiler_agent import CareerProfilerAgent
        profiler = CareerProfilerAgent()
        career = await profiler.profile(profile)
    except Exception as e:
        log.error(f"Career profiling failed during resume upload: {e}", exc_info=True)

    # Persist candidate profile
    if current_user:
        try:
            import auth
            import db as database
            auth.update_user_profile(current_user["email"], {
                "title": profile.skills[0] if profile.skills else "",
                "location": profile.location,
                "skills": profile.skills,
                "keywords": profile.keywords,
                "resume_score": profile.resume_score,
                "ats_score": profile.ats_score,
                "missing_skills": profile.missing_skills,
                "improvements": profile.improvements,
                "run_id": run_id,
                "raw_text": profile.raw_text,
            })
            # Save logs to agent_logs table
            database.db_save_agent_log(
                user_id=current_user["id"],
                agent="resume",
                text=f"Re-indexed resume after upload: {file.filename}",
                kind="info"
            )
            if profile.skills:
                database.db_save_agent_log(
                    user_id=current_user["id"],
                    agent="resume",
                    text=f"Detected new skills: {', '.join(profile.skills[:5])}",
                    kind="info"
                )
        except Exception as e:
            log.error(f"Failed to persist candidate profile or save log: {e}", exc_info=True)

    # Create initial workflow state
    from models import WorkflowState
    state = WorkflowState(
        run_id=run_id,
        user_id=profile.id,
        user_profile=profile,
        career_profile=career,
        status="pending"
    )
    store.save_workflow(state)

    response_data: dict[str, Any] = {
        "run_id": run_id,
        "status": "parsed",
        "profile": profile.model_dump(mode="json"),
        "career_profile": career.model_dump(mode="json") if career else None,
        "message": f"Resume parsed successfully. Found {len(profile.skills)} skills.",
    }

    # Optionally kick off full workflow in background
    if auto_start_workflow:
        req = StartWorkflowRequest(role=role, remote_preference=remote_preference)
        background_tasks.add_task(run_full_workflow, run_id, profile, req, save_path)
        response_data["workflow_started"] = True
        response_data["ws_url"] = f"ws://localhost:{settings.backend_port}/ws/{run_id}"

    return JSONResponse(content=response_data)


@app.get("/api/resume/{run_id}", tags=["Resume"])
async def get_resume_profile(run_id: str):
    """Get the parsed user profile for a run."""
    state = store.get_workflow(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")
    if not state.user_profile:
        raise HTTPException(status_code=404, detail="Profile not yet available")
    return state.user_profile.model_dump(mode="json")


# ─── Workflow ─────────────────────────────────────────────────────────────────

@app.post("/api/workflow/start", tags=["Workflow"])
async def start_workflow(
    background_tasks: BackgroundTasks,
    request: StartWorkflowRequest,
    run_id: str | None = None,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
):
    """
    Start (or restart) the full agentic workflow.
    If run_id is provided and has a parsed profile, reuses it.
    Otherwise creates a minimal profile from the request.
    """
    if run_id:
        state = store.get_workflow(run_id)
        user_profile = state.user_profile if state else None
    else:
        user_profile = None
        run_id = str(uuid.uuid4())

    if not user_profile:
        if current_user:
            import db
            db_user = db.get_user_by_id(current_user["id"])
            if db_user:
                user_profile = UserProfile(
                    id=db_user["id"],
                    name=db_user["name"],
                    email=db_user["email"],
                    location=db_user.get("location", ""),
                    skills=db_user.get("skills", []) or [],
                    resume_score=db_user.get("resume_score", 0),
                    ats_score=db_user.get("ats_score", 0),
                )
        if not user_profile:
            user_profile = UserProfile(
                name=current_user["name"] if current_user else "Job Seeker",
                email=current_user["email"] if current_user else "",
                summary=f"Looking for {request.role} roles",
                skills=[request.role] if request.role else [],
            )

    if current_user:
        user_profile.id = current_user["id"]
        user_profile.name = current_user["name"]
        user_profile.email = current_user["email"]

    from models import WorkflowState
    state = WorkflowState(run_id=run_id, user_id=user_profile.id, status="pending")
    store.save_workflow(state)

    background_tasks.add_task(run_full_workflow, run_id, user_profile, request, "")

    return {
        "run_id": run_id,
        "status": "started",
        "message": "Agentic workflow started. Connect to WebSocket for live updates.",
        "ws_url": f"ws://localhost:{settings.backend_port}/ws/{run_id}",
    }


@app.get("/api/workflow/{run_id}", tags=["Workflow"])
async def get_workflow_state(run_id: str):
    """Get the current state of a workflow run."""
    state = store.get_workflow(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return state.model_dump(mode="json", exclude={"raw_jobs", "scored_jobs"})


@app.get("/api/workflow/{run_id}/jobs", tags=["Workflow"])
async def get_workflow_jobs(run_id: str, limit: int = 20, min_match: int = 0):
    """Get scored jobs from a completed workflow."""
    state = store.get_workflow(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    jobs = [j for j in state.scored_jobs if j.overall_match >= min_match]
    jobs_sorted = sorted(jobs, key=lambda j: j.overall_match, reverse=True)

    return {
        "run_id": run_id,
        "total": len(jobs_sorted),
        "jobs": [j.model_dump(mode="json") for j in jobs_sorted[:limit]],
    }


@app.get("/api/workflow/{run_id}/report", tags=["Workflow"])
async def get_workflow_report(run_id: str):
    """Get the complete analysis report: profile + career + market + top jobs."""
    state = store.get_workflow(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "run_id": run_id,
        "status": state.status,
        "user_profile": state.user_profile.model_dump(mode="json") if state.user_profile else None,
        "career_profile": state.career_profile.model_dump(mode="json") if state.career_profile else None,
        "market_report": state.market_report.model_dump(mode="json") if state.market_report else None,
        "top_jobs": [j.model_dump(mode="json") for j in state.scored_jobs[:10]],
        "steps_completed": state.steps_completed,
    }


# ─── Jobs ─────────────────────────────────────────────────────────────────────

@app.post("/api/jobs/search", tags=["Jobs"])
async def search_jobs(
    request: JobSearchRequest,
    background_tasks: BackgroundTasks,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
):
    """
    Quick job search without requiring a resume.
    Kicks off a lightweight discovery + scoring workflow.
    """
    run_id = str(uuid.uuid4())
    user_id = current_user["id"] if current_user else None
    background_tasks.add_task(
        run_job_search_workflow,
        run_id, request.role, request.location,
        request.remote_preference, request.limit,
        user_id,
    )
    return {
        "run_id": run_id,
        "status": "searching",
        "message": f"Searching for {request.role} roles…",
        "ws_url": f"ws://localhost:{settings.backend_port}/ws/{run_id}",
    }


@app.post("/api/jobs/direct-search", tags=["Jobs"])
async def direct_job_search(
    request: DirectJobSearchRequest,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional)
):
    """
    Direct Job Search Portal endpoint.
    Operates independently of the Resume Agent pipeline.
    Does not require Gemini analysis or agent orchestration.
    """
    import re
    from job_providers import search_jobs_resilient

    role = request.role.strip()
    if not role:
        raise HTTPException(status_code=400, detail="Job Role is required.")

    location = request.location.strip()
    salary_target = request.salary_target.strip()

    # Search using the resilient multi-provider pipeline
    try:
        all_jobs_raw, provider_used = await search_jobs_resilient(
            role=role,
            location=location,
            salary_target=salary_target,
            firecrawl_key=settings.firecrawl_api_key,
            rapidapi_key="",
            direct_search=True,
        )
    except Exception as e:
        log.error(f"Direct job search crawler error: {e}", exc_info=True)
        all_jobs_raw = []
        provider_used = "error_boundary_fallback"

    # Filter to ensure only NAUKRI or GLASSDOOR jobs are returned, completely stripping out any others
    allowed_sources = {"naukri", "glassdoor"}
    all_jobs_raw = [j for j in all_jobs_raw if j.get("source", "").lower() in allowed_sources]

    log.info(f"Direct search got {len(all_jobs_raw)} jobs from {provider_used}")

    # Role Matching — filter jobs where title contains at least one role keyword
    role_terms = [w.lower() for w in re.findall(r'\b\w{3,}\b', role)]
    if not role_terms:
        role_terms = [role.lower()]

    filtered_jobs = []
    for job in all_jobs_raw:
        title_lower = job.get("title", "").lower()
        if any(term in title_lower for term in role_terms):
            filtered_jobs.append(job)

    # If filtering removed everything (e.g. very generic role), use all jobs
    if not filtered_jobs:
        filtered_jobs = all_jobs_raw

    # Ranking
    ranked_jobs = []
    target_lpa = None
    if salary_target:
        sal_nums = re.findall(r'\d+', salary_target)
        if sal_nums:
            target_lpa = float(sal_nums[0])

    # Resume skills for matching if user is logged in
    user_skills = []
    if current_user and current_user.get("skills"):
        user_skills = current_user["skills"]

    for job in filtered_jobs:
        score = 0.0

        # A. Location Match
        if location:
            loc_lower = location.lower()
            job_loc_lower = job.get("location", "").lower()
            if loc_lower in job_loc_lower:
                score += 30.0
            elif "remote" in loc_lower and "remote" in job_loc_lower:
                score += 30.0

        # B. Salary Match
        if target_lpa:
            job_sal_str = job.get("salary", "").lower()
            is_undisclosed = (
                not job_sal_str or
                any(k in job_sal_str for k in ["open", "undisclose", "competit", "negotiable", "n/a", "not disclosed"])
            )
            if is_undisclosed:
                score += 10.0
            else:
                job_nums = [float(x.replace(",", "")) for x in re.findall(r'\d+[\d,.]*', job_sal_str)]
                if job_nums:
                    job_lpa = max(job_nums)
                    if job_lpa >= 100000:
                        job_lpa /= 100000.0
                    if job_lpa >= target_lpa:
                        score += 20.0
                    else:
                        score += 20.0 * (job_lpa / target_lpa)

        # C. Resume skill overlap
        if user_skills:
            job_text = " ".join([
                job.get("title", ""),
                job.get("description", ""),
                " ".join(job.get("skills", [])),
            ]).lower()
            overlap = sum(1 for skill in user_skills if skill.lower() in job_text)
            if overlap > 0:
                score += min(40.0, overlap * 5.0)

        ranked_jobs.append((score, job))

    # Sort by score descending
    ranked_jobs.sort(key=lambda x: x[0], reverse=True)

    # Format and return jobs
    source_display_map = {
        "naukri": "NAUKRI",
        "glassdoor": "GLASSDOOR",
        "remoteok": "REMOTEOK",
        "arbeitnow": "ARBEITNOW",
        "jsearch": "JSEARCH",
        "demo": "NAUKRI",  # demo jobs displayed as NAUKRI for UI consistency
    }
    results = []
    for score, job in ranked_jobs:
        src = job.get("source", "").lower()
        source_badge = source_display_map.get(src, job.get("source", "WEB"))
        results.append({
            "id": job.get("id", ""),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location") or "See listing",
            "source": source_badge,
            "salary": job.get("salary") or "Undisclosed",
            "posted_at": job.get("posted_at") or "Recently",
            "url": job.get("url", ""),
        })

    return {"jobs": results}


@app.get("/api/jobs/{run_id}/{job_id}/explain", tags=["Jobs"])
async def explain_job_match(run_id: str, job_id: str):
    """Get an AI explanation of why a specific job matches the candidate."""
    state = store.get_workflow(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")

    job = next((j for j in state.scored_jobs if j.id == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not state.user_profile:
        raise HTTPException(status_code=400, detail="No user profile in this run")

    coach = CareerCoachAgent()
    explanation = await coach.explain_job_match(state.user_profile, job)
    return {"job_id": job_id, "explanation": explanation}


# ─── Career Coach Chat ─────────────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse, tags=["Coach"])
async def career_chat(request: ChatRequest):
    """
    Career coaching chat endpoint.
    Optionally references a workflow run for full context.
    """
    user_profile = None
    career_profile = None
    market_report = None
    top_jobs = []

    if request.run_id:
        state = store.get_workflow(request.run_id)
        if state:
            user_profile = state.user_profile
            career_profile = state.career_profile
            market_report = state.market_report
            top_jobs = state.scored_jobs[:5]

    coach = CareerCoachAgent()
    reply, suggestions = await coach.chat(
        user_message=request.message,
        history=request.history,
        user=user_profile,
        career=career_profile,
        market=market_report,
        top_jobs=top_jobs,
    )
    return ChatResponse(reply=reply, suggestions=suggestions)


@app.post("/api/coach/roadmap", tags=["Coach"])
async def get_learning_roadmap(run_id: str):
    """Generate a personalized 90-day learning roadmap."""
    state = store.get_workflow(run_id)
    if not state or not state.user_profile or not state.career_profile or not state.market_report:
        raise HTTPException(status_code=400, detail="Workflow must be completed with a full profile first.")

    coach = CareerCoachAgent()
    roadmap = await coach.generate_roadmap(
        state.user_profile, state.career_profile, state.market_report
    )
    return {"run_id": run_id, "roadmap": roadmap}


# ─── Application ──────────────────────────────────────────────────────────────

@app.post("/api/apply/{run_id}/{job_id}", tags=["Application"])
async def apply_to_job(run_id: str, job_id: str, background_tasks: BackgroundTasks):
    """Trigger the direct application automation for a specific job."""
    state = store.get_workflow(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")

    job = next((j for j in state.scored_jobs if j.id == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    background_tasks.add_task(directApplyExecutor, job.url, run_id, state.user_profile.id if state.user_profile else "anonymous")
    
    return {
        "status": "launched",
        "message": f"Direct automation launched for job URL: {job.url}"
    }


# ─── Agents Status ────────────────────────────────────────────────────────────

def compile_agents_list(user_id: str | None) -> list[dict]:
    import db as database
    
    # 1. Fetch counts
    if user_id:
        db_counts = database.db_get_dashboard_counts(user_id)
        db_logs = database.db_get_agent_logs(user_id, limit=50)
    else:
        db_counts = {
            "resume": {"today": 0, "lifetime": 0},
            "discovery": {"today": 0, "lifetime": 0},
            "matching": {"today": 0, "lifetime": 0},
            "orchestrator": {"today": 0, "lifetime": 0},
            "autoapply": {"today": 0, "lifetime": 0},
            "tracking": {"today": 0, "lifetime": 0},
            "interview": {"today": 0, "lifetime": 0}
        }
        db_logs = []
    
    # 2. Compile agent statuses
    statuses = {s.agent_id: s for s in store.get_all_agent_statuses()}
    
    # Map log dates to time-ago or human strings
    def format_log_time(iso_str):
        try:
            dt = datetime.fromisoformat(iso_str)
            diff = datetime.utcnow() - dt
            if diff.total_seconds() < 60:
                return "Just now"
            elif diff.total_seconds() < 3600:
                mins = int(diff.total_seconds() // 60)
                return f"{mins} min" if mins == 1 else f"{mins} mins"
            else:
                hours = int(diff.total_seconds() // 3600)
                return f"{hours} hr" if hours == 1 else f"{hours} hrs"
        except Exception:
            return "Recently"
            
    # Build individual agent logs lists
    agent_logs = {
        "resume": [],
        "discovery": [],
        "matching": [],
        "autoapply": [],
        "orchestrator": [],
        "tracking": [],
        "interview": []
    }
    for log_entry in db_logs:
        agent_key = log_entry["agent"]
        if agent_key in agent_logs:
            agent_logs[agent_key].append({
                "time": format_log_time(log_entry["created_at"]),
                "text": log_entry["text"]
            })
            
    agents_list = [
        {
            "id": "resume",
            "agent_id": "resume",
            "name": "Resume Agent",
            "role": "Parses and enhances your resume",
            "description": "Extracts skills, experience and signals from your resume in seconds.",
            "status": "active" if (statuses.get("resume") and statuses["resume"].status == "active") else "idle",
            "progress": 100,
            "tasksToday": db_counts["resume"]["today"],
            "tasks_today": db_counts["resume"]["today"],
            "tasksTotal": db_counts["resume"]["lifetime"],
            "tasks_total": db_counts["resume"]["lifetime"],
            "recentActions": agent_logs["resume"][:3],
            "recent_actions": agent_logs["resume"][:3]
        },
        {
            "id": "discovery",
            "agent_id": "discovery",
            "name": "Discovery Agent",
            "role": "Searches the web for jobs",
            "description": "Crawls 40+ sources continuously to surface roles before they're saturated.",
            "status": "active" if (statuses.get("discovery") and statuses["discovery"].status == "active") else "idle",
            "progress": 64 if (statuses.get("discovery") and statuses["discovery"].status == "active") else 100,
            "tasksToday": db_counts["discovery"]["today"],
            "tasks_today": db_counts["discovery"]["today"],
            "tasksTotal": db_counts["discovery"]["lifetime"],
            "tasks_total": db_counts["discovery"]["lifetime"],
            "recentActions": agent_logs["discovery"][:3],
            "recent_actions": agent_logs["discovery"][:3]
        },
        {
            "id": "matching",
            "agent_id": "matching",
            "name": "Matching Agent",
            "role": "Scores fit for every role",
            "description": "Compares each role against your resume and preferences using multi-factor scoring.",
            "status": "thinking" if (statuses.get("matching") and statuses["matching"].status in ("active", "thinking")) else "idle",
            "progress": 41 if (statuses.get("matching") and statuses["matching"].status in ("active", "thinking")) else 100,
            "tasksToday": db_counts["matching"]["today"],
            "tasks_today": db_counts["matching"]["today"],
            "tasksTotal": db_counts["matching"]["lifetime"],
            "tasks_total": db_counts["matching"]["lifetime"],
            "recentActions": agent_logs["matching"][:3],
            "recent_actions": agent_logs["matching"][:3]
        },
        {
            "id": "apply",
            "agent_id": "apply",
            "name": "AutoApply Agent",
            "role": "Autonomous job applications",
            "description": "Navigates directly to job listings, fills forms with your profile data, uploads your resume, and submits applications autonomously — or escalates to you when human verification is needed.",
            "status": "active" if (statuses.get("autoapply") and statuses["autoapply"].status == "active") else "idle",
            "progress": 22 if (statuses.get("autoapply") and statuses["autoapply"].status == "active") else 100,
            "tasksToday": db_counts["autoapply"]["today"],
            "tasks_today": db_counts["autoapply"]["today"],
            "tasksTotal": db_counts["autoapply"]["lifetime"],
            "tasks_total": db_counts["autoapply"]["lifetime"],
            "recentActions": agent_logs["autoapply"][:3],
            "recent_actions": agent_logs["autoapply"][:3]
        },
        {
            "id": "orchestrator",
            "agent_id": "orchestrator",
            "name": "Agent Orchestrator",
            "role": "Multi-agent coordination engine",
            "description": "Master coordinator that manages the pipeline between Discovery and AutoApply. Polls the database for high-match jobs and dispatches autonomous applications.",
            "status": "active" if (statuses.get("orchestrator") and statuses["orchestrator"].status == "active") else "idle",
            "progress": 100,
            "tasksToday": db_counts["orchestrator"]["today"],
            "tasks_today": db_counts["orchestrator"]["today"],
            "tasksTotal": db_counts["orchestrator"]["lifetime"],
            "tasks_total": db_counts["orchestrator"]["lifetime"],
            "recentActions": agent_logs["orchestrator"][:3],
            "recent_actions": agent_logs["orchestrator"][:3]
        },
        {
            "id": "tracking",
            "agent_id": "tracking",
            "name": "Tracking Agent",
            "role": "Follows up on every application",
            "description": "Monitors inbox and platforms to keep your pipeline up to date.",
            "status": "active" if (statuses.get("tracking") and statuses["tracking"].status == "active") else "idle",
            "progress": 100,
            "tasksToday": db_counts["tracking"]["today"],
            "tasks_today": db_counts["tracking"]["today"],
            "tasksTotal": db_counts["tracking"]["lifetime"],
            "tasks_total": db_counts["tracking"]["lifetime"],
            "recentActions": agent_logs["tracking"][:3],
            "recent_actions": agent_logs["tracking"][:3]
        },
        {
            "id": "interview",
            "agent_id": "interview",
            "name": "Interview Agent",
            "role": "Coaches you for every round",
            "description": "Generates likely questions, runs mock interviews and gives feedback.",
            "status": "active" if (statuses.get("interview") and statuses["interview"].status == "active") else "paused",
            "progress": 0 if not (statuses.get("interview") and statuses["interview"].status == "active") else 50,
            "tasksToday": db_counts["interview"]["today"],
            "tasks_today": db_counts["interview"]["today"],
            "tasksTotal": db_counts["interview"]["lifetime"],
            "tasks_total": db_counts["interview"]["lifetime"],
            "recentActions": agent_logs["interview"][:3],
            "recent_actions": agent_logs["interview"][:3]
        }
    ]
    return agents_list


@app.get("/api/agents/status", tags=["Agents"])
async def get_agents_status(current_user: dict[str, Any] | None = Depends(get_current_user_optional)):
    """Get current status of all 7 AI agents."""
    user_id = current_user["id"] if current_user else None
    agents_list = compile_agents_list(user_id)
    return {
        "agents": agents_list,
        "total": len(agents_list),
        "active": sum(1 for s in agents_list if s["status"] in ("active", "thinking")),
    }


@app.get("/api/agents/dashboard", tags=["Agents"])
async def get_agents_dashboard(current_user: dict[str, Any] = Depends(get_current_user)):
    """Get real-time agent statuses, counts, and recent logs for the dashboard."""
    agents_list = compile_agents_list(current_user["id"])
    return {"agents": agents_list}



@app.get("/api/workflows", tags=["Workflow"])
async def list_workflows(current_user: dict[str, Any] | None = Depends(get_current_user_optional)):
    """List all workflow runs."""
    all_states = store.all_workflows()
    if current_user:
        all_states = [s for s in all_states if s.user_id == current_user["id"]]
    return {
        "total": len(all_states),
        "workflows": [
            {
                "run_id": s.run_id,
                "status": s.status,
                "steps_completed": s.steps_completed,
                "jobs_found": len(s.scored_jobs),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in all_states
        ],
    }


# ─── WebSocket — Real-Time Event Stream ───────────────────────────────────────

@app.websocket("/ws/{run_id}")
async def websocket_run(websocket: WebSocket, run_id: str):
    """
    WebSocket endpoint for real-time workflow events.
    Client connects here to receive live updates during an agentic workflow.
    """
    await websocket.accept()
    log.info(f"WebSocket connected for run: {run_id}")

    q = store.subscribe(run_id)

    # Send current state immediately if available
    state = store.get_workflow(run_id)
    if state:
        await websocket.send_json({
            "event_type": "state_snapshot",
            "status": state.status,
            "steps_completed": state.steps_completed,
            "jobs_count": len(state.scored_jobs),
        })

    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30)
                await websocket.send_json(event)

                # Close if workflow is done
                if event.get("event_type") in ("completed", "error"):
                    await asyncio.sleep(1)
                    break
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"event_type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})

    except WebSocketDisconnect:
        log.info(f"WebSocket disconnected for run: {run_id}")
    except Exception as e:
        log.error(f"WebSocket error for run {run_id}: {e}")
    finally:
        store.unsubscribe(run_id, q)


# ─── Auth & Session Management ────────────────────────────────────────────────

@app.post("/api/auth/register", tags=["Auth"])
async def api_register(req: RegisterRequest):
    try:
        token, user = register_user(req.name, req.email, req.password)
        return {"token": token, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login", tags=["Auth"])
async def api_login(req: LoginRequest):
    try:
        token, user = login_user(req.email, req.password)
        return {"token": token, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/google", tags=["Auth"])
async def api_google_auth(req: GoogleLoginRequest):
    try:
        token, user = google_auth_user(req.token, req.name, req.email)
        return {"token": token, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.get("/api/auth/me", tags=["Auth"])
async def api_me(current_user: dict[str, Any] = Depends(get_current_user)):
    return current_user


@app.post("/api/auth/logout", tags=["Auth"])
async def api_logout(current_user: dict[str, Any] = Depends(get_current_user)):
    return {"message": "Logged out successfully"}


# ─── Applications Management ──────────────────────────────────────────────────

class CreateApplicationRequest(BaseModel):
    job_id: str
    title: str
    company: str
    company_logo: Optional[str] = None
    stage: str
    location: Optional[str] = None
    salary: Optional[str] = None
    url: Optional[str] = None


@app.get("/api/applications", tags=["Applications"])
async def list_applications(current_user: dict[str, Any] = Depends(get_current_user)):
    import db
    apps = db.db_get_applications_by_user(current_user["id"])
    return {"applications": apps}


@app.post("/api/applications", tags=["Applications"])
async def create_or_update_application(
    req: CreateApplicationRequest,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    import db
    # Check if application already exists for this user and job_id
    existing_apps = db.db_get_applications_by_user(current_user["id"])
    app_id = None
    for app in existing_apps:
        if app["job_id"] == req.job_id:
            app_id = app["id"]
            break
            
    if not app_id:
        app_id = str(uuid.uuid4())
        
    app_data = {
        "id": app_id,
        "user_id": current_user["id"],
        "job_id": req.job_id,
        "title": req.title,
        "company": req.company,
        "company_logo": req.company_logo or req.company[0].upper() if req.company else "?",
        "stage": req.stage,
        "location": req.location or "",
        "salary": req.salary or "",
        "url": req.url or "",
        "updated_at": datetime.utcnow().isoformat()
    }
    db.db_save_application(app_data)
    return {"status": "success", "application": app_data}


@app.delete("/api/applications/{app_id}", tags=["Applications"])
async def delete_application(
    app_id: str,
    current_user: dict[str, Any] = Depends(get_current_user)
):
    import db
    app = db.db_get_application(app_id)
    if not app or app["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Application not found")
    db.db_delete_application(app_id)
    return {"status": "success", "message": "Application deleted"}


# ─── AutoApply Queue Management ───────────────────────────────────────────────

@app.get("/api/autoapply/stats", tags=["AutoApply"])
async def get_autoapply_stats(current_user: dict[str, Any] = Depends(get_current_user)):
    """Get aggregate statistics of the auto-apply pipeline for the current user."""
    from agents.orchestrator import db_get_queue_stats
    stats = db_get_queue_stats(user_id=current_user["id"])
    return {
        "stats": stats,
        "total": sum(stats.values()),
        "applied": stats.get("applied", 0),
        "pending": stats.get("discovered", 0) + stats.get("queued", 0),
        "manual": stats.get("requires_manual_intervention", 0),
        "failed": stats.get("failed", 0),
    }


@app.get("/api/autoapply/queue", tags=["AutoApply"])
async def get_autoapply_queue(
    current_user: dict[str, Any] = Depends(get_current_user),
    limit: int = 50,
):
    """Get the auto-apply queue entries for the current user."""
    from agents.orchestrator import db_get_queue_entries
    entries = db_get_queue_entries(user_id=current_user["id"], limit=limit)
    return {"entries": entries, "total": len(entries)}


class ManualEnqueueRequest(BaseModel):
    run_id: str
    job_id: str
    job_title: str
    job_company: str
    job_url: str
    job_source: str = ""


@app.post("/api/autoapply/enqueue", tags=["AutoApply"])
async def manual_enqueue_job(
    req: ManualEnqueueRequest,
    background_tasks: BackgroundTasks,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Manually trigger direct auto-application for a specific job."""
    print(f"[AUTO-APPLY TRIGGER] Received manual direct apply request for job '{req.job_title}' at {req.job_company}")
    
    background_tasks.add_task(directApplyExecutor, req.job_url, req.run_id, current_user["id"])
    
    return {
        "status": "launched",
        "message": f"Direct browser automation launched for {req.job_title} at {req.job_company}."
    }


# ─── Dev entry ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )