"""
Authentication & User Management for Stellar Career Agent.

Real registration and login using JWT tokens.
No mock users. No seeded data. Brand-new users start with empty state.
"""
from __future__ import annotations
import hashlib
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt
from pydantic import BaseModel, Field

from config import get_settings
from logger import get_logger

log = get_logger("Auth")
settings = get_settings()

# ─── SQLite User Store ────────────────────────────────────────────────────────

import db

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


class UserRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Profile data (filled after resume parsing)
    title: str = ""
    location: str = ""
    skills: list[str] = []
    resume_score: int = 0
    ats_score: int = 0
    missing_skills: list[str] = []
    run_id: str = ""  # latest workflow run


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
    """Register a new user. Returns (token, user_data). Raises ValueError on duplicate."""
    email_lower = email.lower().strip()
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
        "run_id": "",
    }

    db.save_user(user_data)
    token = _create_token(user_id, email_lower)
    log.info(f"User registered: {email_lower} (id={user_id})")

    # Return safe user data (no password hash)
    safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
    return token, safe_user


def login_user(email: str, password: str) -> tuple[str, dict[str, Any]]:
    """Login user. Returns (token, user_data). Raises ValueError on failure."""
    email_lower = email.lower().strip()
    user_data = db.get_user_by_email(email_lower)

    if not user_data:
        raise ValueError("Invalid email or password")

    if not _verify_password(password, user_data["password_hash"]):
        raise ValueError("Invalid email or password")

    token = _create_token(user_data["id"], email_lower)
    log.info(f"User logged in: {email_lower}")

    safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
    return token, safe_user


def get_user_by_token(token: str) -> dict[str, Any] | None:
    """Validate token and return user data."""
    payload = _decode_token(token)
    if not payload:
        return None

    email = payload.get("email", "")
    user_data = db.get_user_by_email(email)
    if not user_data:
        return None

    return {k: v for k, v in user_data.items() if k != "password_hash"}


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Get user by ID."""
    user_data = db.get_user_by_id(user_id)
    if not user_data:
        return None
    return {k: v for k, v in user_data.items() if k != "password_hash"}


def update_user_profile(email: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update user profile fields."""
    email_lower = email.lower().strip()
    user_data = db.get_user_by_email(email_lower)
    if not user_data:
        return None

    for key, value in updates.items():
        if key not in ("id", "email", "password_hash", "created_at"):
            user_data[key] = value

    db.save_user(user_data)
    return {k: v for k, v in user_data.items() if k != "password_hash"}
