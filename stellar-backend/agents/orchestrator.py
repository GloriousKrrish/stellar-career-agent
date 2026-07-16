"""
Agent Orchestrator — Multi-Agent Coordination Engine
====================================================
Master coordinator that manages the pipeline between Aria (discovery)
and the AutoApply agent. Implements a database-driven state machine
that continuously polls for discovered jobs and queues them for
autonomous application.

Pipeline States:
  discovered → queued → applying → applied | requires_manual_intervention | failed

Architecture:
  - Runs as a persistent background asyncio task alongside the FastAPI server
  - Polls the `auto_apply_queue` table for jobs with status 'discovered'
  - Batches and rate-limits applications to avoid triggering anti-bot systems
  - Streams real-time events to the frontend via WebSocket pub/sub
  - Supports configurable concurrency and cooldown intervals

Author: Stellar Career Agent Platform
"""
from __future__ import annotations
import asyncio
import os
import sys
import threading
import uuid
from datetime import datetime
from typing import Any, Optional

from logger import get_logger
from models import UserProfile
import store
import db as database

log = get_logger("AgentOrchestrator")

# ── Configuration ─────────────────────────────────────────────────────────────

# How often to poll the database for new discovered jobs (seconds)
POLL_INTERVAL_SECONDS = int(os.getenv("AUTOAPPLY_POLL_INTERVAL", "15"))

# Maximum concurrent application tasks
MAX_CONCURRENT_APPLIES = int(os.getenv("AUTOAPPLY_MAX_CONCURRENT", "2"))

# Cooldown between individual applications (seconds) — prevents rate-limiting
APPLY_COOLDOWN_SECONDS = int(os.getenv("AUTOAPPLY_COOLDOWN", "30"))

# Maximum applications per polling cycle
MAX_PER_CYCLE = int(os.getenv("AUTOAPPLY_MAX_PER_CYCLE", "5"))

# Master kill switch (can be toggled via env var or API)
AUTOAPPLY_ENABLED = os.getenv("AUTOAPPLY_ENABLED", "true").lower() in ("true", "1", "yes")


# ── Database Operations for Auto-Apply Queue ─────────────────────────────────

