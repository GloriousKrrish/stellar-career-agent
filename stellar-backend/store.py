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
    for q in list(_ws_queues.get(run_id, [])):
        await q.put(event)


# ─── Agent status ─────────────────────────────────────────────────────────────

def update_agent_status(status: AgentStatus) -> None:
    _agent_statuses[status.agent_id] = status


def get_all_agent_statuses() -> list[AgentStatus]:
    return list(_agent_statuses.values())
