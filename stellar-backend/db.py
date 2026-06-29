import sqlite3
import json
import os
from datetime import datetime
from typing import Any, List, Dict, Optional
from models import WorkflowState, UserProfile, CareerProfile, MarketReport, RawJob, ScoredJob, AgentStatus
from logger import get_logger
import supabase_client

log = get_logger("Database")
DB_PATH = os.path.join(os.path.dirname(__file__), "stellar.db")

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
IS_POSTGRES = DATABASE_URL is not None and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://"))

if IS_POSTGRES and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_db_connection():
    if IS_POSTGRES:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def get_db_cursor(conn):
    if IS_POSTGRES:
        from psycopg2.extras import DictCursor
        return conn.cursor(cursor_factory=DictCursor)
    else:
        return conn.cursor()

def init_db():
    log.info(f"Initializing database. Postgres={IS_POSTGRES}")
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    # Create Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        title TEXT DEFAULT '',
        location TEXT DEFAULT '',
        skills TEXT DEFAULT '[]',
        resume_score INTEGER DEFAULT 0,
        ats_score INTEGER DEFAULT 0,
        missing_skills TEXT DEFAULT '[]',
        improvements TEXT DEFAULT '[]',
        run_id TEXT DEFAULT '',
        raw_text TEXT DEFAULT '',
        keywords TEXT DEFAULT '[]',
        experience TEXT DEFAULT '[]',
        preferences TEXT DEFAULT '{}'
    )
    """)
    
    # Ensure keywords, experience, and preferences columns exist if DB was already created without them
    for col, default_val in [("keywords", "[]"), ("experience", "[]"), ("preferences", "{}")]:
        try:
            if IS_POSTGRES:
                cursor.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} TEXT DEFAULT '{default_val}'")
            else:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT '{default_val}'")
        except Exception:
            pass
    
    # Create Workflows table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workflows (
        run_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        status TEXT NOT NULL,
        current_step TEXT NOT NULL,
        steps_completed TEXT NOT NULL, -- JSON list
        user_profile TEXT, -- JSON dict
        career_profile TEXT, -- JSON dict
        market_report TEXT, -- JSON dict
        raw_jobs TEXT, -- JSON list
        scored_jobs TEXT, -- JSON list
        error TEXT,
        action_required_reason TEXT,
        action_required_url TEXT,
        action_required_screenshot TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    
    # Create Applications table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        company_logo TEXT NOT NULL,
        stage TEXT NOT NULL,
        location TEXT DEFAULT '',
        salary TEXT DEFAULT '',
        url TEXT DEFAULT '',
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    
    conn.commit()
    conn.close()
    log.info("Database initialized successfully")

# Run DB initialization immediately when the module is imported
init_db()



# ─── User Operations ─────────────────────────────────────────────────────────

def save_user(user_data: dict) -> None:
    if supabase_client.SUPABASE_ENABLED:
        # Map fields for compatibility
        supabase_data = {
            "id": user_data["id"],
            "name": user_data["name"],
            "email": user_data["email"],
            "title": user_data.get("title", ""),
            "location": user_data.get("location", ""),
            "skills": user_data.get("skills") if isinstance(user_data.get("skills"), list) else [],
            "resume_score": user_data.get("resume_score", 0),
            "ats_score": user_data.get("ats_score", 0),
            "missing_skills": user_data.get("missing_skills") if isinstance(user_data.get("missing_skills"), list) else [],
            "improvements": user_data.get("improvements") if isinstance(user_data.get("improvements"), list) else [],
            "run_id": user_data.get("run_id", ""),
            "raw_text": user_data.get("raw_text", ""),
            "resume_text": user_data.get("raw_text", ""),
            "keywords": user_data.get("keywords") if isinstance(user_data.get("keywords"), list) else [],
            "resume_path": user_data.get("resume_path", ""),
            "experience": user_data.get("experience") if isinstance(user_data.get("experience"), list) else [],
            "preferences": user_data.get("preferences") if isinstance(user_data.get("preferences"), dict) else {}
        }
        try:
            from supabase_client import supabase
            supabase.table("profiles").upsert(supabase_data).execute()
            log.info(f"User profile saved to Supabase: {user_data['email']}")
        except Exception as e:
            log.error(f"Failed to save user profile to Supabase: {e}")
    else:
        conn = get_db_connection()
        cursor = get_db_cursor(conn)
        
        password_hash = user_data.get("password_hash")
        if not password_hash:
            existing = get_user_by_id(user_data["id"])
            if existing:
                password_hash = existing.get("password_hash")
        
        created_at = user_data.get("created_at") or datetime.utcnow().isoformat()
        
        if IS_POSTGRES:
            cursor.execute("""
            INSERT INTO users (
                id, name, email, password_hash, created_at, title, location, skills,
                resume_score, ats_score, missing_skills, improvements, run_id, raw_text, keywords, experience, preferences
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                created_at = EXCLUDED.created_at,
                title = EXCLUDED.title,
                location = EXCLUDED.location,
                skills = EXCLUDED.skills,
                resume_score = EXCLUDED.resume_score,
                ats_score = EXCLUDED.ats_score,
                missing_skills = EXCLUDED.missing_skills,
                improvements = EXCLUDED.improvements,
                run_id = EXCLUDED.run_id,
                raw_text = EXCLUDED.raw_text,
                keywords = EXCLUDED.keywords,
                experience = EXCLUDED.experience,
                preferences = EXCLUDED.preferences
            """, (
                user_data["id"],
                user_data["name"],
                user_data["email"],
                password_hash or "",
                created_at,
                user_data.get("title", ""),
                user_data.get("location", ""),
                json.dumps(user_data.get("skills", [])),
                user_data.get("resume_score", 0),
                user_data.get("ats_score", 0),
                json.dumps(user_data.get("missing_skills", [])),
                json.dumps(user_data.get("improvements", [])),
                user_data.get("run_id", ""),
                user_data.get("raw_text", ""),
                json.dumps(user_data.get("keywords", [])),
                json.dumps(user_data.get("experience", [])),
                json.dumps(user_data.get("preferences", {}))
            ))
        else:
            cursor.execute("""
            INSERT OR REPLACE INTO users (
                id, name, email, password_hash, created_at, title, location, skills,
                resume_score, ats_score, missing_skills, improvements, run_id, raw_text, keywords, experience, preferences
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data["id"],
                user_data["name"],
                user_data["email"],
                password_hash or "",
                created_at,
                user_data.get("title", ""),
                user_data.get("location", ""),
                json.dumps(user_data.get("skills", [])),
                user_data.get("resume_score", 0),
                user_data.get("ats_score", 0),
                json.dumps(user_data.get("missing_skills", [])),
                json.dumps(user_data.get("improvements", [])),
                user_data.get("run_id", ""),
                user_data.get("raw_text", ""),
                json.dumps(user_data.get("keywords", [])),
                json.dumps(user_data.get("experience", [])),
                json.dumps(user_data.get("preferences", {}))
            ))
        conn.commit()
        conn.close()
        log.info(f"User profile saved to local DB: {user_data['email']}")