def db_init_auto_apply_table() -> None:
    """Create the auto_apply_queue table if it doesn't exist."""
    conn = database.get_db_connection()
    cursor = database.get_db_cursor(conn)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auto_apply_queue (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        job_title TEXT NOT NULL,
        job_company TEXT NOT NULL,
        job_url TEXT NOT NULL,
        job_source TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'discovered',
        ats_platform TEXT DEFAULT '',
        failure_reason TEXT DEFAULT '',
        screenshot_path TEXT DEFAULT '',
        fields_filled INTEGER DEFAULT 0,
        attempts INTEGER DEFAULT 0,
        max_attempts INTEGER DEFAULT 3,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        applied_at TEXT DEFAULT '',
        debug_mode BOOLEAN DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    try:
        if database.IS_POSTGRES:
            cursor.execute("ALTER TABLE auto_apply_queue ADD COLUMN IF NOT EXISTS debug_mode BOOLEAN DEFAULT FALSE")
        else:
            cursor.execute("ALTER TABLE auto_apply_queue ADD COLUMN debug_mode BOOLEAN DEFAULT 0")
    except Exception:
        pass

    conn.commit()
    conn.close()
    log.info("auto_apply_queue table initialized")


def db_enqueue_job(
    user_id: str,
    run_id: str,
    job_id: str,
    job_title: str,
    job_company: str,
    job_url: str,
    job_source: str = "",
    initial_status: str = "discovered",
    debug_mode: bool = False,
) -> str:
    """Insert a discovered job into the auto-apply queue.
    
    Args:
        initial_status: 'discovered' (for orchestrator loop pickup) or
                        'queued' (for manually-dispatched jobs, to prevent
                        double-execution by the background orchestrator loop).
    """
    queue_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = database.get_db_connection()
    cursor = database.get_db_cursor(conn)

    if database.IS_POSTGRES:
        cursor.execute("""
        INSERT INTO auto_apply_queue (
            id, user_id, run_id, job_id, job_title, job_company, job_url, job_source,
            status, created_at, updated_at, debug_mode
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """, (queue_id, user_id, run_id, job_id, job_title, job_company, job_url,
              job_source, initial_status, now, now, debug_mode))
    else:
        cursor.execute("""
        INSERT OR IGNORE INTO auto_apply_queue (
            id, user_id, run_id, job_id, job_title, job_company, job_url, job_source,
            status, created_at, updated_at, debug_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (queue_id, user_id, run_id, job_id, job_title, job_company, job_url,
              job_source, initial_status, now, now, 1 if debug_mode else 0))

    conn.commit()
    conn.close()

    try:
        import db as database_module
        existing = database_module.db_get_application_by_job(user_id, job_id)
        app_id = existing["id"] if existing else str(uuid.uuid4())
        database_module.db_save_application({
            "id": app_id,
            "user_id": user_id,
            "job_id": job_id,
            "title": job_title,
            "company": job_company,
            "company_logo": job_company[0].upper() if job_company else "?",
            "stage": "matching",
            "location": existing.get("location", "") if existing else "",
            "salary": existing.get("salary", "") if existing else "",
            "url": job_url,
            "updated_at": datetime.utcnow().isoformat(),
        })
    except Exception as app_err:
        log.error(f"Failed to create/update matching application on enqueue: {app_err}")

    log.info(f"Enqueued job for auto-apply: {job_title} @ {job_company} (queue_id={queue_id[:8]}, status={initial_status}, debug_mode={debug_mode})")
    return queue_id


def db_get_discovered_jobs(limit: int = MAX_PER_CYCLE) -> list[dict]:
    """Fetch jobs with status='discovered' that are ready for application."""
    conn = database.get_db_connection()
    cursor = database.get_db_cursor(conn)

    if database.IS_POSTGRES:
        cursor.execute("""
        SELECT * FROM auto_apply_queue
        WHERE status = 'discovered' AND attempts < max_attempts
        ORDER BY created_at ASC
        LIMIT %s
        """, (limit,))
    else:
        cursor.execute("""
        SELECT * FROM auto_apply_queue
        WHERE status = 'discovered' AND attempts < max_attempts
        ORDER BY created_at ASC
        LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def db_update_queue_status(
    queue_id: str,
    status: str,
    failure_reason: str = "",
    screenshot_path: str = "",
    fields_filled: int = 0,
    ats_platform: str = "",
) -> None:
    """Update the status of a queue entry after an application attempt."""
    now = datetime.utcnow().isoformat()
    conn = database.get_db_connection()
    cursor = database.get_db_cursor(conn)

    applied_at = now if status == "applied" else None

    if database.IS_POSTGRES:
        cursor.execute("""
        UPDATE auto_apply_queue SET
            status = %s,
            failure_reason = %s,
            screenshot_path = %s,
            fields_filled = %s,
            ats_platform = %s,
            attempts = attempts + 1,
            updated_at = %s,
            applied_at = %s
        WHERE id = %s
        """, (status, failure_reason, screenshot_path, fields_filled,
              ats_platform, now, applied_at, queue_id))
    else:
        cursor.execute("""
        UPDATE auto_apply_queue SET
            status = ?,
            failure_reason = ?,
            screenshot_path = ?,
            fields_filled = ?,
            ats_platform = ?,
            attempts = attempts + 1,
            updated_at = ?,
            applied_at = ?
        WHERE id = ?
        """, (status, failure_reason, screenshot_path, fields_filled,
              ats_platform, now, applied_at, queue_id))

    conn.commit()
    conn.close()


def db_mark_as_queued(queue_id: str) -> None:
    """Transition a job from 'discovered' → 'queued' (claimed by orchestrator)."""
    now = datetime.utcnow().isoformat()
    conn = database.get_db_connection()
    cursor = database.get_db_cursor(conn)

    if database.IS_POSTGRES:
        cursor.execute(
            "UPDATE auto_apply_queue SET status = 'queued', updated_at = %s WHERE id = %s",
            (now, queue_id)
        )
    else:
        cursor.execute(
            "UPDATE auto_apply_queue SET status = 'queued', updated_at = ? WHERE id = ?",
            (now, queue_id)
        )

    conn.commit()
    conn.close()


def db_get_queue_stats(user_id: Optional[str] = None) -> dict[str, int]:
    """Get aggregate counts of queue entries by status."""
    conn = database.get_db_connection()
    cursor = database.get_db_cursor(conn)

    if user_id:
        if database.IS_POSTGRES:
            cursor.execute(
                "SELECT status, COUNT(*) as cnt FROM auto_apply_queue WHERE user_id = %s GROUP BY status",
                (user_id,)
            )
        else:
            cursor.execute(
                "SELECT status, COUNT(*) as cnt FROM auto_apply_queue WHERE user_id = ? GROUP BY status",
                (user_id,)
            )
    else:
        cursor.execute("SELECT status, COUNT(*) as cnt FROM auto_apply_queue GROUP BY status")

    rows = cursor.fetchall()
    conn.close()
    return {dict(r)["status"]: dict(r)["cnt"] for r in rows}


def db_get_queue_entries(user_id: str, limit: int = 50) -> list[dict]:
    """Get all queue entries for a user, sorted by most recent first."""
    conn = database.get_db_connection()
    cursor = database.get_db_cursor(conn)

    if database.IS_POSTGRES:
        cursor.execute(
            "SELECT * FROM auto_apply_queue WHERE user_id = %s ORDER BY updated_at DESC LIMIT %s",
            (user_id, limit)
        )
    else:
        cursor.execute(
            "SELECT * FROM auto_apply_queue WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit)
        )

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Event Emitter ─────────────────────────────────────────────────────────────

async def _emit_autoapply_event(
    run_id: str,
    event_type: str,
    message: str,
    data: dict | None = None,
    user_id: str | None = None,
) -> None:
    """Broadcast an auto-apply event to the WebSocket live feed and save to agent_logs."""
    from models import LiveEvent
    import db as database
    
    event = LiveEvent(
        run_id=run_id,
        event_type=event_type,
        agent="AutoApplyAgent",
        message=message,
        data=data or {},
    )
    await store.publish(run_id, event.model_dump(mode="json"))
    log.info(f"[AutoApplyAgent] [{run_id[:8]}] {message}")

    # Persist log to agent_logs table
    if user_id:
        try:
            database.db_save_agent_log(
                user_id=user_id,
                agent="autoapply",
                text=message,
                kind="success" if ("success" in message.lower() or "✅" in message) else "error" if ("fail" in message.lower() or "❌" in message) else "info"
            )
            # Also log for Agent Orchestrator to populate both cards with real activities
            database.db_save_agent_log(
                user_id=user_id,
                agent="orchestrator",
                text=message,
                kind="success" if ("success" in message.lower() or "✅" in message) else "error" if ("fail" in message.lower() or "❌" in message) else "info"
            )
        except Exception as e:
            log.error(f"Failed to save agent log: {e}")


def run_autoapply_job_in_thread(entry: dict) -> None:
    """
    Fire-and-forget: Runs the async process_single_autoapply_job in a new daemon thread
    with its own event loop and WindowsProactorEventLoopPolicy.
    Used for immediate API triggers.
    """
    def worker():
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass
        thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_loop)
        try:
            thread_loop.run_until_complete(process_single_autoapply_job(entry))
        finally:
            thread_loop.close()

    t = threading.Thread(target=worker, daemon=True)
    t.start()


async def run_coro_in_thread(coro_func, *args) -> Any:
    """
    Awaited: Runs an async coroutine function in a background thread with its own
    ProactorEventLoop, returning the result asynchronously to the main event loop.
    Used in the orchestrator loop to preserve concurrency and cooldown pacing.
    """
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def worker():
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass
        thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_loop)
        try:
            res = thread_loop.run_until_complete(coro_func(*args))
            loop.call_soon_threadsafe(future.set_result, res)
        except Exception as e:
            loop.call_soon_threadsafe(future.set_exception, e)
        finally:
            thread_loop.close()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return await future


