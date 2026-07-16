"""
In-memory store for workflow states and active WebSocket connections.
In production, swap this for Redis / PostgreSQL.
"""
import asyncio
from typing import Any
from collections import defaultdict
from models import WorkflowState, AgentStatus

# Run ID → WorkflowState
_workflow_store: dict[str, WorkflowState] = {}

# Run ID → list of queues (one per WebSocket subscriber)
_ws_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

# Run ID → list of published events
_event_history: dict[str, list[dict[str, Any]]] = defaultdict(list)

# Agent name → AgentStatus
_agent_statuses: dict[str, AgentStatus] = {}


# ─── Workflow ─────────────────────────────────────────────────────────────────

import db

def save_workflow(state: WorkflowState) -> None:
    db.db_save_workflow(state)


def get_workflow(run_id: str) -> WorkflowState | None:
    return db.db_get_workflow(run_id)


def all_workflows() -> list[WorkflowState]:
    return db.db_all_workflows()


# ─── WebSocket pub/sub ────────────────────────────────────────────────────────

# Store the main loop reference for thread-safe websocket events
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def subscribe(run_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _ws_queues[run_id].append(q)
    return q


def unsubscribe(run_id: str, q: asyncio.Queue) -> None:
    try:
        _ws_queues[run_id].remove(q)
    except ValueError:
        pass


def get_event_history(run_id: str) -> list[dict[str, Any]]:
    return _event_history[run_id]


async def publish(run_id: str, event: dict[str, Any]) -> None:
    _event_history[run_id].append(event)
    
    current_loop = None
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        pass

    if _main_loop and _main_loop.is_running() and current_loop != _main_loop:
        def put_in_queue():
            for q in list(_ws_queues.get(run_id, [])):
                q.put_nowait(event)
        _main_loop.call_soon_threadsafe(put_in_queue)
    else:
        for q in list(_ws_queues.get(run_id, [])):
            await q.put(event)


# ─── Agent status ─────────────────────────────────────────────────────────────

def update_agent_status(status: AgentStatus) -> None:
    _agent_statuses[status.agent_id] = status


def get_all_agent_statuses() -> list[AgentStatus]:
    return list(_agent_statuses.values())


# ─── Debug Sessions ───────────────────────────────────────────────────────────

_finished_debug_sessions: set[str] = set()

def finish_debug_session(task_id: str) -> None:
    _finished_debug_sessions.add(task_id)

def is_debug_session_finished(task_id: str) -> bool:
    return task_id in _finished_debug_sessions


# ─── HITL (Human-in-the-Loop) Automation Signals ─────────────────────────────
# When the engine detects a login gate, CAPTCHA, OTP, etc., it pauses and waits
# for the user to complete the required action.  The frontend sends a signal
# (continue / cancel) which is picked up by the polling loop inside the engine.

from dataclasses import dataclass, field as dc_field
from datetime import datetime as _datetime


@dataclass
class HITLPauseState:
    """Tracks a single paused automation task awaiting user intervention."""
    task_id: str
    reason: str                       # e.g. "Login required", "CAPTCHA detected"
    platform: str                     # e.g. "naukri", "linkedin"
    current_url: str
    screenshot_path: str
    paused_at: str                    # ISO timestamp
    signal: str = "waiting"           # "waiting" | "continue" | "cancel" | "save_session"


# task_id → HITLPauseState
_hitl_pauses: dict[str, HITLPauseState] = {}


def hitl_pause(
    task_id: str,
    reason: str,
    platform: str,
    current_url: str,
    screenshot_path: str,
) -> HITLPauseState:
    """Register a new HITL pause for the given task."""
    from datetime import timezone
    state = HITLPauseState(
        task_id=task_id,
        reason=reason,
        platform=platform,
        current_url=current_url,
        screenshot_path=screenshot_path,
        paused_at=_datetime.now(timezone.utc).isoformat(),
    )
    _hitl_pauses[task_id] = state
    return state


def hitl_signal(task_id: str, signal: str) -> bool:
    """
    Send a signal to a paused task.
    signal: "continue" | "cancel" | "save_session"
    Returns True if the task was found and signalled.
    """
    if task_id in _hitl_pauses:
        _hitl_pauses[task_id].signal = signal
        return True
    return False


def hitl_get_signal(task_id: str) -> str:
    """Read the current signal for a paused task. Returns 'waiting' if no signal yet."""
    if task_id in _hitl_pauses:
        return _hitl_pauses[task_id].signal
    return "waiting"


def hitl_get_pause(task_id: str) -> Optional[HITLPauseState]:
    """Get the pause state for a task, or None."""
    return _hitl_pauses.get(task_id)


def hitl_clear(task_id: str) -> None:
    """Remove the HITL pause state for a task (after resume or cancel)."""
    _hitl_pauses.pop(task_id, None)


def hitl_get_all_pauses() -> list[HITLPauseState]:
    """Return all currently paused tasks."""
    return list(_hitl_pauses.values())