def get_user_by_email(email: str) -> Optional[dict]:
    if supabase_client.SUPABASE_ENABLED:
        try:
            from supabase_client import supabase
            res = supabase.table("profiles").select("*").eq("email", email.lower().strip()).execute()
            if res.data:
                profile = res.data[0]
                profile["raw_text"] = profile.get("resume_text") or profile.get("raw_text") or ""
                return profile
            return None
        except Exception as e:
            log.error(f"Failed to get user by email from Supabase: {e}")
            return None
    else:
        conn = get_db_connection()
        cursor = get_db_cursor(conn)
        if IS_POSTGRES:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email.lower().strip(),))
        else:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        
        user_dict = dict(row)
        user_dict["skills"] = json.loads(user_dict["skills"]) if user_dict["skills"] else []
        user_dict["missing_skills"] = json.loads(user_dict["missing_skills"]) if user_dict["missing_skills"] else []
        user_dict["improvements"] = json.loads(user_dict["improvements"]) if user_dict["improvements"] else []
        user_dict["keywords"] = json.loads(user_dict["keywords"]) if "keywords" in user_dict and user_dict["keywords"] else []
        user_dict["experience"] = json.loads(user_dict["experience"]) if "experience" in user_dict and user_dict["experience"] else []
        user_dict["preferences"] = json.loads(user_dict["preferences"]) if "preferences" in user_dict and user_dict["preferences"] else {}
        return user_dict