async def process_single_autoapply_job(entry: dict) -> None:
    """
    Execute the full auto-apply browser automation process for a single queued entry.
    
    CRITICAL: This entire function is wrapped in a bulletproof try/except/finally
    so that ANY crash — Playwright segfault, missing dep, asyncio cancellation —
    is caught, logged with full stack trace to BOTH the terminal AND the WebSocket
    feed, and the agent status is ALWAYS reset to idle on exit.
    """
    import traceback
    from agents.auto_apply_agent import AutoApplyAgent
    from models import AgentStatus
    from config import get_settings
    import db as database

    queue_id = entry["id"]
    run_id = entry["run_id"]
    user_id = entry["user_id"]

    try:
        agent = AutoApplyAgent()

        # Claim the job
        db_mark_as_queued(queue_id)

        # ── URL Validation Gate ───────────────────────────────────────────────
        job_url = (entry.get("job_url") or "").strip()
        if not job_url:
            fail_reason = "job_url is empty or missing in queue entry"
            log.error(f"[{queue_id[:8]}] URL VALIDATION FAILED: {fail_reason}")
            db_update_queue_status(queue_id, "failed", failure_reason=fail_reason)
            await _emit_autoapply_event(
                run_id, "log",
                f"[AutoApplyAgent]: ❌ {entry['job_title']} @ {entry['job_company']}: {fail_reason}",
                user_id=user_id
            )
            return

        if not job_url.startswith(("http://", "https://")):
            fail_reason = f"job_url is not a valid absolute URL: '{job_url[:100]}'"
            log.error(f"[{queue_id[:8]}] URL VALIDATION FAILED: {fail_reason}")
            db_update_queue_status(queue_id, "failed", failure_reason=fail_reason)
            await _emit_autoapply_event(
                run_id, "log",
                f"[AutoApplyAgent]: ❌ {entry['job_title']} @ {entry['job_company']}: {fail_reason}",
                user_id=user_id
            )
            return

        log.info(f"[{queue_id[:8]}] URL validated: {job_url}")

        # ── Resolve user profile ──────────────────────────────────────────────
        user_data = database.get_user_by_id(user_id)
        if not user_data:
            db_update_queue_status(queue_id, "failed", failure_reason="User profile not found")
            await _emit_autoapply_event(run_id, "log", f"[AutoApplyAgent]: ⚠️ Skipped {entry['job_title']}: user profile missing", user_id=user_id)
            return

        user_profile = UserProfile(
            id=user_data["id"],
            name=user_data.get("name", ""),
            email=user_data.get("email", ""),
            phone=user_data.get("phone", ""),
            location=user_data.get("location", ""),
            skills=user_data.get("skills", []) if isinstance(user_data.get("skills"), list) else [],
            linkedin=user_data.get("linkedin", ""),
            github=user_data.get("github", ""),
            summary=user_data.get("summary", ""),
            work_history=user_data.get("work_history", []) if isinstance(user_data.get("work_history"), list) else [],
        )

        # ── Find resume file (Phase 6 - Multiple Resumes Selection) ───────────
        user_resumes = database.db_get_resumes_by_user(user_id)
        selected_resume = None
        
        # If user has uploaded multiple resumes, use Gemini to recommend the best one
        if len(user_resumes) > 1:
            try:
                import google.generativeai as genai
                settings = get_settings()
                if settings.gemini_api_key:
                    genai.configure(api_key=settings.gemini_api_key)
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    
                    resume_list_str = "\n".join([
                        f"- ID: {r['id']}, Filename: {r['filename']}, Skills: {', '.join(r['skills'])}"
                        for r in user_resumes
                    ])
                    
                    prompt = f"""
You are an AI career assistant matching the best resume to a target job application.
Candidate Resumes:
{resume_list_str}

Target Job:
- Title: {entry['job_title']}
- Company: {entry['job_company']}
- URL: {job_url}

Select the ID of the resume that is the most relevant and best fit for this job based on skills and keywords.
Return ONLY the resume ID as plain text, with no extra characters or symbols.
"""
                    response = await model.generate_content_async(prompt)
                    selected_id = response.text.strip()
                    for r in user_resumes:
                        if r["id"] in selected_id or selected_id in r["id"]:
                            selected_resume = r
                            break
            except Exception as e:
                log.warning(f"Failed to auto-select best resume via AI: {e}")
                
        if not selected_resume:
            for r in user_resumes:
                if r["is_default"]:
                    selected_resume = r
                    break
            if not selected_resume and user_resumes:
                selected_resume = user_resumes[0]
                
        resume_path = ""
        resume_raw_text = ""
        if selected_resume:
            resume_path = selected_resume["filepath"]
            resume_raw_text = selected_resume.get("raw_text", "")
            log.info(f"[{queue_id[:8]}] Selected best-fit resume: {selected_resume['filename']} (ID: {selected_resume['id']})")
            await _emit_autoapply_event(
                run_id, "log",
                f"[AutoApplyAgent]: 📄 Selected best-fit resume: {selected_resume['filename']}",
                user_id=user_id
            )
        else:
            settings = get_settings()
            run_id_for_resume = user_data.get("run_id", "")
            if run_id_for_resume:
                upload_dir = settings.upload_dir
                for f in os.listdir(upload_dir) if os.path.isdir(upload_dir) else []:
                    if run_id_for_resume in f:
                        resume_path = os.path.join(upload_dir, f)
                        break
            if user_profile and user_profile.summary:
                resume_raw_text = user_profile.summary

        # Retrieve job description from workflow run
        job_description = ""
        try:
            workflow_state = store.get_workflow(run_id)
            if workflow_state and workflow_state.scored_jobs:
                for j in workflow_state.scored_jobs:
                    if j.id == entry["job_id"]:
                        job_description = j.description
                        break
        except Exception as e:
            log.warning(f"Failed to retrieve job description: {e}")

        # ── Evaluate Job Match (Phase 4 - AI Job Matching) ────────────────────
        threshold = 70
        await _emit_autoapply_event(
            run_id, "log",
            f"[AutoApplyAgent]: 🔍 Evaluating job match fit for {entry['job_title']}...",
            user_id=user_id
        )
        
        evaluation = await agent.evaluate_job_match(
            user=user_profile,
            job_title=entry['job_title'],
            job_company=entry['job_company'],
            job_url=job_url,
            resume_text=resume_raw_text or user_profile.summary,
            threshold=threshold
        )
        
        match_score = evaluation.get("match_score", 0)
        recommendation = evaluation.get("recommendation", "skip")
        explanation = evaluation.get("explanation", "")
        
        log.info(f"[{queue_id[:8]}] Job Match Evaluation: Score={match_score}, Rec={recommendation}")
        await _emit_autoapply_event(
            run_id, "log",
            f"[AutoApplyAgent]: 📊 Fit analysis complete. Match Score: {match_score}% | Recommendation: {recommendation.upper()}",
            user_id=user_id
        )
        
        if recommendation == "skip" and match_score < threshold:
            database.db_update_queue_status(queue_id, "skipped", failure_reason=f"Skipped: match score {match_score}% is below threshold {threshold}%. Explanation: {explanation}")
            await _emit_autoapply_event(
                run_id, "log",
                f"[AutoApplyAgent]: ⚠️ Skipping application (Fit score {match_score}% < {threshold}%). Explanation: {explanation}",
                user_id=user_id
            )
            try:
                existing = database.db_get_application_by_job(user_id, entry["job_id"])
                app_id = existing["id"] if existing else str(uuid.uuid4())
                database.db_save_application({
                    "id": app_id,
                    "user_id": user_id,
                    "job_id": entry["job_id"],
                    "title": entry["job_title"],
                    "company": entry["job_company"],
                    "company_logo": entry["job_company"][0].upper() if entry["job_company"] else "?",
                    "stage": "skipped",
                    "location": existing.get("location", "") if existing else "",
                    "salary": existing.get("salary", "") if existing else "",
                    "url": job_url,
                    "updated_at": datetime.utcnow().isoformat(),
                })
                await _emit_autoapply_event(
                    run_id, "application_completed",
                    f"[AutoApplyAgent]: Job application skipped (Score: {match_score}%)",
                    {
                        "status": "skipped",
                        "job_id": entry["job_id"],
                        "queue_id": queue_id,
                        "job_title": entry["job_title"],
                        "job_company": entry["job_company"],
                        "stage": "skipped",
                        "explanation": explanation,
                        "match_score": match_score
                    },
                    user_id=user_id
                )
            except Exception as e:
                log.error(f"Failed to update app to skipped stage: {e}")
            return

        # ── Emit "starting" progress ──────────────────────────────────────────
        await _emit_autoapply_event(
            run_id, "progress",
            f"[AutoApplyAgent]: 🤖 AutoApply starting: {entry['job_title']} @ {entry['job_company']}",
            {"job_id": entry["job_id"], "queue_id": queue_id},
            user_id=user_id
        )

        # ── Update application stage to 'applying' ───────────────────────────
        try:
            existing = database.db_get_application_by_job(user_id, entry["job_id"])
            app_id = existing["id"] if existing else str(uuid.uuid4())
            database.db_save_application({
                "id": app_id,
                "user_id": user_id,
                "job_id": entry["job_id"],
                "title": entry["job_title"],
                "company": entry["job_company"],
                "company_logo": entry["job_company"][0].upper() if entry["job_company"] else "?",
                "stage": "applying",
                "location": existing.get("location", "") if existing else "",
                "salary": existing.get("salary", "") if existing else "",
                "url": job_url,
                "updated_at": datetime.utcnow().isoformat(),
            })
            await _emit_autoapply_event(
                run_id, "application_updated",
                f"[AutoApplyAgent]: Job {entry['job_title']} @ {entry['job_company']} status updated to 'applying'",
                {
                    "status": "applying",
                    "job_id": entry["job_id"],
                    "queue_id": queue_id,
                    "job_title": entry["job_title"],
                    "job_company": entry["job_company"],
                    "stage": "applying"
                },
                user_id=user_id
            )
        except Exception as app_err:
            log.error(f"Failed to update application to applying stage: {app_err}")

        # ── Update agent status board ─────────────────────────────────────────
        store.update_agent_status(AgentStatus(
            agent_id="autoapply",
            name="AutoApply Agent",
            status="active",
            current_task=f"Applying to {entry['job_title']} @ {entry['job_company']}",
        ))

        # ── Execute the application ───────────────────────────────────────────
        async def on_progress(msg: str):
            await _emit_autoapply_event(run_id, "log", msg, user_id=user_id)

        result = await agent.apply_to_job(
            task_id=queue_id,
            job_url=job_url,
            job_title=entry["job_title"],
            job_company=entry["job_company"],
            user=user_profile,
            resume_path=resume_path,
            on_progress=on_progress,
            job_description=job_description,
            resume_text=resume_raw_text,
            debug_mode=bool(entry.get("debug_mode", False)),
        )

        # ── Update database with result ───────────────────────────────────────
        status = result.get("status", "failed")
        reason = result.get("reason", "")
        db_update_queue_status(
            queue_id=queue_id,
            status=status,
            failure_reason=reason,
            screenshot_path=result.get("screenshot", ""),
            fields_filled=result.get("fields_filled", 0),
            ats_platform=result.get("ats_platform", ""),
        )

        # ── Update the applications table if successfully applied or simulated ─
        if status in ("applied", "simulated"):
            try:
                existing = database.db_get_application_by_job(user_id, entry["job_id"])
                app_id = existing["id"] if existing else str(uuid.uuid4())

                database.db_save_application({
                    "id": app_id,
                    "user_id": user_id,
                    "job_id": entry["job_id"],
                    "title": entry["job_title"],
                    "company": entry["job_company"],
                    "company_logo": entry["job_company"][0].upper() if entry["job_company"] else "?",
                    "stage": "applied",
                    "location": existing.get("location", "") if existing else "",
                    "salary": existing.get("salary", "") if existing else "",
                    "url": job_url,
                    "updated_at": datetime.utcnow().isoformat(),
                })
                log.info(f"Transitioned job application {app_id[:8]} to 'applied' stage.")
            except Exception as e:
                log.error(f"Failed to save applied application: {e}")

        # ── Emit result event with DETAILED reason in message ─────────────────
        # Always use "application_completed" as the terminal event type so the
        # frontend WebSocket handler can reliably detect all outcomes.
        event_type = "application_completed"
        emoji = {"applied": "✅", "requires_manual_intervention": "⚠️", "failed": "❌", "simulated": "🔄"}.get(status, "ℹ️")
        status_label = status.replace('_', ' ').title()
        reason_suffix = f" — {reason[:200]}" if reason and status in ("failed", "requires_manual_intervention") else ""
        await _emit_autoapply_event(
            run_id, event_type,
            f"[AutoApplyAgent]: {emoji} {entry['job_title']} @ {entry['job_company']}: {status_label}{reason_suffix}",
            {
                "status": status,
                "job_id": entry["job_id"],
                "queue_id": queue_id,
                "job_title": entry["job_title"],
                "job_company": entry["job_company"],
                "stage": "applied" if status == "applied" else status,
                "reason": reason,
            },
            user_id=user_id
        )

    except Exception as fatal_err:
        # ── BULLETPROOF CRASH HANDLER ─────────────────────────────────────────
        # This catches ANY unhandled exception — Playwright segfault, import
        # error, asyncio cancellation, DB error, etc. — and ensures the failure
        # is visible in BOTH the terminal AND the live WebSocket feed.
        tb_str = traceback.format_exc()
        error_msg = f"{type(fatal_err).__name__}: {str(fatal_err)}"
        log.error(f"\n{'='*60}\nDETAILED RUNTIME FAILURE STACK (process_single_autoapply_job):\n{tb_str}{'='*60}")
        print(f"\n{'='*60}\nDETAILED RUNTIME FAILURE STACK:\n{tb_str}{'='*60}", flush=True)

        # Update queue status to failed
        try:
            db_update_queue_status(queue_id, "failed", failure_reason=error_msg[:500])
        except Exception:
            pass

        # Send the EXACT error message to the WebSocket feed
        try:
            await _emit_autoapply_event(
                run_id, "log",
                f"[AutoApplyAgent]: ❌ {entry.get('job_title', 'Unknown')} @ {entry.get('job_company', 'Unknown')}: CRASHED — {error_msg[:300]}",
                {
                    "status": "failed",
                    "job_id": entry.get("job_id", ""),
                    "queue_id": queue_id,
                    "reason": error_msg[:500],
                    "stack_trace": tb_str[:1000],
                },
                user_id=user_id
            )
        except Exception:
            pass

    finally:
        # ── ALWAYS reset agent status to idle ─────────────────────────────────
        try:
            from models import AgentStatus as _AgentStatus
            store.update_agent_status(_AgentStatus(
                agent_id="autoapply",
                name="AutoApply Agent",
                status="idle",
            ))
        except Exception:
            pass


