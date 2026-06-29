"""
Authentication & User Management for Stellar Career Agent.
Supports both Supabase Auth and local SQLite fallback.
"""
from __future__ import annotations
import hashlib
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt
from pydantic import BaseModel

import supabase_client
from config import get_settings
from logger import get_logger

log = get_logger("Auth")
settings = get_settings()

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


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + hashed.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return hashed.hex() == hash_hex
    except Exception:
        return False


def _create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def register_user(name: str, email: str, password: str) -> tuple[str, dict[str, Any]]:
    """Register a new user using either Supabase or local SQLite DB."""
    email_lower = email.lower().strip()
    
    if supabase_client.SUPABASE_ENABLED:
        supabase = supabase_client.supabase
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
    else:
        # Local SQLite registration
        import db
        if db.get_user_by_email(email_lower):
            raise ValueError("Email already registered")

        user_id = str(uuid.uuid4())
        password_hash = _hash_password(password)

        user_data = {
            "id": user_id,
            "name": name.strip(),
            "email": email_lower,
            "password_hash": password_hash,
            "created_at": datetime.utcnow().isoformat(),
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

        db.save_user(user_data)
        token = _create_token(user_id, email_lower)
        log.info(f"User registered locally: {email_lower} (id={user_id})")

        safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
        return token, safe_user


def login_user(email: str, password: str) -> tuple[str, dict[str, Any]]:
    """Login user. Returns (token, user_data). Raises ValueError on failure."""
    email_lower = email.lower().strip()
    
    if supabase_client.SUPABASE_ENABLED:
        supabase = supabase_client.supabase
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

        log.info(f"User logged in to Supabase: {email_lower}")
        return token, profile
    else:
        # Local SQLite login
        import db
        user_data = db.get_user_by_email(email_lower)

        if not user_data:
            raise ValueError("Invalid email or password")

        if not _verify_password(password, user_data.get("password_hash", "")):
            raise ValueError("Invalid email or password")

        token = _create_token(user_data["id"], email_lower)
        log.info(f"User logged in locally: {email_lower}")

        safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
        return token, safe_user


def get_user_by_token(token: str) -> dict[str, Any] | None:
    """Validate token and return user profile."""
    if supabase_client.SUPABASE_ENABLED:
        supabase = supabase_client.supabase
        try:
            res = supabase.auth.get_user(token)
            if not res or not res.user:
                return None
            user_id = res.user.id
            return get_user_by_id(user_id)
        except Exception as e:
            log.warning(f"Failed to validate Supabase token: {e}")
            return None
    else:
        # Local JWT validation
        payload = _decode_token(token)
        if not payload:
            return None

        email = payload.get("email", "")
        import db
        user_data = db.get_user_by_email(email)
        if not user_data:
            return None

        return {k: v for k, v in user_data.items() if k != "password_hash"}


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Retrieve user profile by ID."""
    if supabase_client.SUPABASE_ENABLED:
        supabase = supabase_client.supabase
        try:
            res = supabase.table("profiles").select("*").eq("id", user_id).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            log.error(f"Failed to retrieve user profile by ID {user_id} from Supabase: {e}")
            return None
    else:
        import db
        user_dict = db.get_user_by_id(user_id)
        if not user_dict:
            return None
        return {k: v for k, v in user_dict.items() if k != "password_hash"}


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

    if supabase_client.SUPABASE_ENABLED:
        supabase = supabase_client.supabase
        try:
            res = supabase.table("profiles").update(filtered_updates).eq("email", email_lower).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            log.error(f"Failed to update profile for {email_lower} in Supabase: {e}")
            return None
    else:
        import db
        user_data = db.get_user_by_email(email_lower)
        if not user_data:
            return None

        for key, value in filtered_updates.items():
            user_data[key] = value

        db.save_user(user_data)
        return {k: v for k, v in user_data.items() if k != "password_hash"}
