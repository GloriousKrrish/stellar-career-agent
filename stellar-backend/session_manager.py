"""
session_manager.py
==================
Persistent browser session storage per job-portal platform.

Stores cookies, localStorage, and sessionStorage snapshots so that
subsequent automation runs can skip login if the session is still valid.

Sessions are saved as JSON files inside the ``cookies/`` directory:
    cookies/session_naukri.json
    cookies/session_linkedin.json
    ...

Each file contains:
    {
        "platform": "naukri",
        "cookies": [...],
        "local_storage": {...},
        "session_storage": {...},
        "saved_at": "2026-07-16T10:00:00Z",
        "expires_hint": "2026-07-17T10:00:00Z",   # best-effort
        "applications_count": 5
    }
"""
from __future__ import annotations

import json
import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from urllib.parse import urlparse

log = logging.getLogger("SessionManager")

# ── Directory for session files ──────────────────────────────────────────────
SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies")
os.makedirs(SESSION_DIR, exist_ok=True)

# ── Platform domain → canonical name mapping ─────────────────────────────────
PLATFORM_MAP: dict[str, str] = {
    "naukri.com": "naukri",
    "linkedin.com": "linkedin",
    "indeed.com": "indeed",
    "glassdoor.com": "glassdoor",
    "glassdoor.co.in": "glassdoor",
    "wellfound.com": "wellfound",
    "monster.com": "monster",
    "shine.com": "shine",
    "foundit.in": "foundit",
    "instahyre.com": "instahyre",
}

# Default session TTL when we cannot infer from cookies (24 hours)
DEFAULT_SESSION_TTL_HOURS = 24


def url_to_platform(url: str) -> Optional[str]:
    """Extract the canonical platform name from a job URL."""
    try:
        domain = urlparse(url).netloc.lower()
        for domain_key, platform in PLATFORM_MAP.items():
            if domain_key in domain:
                return platform
    except Exception:
        pass
    return None


def _session_path(platform: str) -> str:
    return os.path.join(SESSION_DIR, f"session_{platform}.json")


# ── Public API ────────────────────────────────────────────────────────────────

def get_session(platform: str) -> Optional[dict]:
    """Load a saved session for the given platform.  Returns None if absent."""
    path = _session_path(platform)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        log.warning(f"Failed to load session for {platform}: {e}")
        return None


def is_session_valid(platform: str) -> tuple[bool, Optional[dict]]:
    """
    Check whether a saved session exists and is likely still valid.

    Returns (is_valid, session_data).
    A session is considered expired if:
      - ``expires_hint`` is in the past, OR
      - ``saved_at`` is older than DEFAULT_SESSION_TTL_HOURS and no
        ``expires_hint`` was recorded.
    """
    session = get_session(platform)
    if not session:
        return False, None

    now = datetime.now(timezone.utc)

    # Check explicit expiry hint
    expires_hint = session.get("expires_hint")
    if expires_hint:
        try:
            exp_dt = datetime.fromisoformat(expires_hint)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if now > exp_dt:
                log.info(f"Session for {platform} expired at {expires_hint}")
                return False, session
        except Exception:
            pass

    # Fallback: check saved_at age
    saved_at = session.get("saved_at")
    if saved_at:
        try:
            saved_dt = datetime.fromisoformat(saved_at)
            if saved_dt.tzinfo is None:
                saved_dt = saved_dt.replace(tzinfo=timezone.utc)
            if now - saved_dt > timedelta(hours=DEFAULT_SESSION_TTL_HOURS):
                log.info(f"Session for {platform} is older than {DEFAULT_SESSION_TTL_HOURS}h — treating as expired")
                return False, session
        except Exception:
            pass

    return True, session