async def run_orchestrator_loop() -> None:
    """
    Persistent background task that polls the auto_apply_queue and dispatches
    the AutoApplyAgent worker for each discovered job.
    """
    from agents.auto_apply_agent import AutoApplyAgent

    log.info("AgentOrchestrator background loop started")
    log.info(f"  Poll interval: {POLL_INTERVAL_SECONDS}s | Max concurrent: {MAX_CONCURRENT_APPLIES}")
    log.info(f"  Cooldown: {APPLY_COOLDOWN_SECONDS}s | Max per cycle: {MAX_PER_CYCLE}")
    log.info(f"  Enabled: {AUTOAPPLY_ENABLED}")

    # Initialize the auto-apply queue table
    try:
        db_init_auto_apply_table()
    except Exception as e:
        log.error(f"Failed to initialize auto_apply_queue table: {e}")

    while True:
        try:
            if not AUTOAPPLY_ENABLED:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            # Poll for discovered jobs
            discovered = db_get_discovered_jobs(limit=MAX_PER_CYCLE)

            if not discovered:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            log.info(f"Orchestrator found {len(discovered)} discovered jobs to process")

            # Process each job (rate-limited)
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_APPLIES)

            async def process_job(entry: dict) -> None:
                async with semaphore:
                    await run_coro_in_thread(process_single_autoapply_job, entry)
                    # Cooldown between applications
                    await asyncio.sleep(APPLY_COOLDOWN_SECONDS)

            # Run all discovered jobs with concurrency limiting
            tasks = [asyncio.create_task(process_job(entry)) for entry in discovered]
            await asyncio.gather(*tasks, return_exceptions=True)

        except asyncio.CancelledError:
            log.info("Orchestrator loop cancelled — shutting down gracefully")
            break
        except Exception as e:
            log.error(f"Orchestrator loop error: {e}", exc_info=True)

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


