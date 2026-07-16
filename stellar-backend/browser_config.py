"""
browser_config.py
=================
Central configuration for the Playwright browser engine.

Supports two operational modes:
  - Development Mode: Launches Chrome against a persistent, user-chosen profile.
    Cookies and login sessions are reused. Browser stays open after execution.
  - Production Mode: Launches an isolated Playwright-managed Chromium.
    Resources are released automatically after each job application.

Settings are loaded from environment variables or the database user-settings table,
so no path is ever hardcoded in source code.
"""
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("BrowserConfig")


# ── Defaults from environment variables ──────────────────────────────────────
# These can be overridden at any time via the /api/settings/browser endpoint.

def _default_profile_dir() -> str:
    """
    Compute a safe, cross-platform default Chrome profile path.
    Points to a Stellar-dedicated profile so we never touch the user's
    primary browser profile.
    """
    if sys.platform == "win32":
        base = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Google", "Chrome", "User Data"
        )
    elif sys.platform == "darwin":
        base = os.path.expanduser(
            "~/Library/Application Support/Google/Chrome"
        )
    else:
        base = os.path.expanduser("~/.config/google-chrome")

    # Use a separate sub-profile, never "Default"
    return os.path.join(base, "StellarAutomation")


@dataclass
class BrowserConfig:
    """
    Immutable snapshot of browser settings for one application run.

    Fields
    ------
    mode : "development" | "production"
        Development  → persistent profile, sessions reused, browser stays open.
        Production   → isolated context, closed automatically on finish.
    browser_executable_path : str | None
        Absolute path to chrome/chromium binary.  None = use Playwright's
        bundled Chromium.
    profile_path : str | None
        Path to the Chrome user-data directory used in Development Mode.
        Must NOT be the profile already open in another Chrome process.
    keep_open : bool
        When True the browser window is kept alive after the job run
        (always True in Development Mode, ignored in Production Mode).
    debug_logging : bool
        Emit verbose Playwright action logs to the WebSocket stream.
    headless : bool
        Run Chrome without a visible window.
        Forced to False in Development Mode.
    slow_mo : int
        Milliseconds added between Playwright actions (simulates human cadence).
    """
    mode: str = field(
        default_factory=lambda: os.getenv("BROWSER_MODE", "production").lower()
    )
    browser_executable_path: Optional[str] = field(
        default_factory=lambda: os.getenv("BROWSER_EXECUTABLE_PATH") or None
    )
    profile_path: Optional[str] = field(
        default_factory=lambda: os.getenv("BROWSER_PROFILE_PATH") or None
    )
    keep_open: bool = field(
        default_factory=lambda: os.getenv("BROWSER_KEEP_OPEN", "false").lower() in ("true", "1", "yes")
    )
    debug_logging: bool = field(
        default_factory=lambda: os.getenv("BROWSER_DEBUG_LOGGING", "false").lower() in ("true", "1", "yes")
    )
    headless: bool = field(
        default_factory=lambda: os.getenv("AUTOAPPLY_HEADLESS", "false").lower() in ("true", "1", "yes")
    )
    slow_mo: int = field(
        default_factory=lambda: int(os.getenv("AUTOAPPLY_SLOW_MO", "1200"))
    )

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_development(self) -> bool:
        return self.mode == "development"

    @property
    def effective_headless(self) -> bool:
        """Development Mode is always headful so the user can inspect the browser."""
        if self.is_development:
            return False
        return self.headless

    @property
    def effective_keep_open(self) -> bool:
        """Development Mode always keeps the browser open."""
        if self.is_development:
            return True
        return self.keep_open

    @property
    def effective_profile_path(self) -> str:
        """
        Returns the resolved profile path.
        - Development Mode: uses `profile_path` if set, else the computed default.
        - Production Mode: uses a dedicated 'StellarProd' sub-profile inside the
          default Chrome user-data dir (isolated from the user's real sessions).
        """
        if self.profile_path:
            return self.profile_path
        if self.is_development:
            return _default_profile_dir()
        # Production: use a separate profile under the same base directory
        if sys.platform == "win32":
            base = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "Google", "Chrome", "User Data"
            )
        elif sys.platform == "darwin":
            base = os.path.expanduser(
                "~/Library/Application Support/Google/Chrome"
            )
        else:
            base = os.path.expanduser("~/.config/google-chrome")
        return os.path.join(base, "StellarProd")

    # ── Profile-lock detection ─────────────────────────────────────────────────

    def is_profile_in_use(self) -> tuple[bool, str]:
        """
        Detect whether the target Chrome profile is currently locked by another
        Chrome process.  Uses two heuristics:
          1. The presence of a 'SingletonLock' or 'lockfile' inside the profile.
          2. A running Chrome process whose command line references the same path.

        Returns
        -------
        (in_use: bool, message: str)
        """
        profile_dir = self.effective_profile_path

        # Heuristic 1 — singleton lock file
        lock_files = [
            os.path.join(profile_dir, "SingletonLock"),
            os.path.join(profile_dir, "SingletonSocket"),
            os.path.join(profile_dir, "lockfile"),
        ]
        for lf in lock_files:
            if os.path.exists(lf):
                return (
                    True,
                    f"Chrome profile is locked — '{os.path.basename(lf)}' exists at "
                    f"'{profile_dir}'. Close all Chrome windows using this profile "
                    "or select a separate automation profile."
                )

        # Heuristic 2 — running Chrome process that references the profile path
        try:
            import psutil
            profile_lower = profile_dir.lower().replace("\\", "/")
            for proc in psutil.process_iter(["name", "cmdline"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if "chrome" not in name and "chromium" not in name:
                        continue
                    cmdline = " ".join(proc.info.get("cmdline") or []).lower().replace("\\", "/")
                    if profile_lower in cmdline:
                        return (
                            True,
                            f"Chrome is already running with profile '{profile_dir}' "
                            f"(PID {proc.pid}). Close Chrome or choose a different "
                            "automation profile path in Browser Settings."
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            log.warning("psutil not available — skipping running-process profile lock check")

        return False, ""

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "browser_executable_path": self.browser_executable_path or "",
            "profile_path": self.profile_path or "",
            "keep_open": self.keep_open,
            "debug_logging": self.debug_logging,
            "headless": self.headless,
            "slow_mo": self.slow_mo,
            # Derived / computed fields surfaced to the UI
            "effective_profile_path": self.effective_profile_path,
            "is_development": self.is_development,
            "effective_headless": self.effective_headless,
            "effective_keep_open": self.effective_keep_open,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BrowserConfig":
        return cls(
            mode=data.get("mode", "production"),
            browser_executable_path=data.get("browser_executable_path") or None,
            profile_path=data.get("profile_path") or None,
            keep_open=bool(data.get("keep_open", False)),
            debug_logging=bool(data.get("debug_logging", False)),
            headless=bool(data.get("headless", False)),
            slow_mo=int(data.get("slow_mo", 1200)),
        )


# ── In-process settings store ─────────────────────────────────────────────────
# A simple dict persisted in the server process lifetime.
# For multi-process or multi-user production deployments this should be
# moved to the database; for a single-user local prototype this is sufficient.

_SETTINGS_STORE: dict[str, BrowserConfig] = {}
_GLOBAL_KEY = "__global__"


def get_browser_config(user_id: str | None = None) -> BrowserConfig:
    """
    Return the BrowserConfig for the given user, falling back to the
    global (process-level) config if none has been saved yet.
    """
    key = user_id or _GLOBAL_KEY
    return _SETTINGS_STORE.get(key, BrowserConfig())


def save_browser_config(config: BrowserConfig, user_id: str | None = None) -> None:
    """Persist a BrowserConfig for the given user in the process store."""
    key = user_id or _GLOBAL_KEY
    _SETTINGS_STORE[key] = config
    log.info(
        f"Browser config updated for user={key!r}: "
        f"mode={config.mode!r}, profile={config.effective_profile_path!r}"
    )
