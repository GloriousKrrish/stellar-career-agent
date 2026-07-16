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