# ── Public API for Workflow Integration ───────────────────────────────────────

def enqueue_discovered_jobs(
    user_id: str,
    run_id: str,
    scored_jobs: list,
    auto_apply_threshold: int = 70,
) -> int:
    """
    Called by the workflow orchestrator after job scoring is complete.
    Enqueues all jobs above the match threshold into the auto-apply pipeline.
    
    Returns the number of jobs enqueued.
    """
    enqueued = 0
    for job in scored_jobs:
        if isinstance(job, dict):
            match_score = job.get("overall_match", 0)
            job_url = job.get("url", "")
            job_id = job.get("id", str(uuid.uuid4()))
            job_title = job.get("title", "Unknown")
            job_company = job.get("company", "Unknown")
            job_source = job.get("source", "")
        else:
            match_score = getattr(job, "overall_match", 0)
            job_url = getattr(job, "url", "")
            job_id = getattr(job, "id", str(uuid.uuid4()))
            job_title = getattr(job, "title", "Unknown")
            job_company = getattr(job, "company", "Unknown")
            job_source = getattr(job, "source", "")

        # Only auto-apply to jobs with sufficient match score
        if match_score < auto_apply_threshold:
            continue

        # Skip jobs without valid URLs
        if not job_url or job_url.startswith("https://jobs.example"):
            continue

        try:
            db_enqueue_job(
                user_id=user_id,
                run_id=run_id,
                job_id=job_id,
                job_title=job_title,
                job_company=job_company,
                job_url=job_url,
                job_source=job_source,
            )
            enqueued += 1
        except Exception as e:
            log.error(f"Failed to enqueue job: {e}")

    log.info(f"Enqueued {enqueued}/{len(scored_jobs)} jobs for auto-apply (threshold={auto_apply_threshold}%)")
    return enqueued
