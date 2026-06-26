"""
Authentication & User Management for Stellar Career Agent using Supabase.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel
import supabase_client
from logger import get_logger

log = get_logger("Auth")
supabase = supabase_client.supabase

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict[str, Any]


def register_user(name: str, email: str, password: str) -> tuple[str, dict[str, Any]]:
    """Register a new user in Supabase Auth and create their profile in the database."""
    email_lower = email.lower().strip()
    
    # 1. Check if user already exists in profiles
    try:
        existing = supabase.table("profiles").select("*").eq("email", email_lower).execute()
        if existing.data:
            raise ValueError("Email already registered")
    except Exception as e:
        if "Email already registered" in str(e):
            raise
        log.warning(f"Error checking existing profile: {e}")

    # 2. Create user in Supabase Auth
    # We attempt admin create first to automatically confirm email (if service role permits)
    user_id = None
    try:
        admin_res = supabase.auth.admin.create_user({
            "email": email_lower,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"name": name.strip()}
        })
        user_id = admin_res.user.id
        log.info(f"User created via admin API: {email_lower} (id={user_id})")
    except Exception as e:
        log.warning(f"Admin user creation failed, falling back to public signUp: {e}")
        try:
            signup_res = supabase.auth.sign_up({
                "email": email_lower,
                "password": password,
                "options": {"data": {"name": name.strip()}}
            })
            user_id = signup_res.user.id
            log.info(f"User registered via public signUp: {email_lower} (id={user_id})")
        except Exception as signUp_err:
            raise ValueError(f"Signup failed: {str(signUp_err)}")

    if not user_id:
        raise ValueError("Failed to retrieve user ID from Supabase Auth response")

    # 3. Create profile in 'profiles' table
    profile_data = {
        "id": user_id,
        "name": name.strip(),
        "email": email_lower,
        "title": "",
        "location": "",
        "skills": [],
        "resume_score": 0,
        "ats_score": 0,
        "missing_skills": [],
        "improvements": [],
        "run_id": "",
        "raw_text": "",
        "resume_text": "",
        "resume_path": "",
        "experience": [],
        "preferences": {},
        "keywords": []
    }

    try:
        supabase.table("profiles").insert(profile_data).execute()
        log.info(f"Profile created for user ID: {user_id}")
    except Exception as e:
        log.error(f"Failed to create user profile in database: {e}")

    # 4. Sign in to obtain access token
    try:
        login_res = supabase.auth.sign_in_with_password({"email": email_lower, "password": password})
        token = login_res.session.access_token
        return token, profile_data
    except Exception as e:
        raise ValueError(f"Account created, but automatic sign-in failed: {str(e)}")


def login_user(email: str, password: str) -> tuple[str, dict[str, Any]]:
    """Login user via Supabase Auth and retrieve their profile."""
    email_lower = email.lower().strip()
    try:
        login_res = supabase.auth.sign_in_with_password({"email": email_lower, "password": password})
        token = login_res.session.access_token
        user_id = login_res.user.id
    except Exception as e:
        raise ValueError("Invalid email or password")

    # Retrieve profile
    profile = get_user_by_id(user_id)
    if not profile:
        # Create a fallback profile if none exists in profiles table
        name = login_res.user.user_metadata.get("name", "User") if login_res.user.user_metadata else "User"
        profile = {
            "id": user_id,
            "name": name,
            "email": email_lower,
            "title": "",
            "location": "",
            "skills": [],
            "resume_score": 0,
            "ats_score": 0,
            "missing_skills": [],
            "improvements": [],
            "run_id": "",
            "raw_text": "",
            "resume_text": "",
            "resume_path": "",
            "experience": [],
            "preferences": {},
            "keywords": []
        }
        try:
            supabase.table("profiles").insert(profile).execute()
            log.info(f"On-demand profile created for user ID: {user_id}")
        except Exception as e:
            log.error(f"Failed to create on-demand profile: {e}")

    log.info(f"User logged in: {email_lower}")
    return token, profile


def get_user_by_token(token: str) -> dict[str, Any] | None:
    """Validate Supabase JWT and return user profile."""
    try:
        res = supabase.auth.get_user(token)
        if not res or not res.user:
            return None
        user_id = res.user.id
        return get_user_by_id(user_id)
    except Exception as e:
        log.warning(f"Failed to validate token: {e}")
        return None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Retrieve user profile by ID from the database."""
    try:
        res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        log.error(f"Failed to retrieve user profile by ID {user_id}: {e}")
        return None


def update_user_profile(email: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update user profile fields in the database."""
    email_lower = email.lower().strip()
    
    # Filter out read-only fields
    filtered_updates = {}
    allowed_keys = {
        "name", "resume_path", "resume_text", "skills", "experience", 
        "preferences", "title", "location", "resume_score", "ats_score", 
        "missing_skills", "improvements", "run_id", "keywords", "raw_text"
    }
    
    # For backward compatibility: if updates has 'raw_text', store it in 'resume_text' too
    if "raw_text" in updates and "resume_text" not in updates:
        updates["resume_text"] = updates["raw_text"]
        
    for k, v in updates.items():
        if k in allowed_keys:
            filtered_updates[k] = v

    try:
        res = supabase.table("profiles").update(filtered_updates).eq("email", email_lower).execute()
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        log.error(f"Failed to update profile for {email_lower}: {e}")
        return None
