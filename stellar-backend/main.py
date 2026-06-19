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
from auth import RegisterRequest, LoginRequest, register_user, login_user, get_user_by_token

log = get_logger("API")
settings = get_settings()


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
    ]:
        store.update_agent_status(AgentStatus(
            agent_id=agent_def[0],
            name=agent_def[1],
            status=agent_def[2],
        ))

    yield
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
        settings.frontend_url
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
        "version": "2.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "agents": 7,
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
        except Exception as e:
            log.error(f"Failed to persist candidate profile: {e}", exc_info=True)

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
        user_profile = UserProfile(
            name="Job Seeker",
            summary=f"Looking for {request.role} roles",
            skills=[request.role] if request.role else [],
        )

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
async def search_jobs(request: JobSearchRequest, background_tasks: BackgroundTasks):
    """
    Quick job search without requiring a resume.
    Kicks off a lightweight discovery + scoring workflow.
    """
    run_id = str(uuid.uuid4())
    background_tasks.add_task(
        run_job_search_workflow,
        run_id, request.role, request.location,
        request.remote_preference, request.limit,
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
    all_jobs_raw, provider_used = await search_jobs_resilient(
        role=role,
        location=location,
        salary_target=salary_target,
        firecrawl_key=settings.firecrawl_api_key,
        rapidapi_key="",
    )
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
    """Trigger the Application Agent to auto-apply to a specific job."""
    state = store.get_workflow(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")

    job = next((j for j in state.scored_jobs if j.id == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not state.user_profile:
        raise HTTPException(status_code=400, detail="No user profile found")

    # Find resume path
    resume_path = ""
    resume_files = [f for f in os.listdir(settings.upload_dir) if run_id in f]
    if resume_files:
        resume_path = os.path.join(settings.upload_dir, resume_files[0])

    agent = ApplicationAgent()
    result = await agent.apply_to_job(
        job=job,
        user=state.user_profile,
        run_id=run_id,
        resume_path=resume_path,
    )

    if result.get("status") == "action_required":
        return JSONResponse(status_code=202, content={
            "status": "ACTION_REQUIRED",
            "reason": result.get("reason", "Human verification required"),
            "url": result.get("url", job.url),
            "screenshot": result.get("screenshot", ""),
            "run_id": run_id,
            "job_id": job_id,
        })

    return result


# ─── Agents Status ────────────────────────────────────────────────────────────

@app.get("/api/agents/status", tags=["Agents"])
async def get_agents_status():
    """Get current status of all 7 AI agents."""
    statuses = store.get_all_agent_statuses()
    return {
        "agents": [s.model_dump(mode="json") for s in statuses],
        "total": len(statuses),
        "active": sum(1 for s in statuses if s.status == "active"),
    }


@app.get("/api/workflows", tags=["Workflow"])
async def list_workflows():
    """List all workflow runs."""
    all_states = store.all_workflows()
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