def get_user_by_id(user_id: str) -> Optional[dict]:
    if supabase_client.SUPABASE_ENABLED:
        try:
            from supabase_client import supabase
            res = supabase.table("profiles").select("*").eq("id", user_id).execute()
            if res.data:
                profile = res.data[0]
                profile["raw_text"] = profile.get("resume_text") or profile.get("raw_text") or ""
                return profile
            return None
        except Exception as e:
            log.error(f"Failed to get user by ID from Supabase: {e}")
            return None
    else:
        conn = get_db_connection()
        cursor = get_db_cursor(conn)
        if IS_POSTGRES:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        else:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        
        user_dict = dict(row)
        user_dict["skills"] = json.loads(user_dict["skills"]) if user_dict["skills"] else []
        user_dict["missing_skills"] = json.loads(user_dict["missing_skills"]) if user_dict["missing_skills"] else []
        user_dict["improvements"] = json.loads(user_dict["improvements"]) if user_dict["improvements"] else []
        user_dict["keywords"] = json.loads(user_dict["keywords"]) if "keywords" in user_dict and user_dict["keywords"] else []
        user_dict["experience"] = json.loads(user_dict["experience"]) if "experience" in user_dict and user_dict["experience"] else []
        user_dict["preferences"] = json.loads(user_dict["preferences"]) if "preferences" in user_dict and user_dict["preferences"] else {}
        return user_dict



# ─── Workflow Operations ─────────────────────────────────────────────────────