async def save_session_from_browser(context: Any, page: Any, platform: str) -> dict:
    """
    Capture the current browser session (cookies + web storage) and persist it.

    Parameters
    ----------
    context : playwright BrowserContext
    page : playwright Page (used for localStorage/sessionStorage extraction)
    platform : canonical platform name (e.g. "naukri")

    Returns the saved session dict.
    """
    cookies = await context.cookies()

    # Determine best-effort expiry from cookies
    max_expiry: float = 0
    playwright_cookies = []
    for c in cookies:
        cookie_obj = {
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
        }
        if c.get("httpOnly") is not None:
            cookie_obj["httpOnly"] = bool(c["httpOnly"])
        if c.get("secure") is not None:
            cookie_obj["secure"] = bool(c["secure"])
        if c.get("sameSite"):
            ss = str(c["sameSite"]).capitalize()
            if ss in ("Strict", "Lax", "None"):
                cookie_obj["sameSite"] = ss
        if c.get("expires") and c["expires"] > 0:
            cookie_obj["expires"] = c["expires"]
            if c["expires"] > max_expiry:
                max_expiry = c["expires"]
        playwright_cookies.append(cookie_obj)

    # Extract localStorage and sessionStorage via page.evaluate
    local_storage = {}
    session_storage = {}
    try:
        local_storage = await page.evaluate("""() => {
            const items = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                items[key] = localStorage.getItem(key);
            }
            return items;
        }""")
    except Exception as e:
        log.debug(f"Could not extract localStorage for {platform}: {e}")

    try:
        session_storage = await page.evaluate("""() => {
            const items = {};
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                items[key] = sessionStorage.getItem(key);
            }
            return items;
        }""")
    except Exception as e:
        log.debug(f"Could not extract sessionStorage for {platform}: {e}")

    now_iso = datetime.now(timezone.utc).isoformat()
    expires_hint = None
    if max_expiry > 0:
        try:
            expires_hint = datetime.fromtimestamp(max_expiry, tz=timezone.utc).isoformat()
        except Exception:
            pass

    # Load existing session to preserve applications_count
    existing = get_session(platform) or {}
    apps_count = existing.get("applications_count", 0)

    session_data = {
        "platform": platform,
        "cookies": playwright_cookies,
        "local_storage": local_storage,
        "session_storage": session_storage,
        "saved_at": now_iso,
        "expires_hint": expires_hint,
        "applications_count": apps_count,
    }

    path = _session_path(platform)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, default=str)
        log.info(f"Session saved for {platform} ({len(playwright_cookies)} cookies, {len(local_storage)} localStorage keys)")
    except Exception as e:
        log.error(f"Failed to save session for {platform}: {e}")

    return session_data


async def inject_session(context: Any, page: Any, platform: str, logger: Any = None) -> bool:
    """
    Inject a previously saved session into the browser context.

    Returns True if cookies were injected successfully.
    """
    valid, session = is_session_valid(platform)
    if not valid or not session:
        if logger:
            await logger.log(f"ℹ️ No valid saved session for {platform} — login will be required.")
        return False

    cookies = session.get("cookies", [])
    if cookies:
        try:
            await context.add_cookies(cookies)
            if logger:
                await logger.log(f"🔑 Injected {len(cookies)} saved session cookies for {platform}")
        except Exception as e:
            log.warning(f"Cookie injection failed for {platform}: {e}")
            return False

    # Inject localStorage
    local_storage = session.get("local_storage", {})
    if local_storage and page:
        try:
            await page.evaluate("""(items) => {
                for (const [key, value] of Object.entries(items)) {
                    localStorage.setItem(key, value);
                }
            }""", local_storage)
            if logger:
                await logger.log(f"🗄️ Restored {len(local_storage)} localStorage entries for {platform}")
        except Exception as e:
            log.debug(f"localStorage injection failed for {platform}: {e}")

    return True


def increment_session_app_count(platform: str) -> None:
    """Increment the applications_count for a platform session."""
    session = get_session(platform)
    if session:
        session["applications_count"] = session.get("applications_count", 0) + 1
        path = _session_path(platform)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2, default=str)
        except Exception:
            pass


def clear_session(platform: str) -> bool:
    """Delete a saved session for the given platform."""
    path = _session_path(platform)
    if os.path.isfile(path):
        try:
            os.remove(path)
            log.info(f"Session cleared for {platform}")
            return True
        except Exception as e:
            log.error(f"Failed to clear session for {platform}: {e}")
    return False


def get_all_sessions_status() -> list[dict]:
    """
    Return a summary of all known platform sessions for the dashboard.

    Each entry:
        {
            "platform": "naukri",
            "status": "active" | "expired" | "none",
            "saved_at": "2026-07-16T10:00:00Z" | null,
            "expires_hint": "..." | null,
            "applications_count": 5,
            "cookie_count": 42,
        }
    """
    results = []
    for domain_key, platform in PLATFORM_MAP.items():
        # Avoid duplicates (glassdoor has two domain keys)
        if any(r["platform"] == platform for r in results):
            continue

        valid, session = is_session_valid(platform)
        if session:
            results.append({
                "platform": platform,
                "status": "active" if valid else "expired",
                "saved_at": session.get("saved_at"),
                "expires_hint": session.get("expires_hint"),
                "applications_count": session.get("applications_count", 0),
                "cookie_count": len(session.get("cookies", [])),
            })
        else:
            results.append({
                "platform": platform,
                "status": "none",
                "saved_at": None,
                "expires_hint": None,
                "applications_count": 0,
                "cookie_count": 0,
            })
    return results