def db_save_workflow(state: WorkflowState) -> None:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    
    user_profile_json = state.user_profile.model_dump_json() if state.user_profile else None
    career_profile_json = state.career_profile.model_dump_json() if state.career_profile else None
    market_report_json = state.market_report.model_dump_json() if state.market_report else None
    raw_jobs_json = json.dumps([j.model_dump(mode="json") for j in state.raw_jobs]) if state.raw_jobs else "[]"
    scored_jobs_json = json.dumps([j.model_dump(mode="json") for j in state.scored_jobs]) if state.scored_jobs else "[]"
    steps_completed_json = json.dumps(state.steps_completed)
    
    if IS_POSTGRES:
        cursor.execute("""
        INSERT INTO workflows (
            run_id, user_id, status, current_step, steps_completed, user_profile,
            career_profile, market_report, raw_jobs, scored_jobs, error,
            action_required_reason, action_required_url, action_required_screenshot,
            created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (run_id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            status = EXCLUDED.status,
            current_step = EXCLUDED.current_step,
            steps_completed = EXCLUDED.steps_completed,
            user_profile = EXCLUDED.user_profile,
            career_profile = EXCLUDED.career_profile,
            market_report = EXCLUDED.market_report,
            raw_jobs = EXCLUDED.raw_jobs,
            scored_jobs = EXCLUDED.scored_jobs,
            error = EXCLUDED.error,
            action_required_reason = EXCLUDED.action_required_reason,
            action_required_url = EXCLUDED.action_required_url,
            action_required_screenshot = EXCLUDED.action_required_screenshot,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at
        """, (
            state.run_id,
            state.user_id,
            state.status,
            state.current_step,
            steps_completed_json,
            user_profile_json,
            career_profile_json,
            market_report_json,
            raw_jobs_json,
            scored_jobs_json,
            state.error,
            state.action_required.reason if state.action_required else None,
            state.action_required.url if state.action_required else None,
            state.action_required.screenshot if state.action_required else None,
            state.created_at.isoformat() if isinstance(state.created_at, datetime) else str(state.created_at),
            state.updated_at.isoformat() if isinstance(state.updated_at, datetime) else str(state.updated_at)
        ))
    else:
        cursor.execute("""
        INSERT OR REPLACE INTO workflows (
            run_id, user_id, status, current_step, steps_completed, user_profile,
            career_profile, market_report, raw_jobs, scored_jobs, error,
            action_required_reason, action_required_url, action_required_screenshot,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            state.run_id,
            state.user_id,
            state.status,
            state.current_step,
            steps_completed_json,
            user_profile_json,
            career_profile_json,
            market_report_json,
            raw_jobs_json,
            scored_jobs_json,
            state.error,
            state.action_required.reason if state.action_required else None,
            state.action_required.url if state.action_required else None,
            state.action_required.screenshot if state.action_required else None,
            state.created_at.isoformat() if isinstance(state.created_at, datetime) else str(state.created_at),
            state.updated_at.isoformat() if isinstance(state.updated_at, datetime) else str(state.updated_at)
        ))
    conn.commit()
    conn.close()

def db_get_workflow(run_id: str) -> Optional[WorkflowState]:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    if IS_POSTGRES:
        cursor.execute("SELECT * FROM workflows WHERE run_id = %s", (run_id,))
    else:
        cursor.execute("SELECT * FROM workflows WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    
    row_dict = dict(row)
    
    user_profile = UserProfile.model_validate_json(row_dict["user_profile"]) if row_dict["user_profile"] else None
    career_profile = CareerProfile.model_validate_json(row_dict["career_profile"]) if row_dict["career_profile"] else None
    market_report = MarketReport.model_validate_json(row_dict["market_report"]) if row_dict["market_report"] else None
    
    raw_jobs = []
    if row_dict["raw_jobs"]:
        raw_jobs = [RawJob.model_validate(j) for j in json.loads(row_dict["raw_jobs"])]
        
    scored_jobs = []
    if row_dict["scored_jobs"]:
        scored_jobs = [ScoredJob.model_validate(j) for j in json.loads(row_dict["scored_jobs"])]
    
    action_required = None
    if row_dict["action_required_reason"]:
        from models import ActionRequiredResponse
        action_required = ActionRequiredResponse(
            reason=row_dict["action_required_reason"],
            url=row_dict["action_required_url"],
            screenshot=row_dict["action_required_screenshot"] or ""
        )
        
    created_at = datetime.fromisoformat(row_dict["created_at"])
    updated_at = datetime.fromisoformat(row_dict["updated_at"])
    
    return WorkflowState(
        run_id=row_dict["run_id"],
        user_id=row_dict["user_id"],
        status=row_dict["status"],
        current_step=row_dict["current_step"],
        steps_completed=json.loads(row_dict["steps_completed"]),
        user_profile=user_profile,
        career_profile=career_profile,
        market_report=market_report,
        raw_jobs=raw_jobs,
        scored_jobs=scored_jobs,
        error=row_dict["error"],
        action_required=action_required,
        created_at=created_at,
        updated_at=updated_at
    )

def db_all_workflows() -> List[WorkflowState]:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT run_id FROM workflows ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    workflows = []
    for r in rows:
        w = db_get_workflow(r["run_id"])
        if w:
            workflows.append(w)
    return workflows


# ─── Application Operations ──────────────────────────────────────────────────

def db_save_application(app_data: dict) -> None:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    if IS_POSTGRES:
        cursor.execute("""
        INSERT INTO applications (
            id, user_id, job_id, title, company, company_logo, stage, location, salary, url, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            job_id = EXCLUDED.job_id,
            title = EXCLUDED.title,
            company = EXCLUDED.company,
            company_logo = EXCLUDED.company_logo,
            stage = EXCLUDED.stage,
            location = EXCLUDED.location,
            salary = EXCLUDED.salary,
            url = EXCLUDED.url,
            updated_at = EXCLUDED.updated_at
        """, (
            app_data["id"],
            app_data["user_id"],
            app_data["job_id"],
            app_data["title"],
            app_data["company"],
            app_data.get("company_logo", app_data["company"][0].upper() if app_data["company"] else "?"),
            app_data["stage"],
            app_data.get("location", ""),
            app_data.get("salary", ""),
            app_data.get("url", ""),
            app_data.get("updated_at", datetime.utcnow().isoformat())
        ))
    else:
        cursor.execute("""
        INSERT OR REPLACE INTO applications (
            id, user_id, job_id, title, company, company_logo, stage, location, salary, url, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app_data["id"],
            app_data["user_id"],
            app_data["job_id"],
            app_data["title"],
            app_data["company"],
            app_data.get("company_logo", app_data["company"][0].upper() if app_data["company"] else "?"),
            app_data["stage"],
            app_data.get("location", ""),
            app_data.get("salary", ""),
            app_data.get("url", ""),
            app_data.get("updated_at", datetime.utcnow().isoformat())
        ))
    conn.commit()
    conn.close()

def db_get_applications_by_user(user_id: str) -> List[dict]:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    if IS_POSTGRES:
        cursor.execute("SELECT * FROM applications WHERE user_id = %s ORDER BY updated_at DESC", (user_id,))
    else:
        cursor.execute("SELECT * FROM applications WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_get_application(app_id: str) -> Optional[dict]:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    if IS_POSTGRES:
        cursor.execute("SELECT * FROM applications WHERE id = %s", (app_id,))
    else:
        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def db_delete_application(app_id: str) -> None:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    if IS_POSTGRES:
        cursor.execute("DELETE FROM applications WHERE id = %s", (app_id,))
    else:
        cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()
