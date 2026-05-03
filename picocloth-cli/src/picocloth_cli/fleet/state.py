"""
Fleet state reader/writer.

Provides typed access to shared/state/fleet-state.json and shared/state/task-queue.json
with lock-file coordination for safe concurrent access.

Citation: Claude Code file-lock pattern (Anthropic, Feb 2026)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import STATE_DIR
from picocloth_cli.core.exceptions import FleetError, TaskQueueError
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import atomic_write_json, lock_file, read_json_safe

logger = get_logger(__name__)

FLEET_STATE_PATH = STATE_DIR / "fleet-state.json"
TASK_QUEUE_PATH = STATE_DIR / "task-queue.json"


def get_fleet_state() -> dict[str, Any]:
    """Read the current fleet state from shared memory.

    Returns:
        A dict with keys: nodes, last_updated, version
    """
    default = {
        "nodes": {},
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
    }
    return read_json_safe(FLEET_STATE_PATH, default=default)


def save_fleet_state(state: dict[str, Any]) -> None:
    """Write fleet state atomically with lock protection."""
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    with lock_file(FLEET_STATE_PATH):
        atomic_write_json(FLEET_STATE_PATH, state)


def get_node_status(node_id: str) -> dict[str, Any] | None:
    """Get status for a single node, or None if not registered."""
    state = get_fleet_state()
    return state.get("nodes", {}).get(node_id)


def get_task_queue() -> list[dict[str, Any]]:
    """Read the current task queue.

    Returns:
        List of task dicts with keys: id, target_node, task, priority, status, created_at, result
    """
    return read_json_safe(TASK_QUEUE_PATH, default=[])


def save_task_queue(queue: list[dict[str, Any]]) -> None:
    """Write task queue atomically with lock protection."""
    with lock_file(TASK_QUEUE_PATH):
        atomic_write_json(TASK_QUEUE_PATH, queue)


def append_task(
    target_node: str,
    task: str,
    priority: str = "normal",
    sender: str = "picocloth-cli",
) -> dict[str, Any]:
    """Append a new task to the shared task queue.

    Returns:
        The created task dict.
    """
    task_id = f"task-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{hash(task) % 10000:04d}"
    entry = {
        "id": task_id,
        "target_node": target_node,
        "task": task,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sender": sender,
        "result": None,
    }

    with lock_file(TASK_QUEUE_PATH):
        queue = get_task_queue()
        queue.append(entry)
        atomic_write_json(TASK_QUEUE_PATH, queue)

    logger.info("Task appended to queue", extra={"task_id": task_id, "target": target_node})
    return entry


def update_task_status(task_id: str, status: str, result: Any = None) -> dict[str, Any] | None:
    """Update the status of a task in the queue.

    Returns:
        The updated task dict, or None if not found.
    """
    with lock_file(TASK_QUEUE_PATH):
        queue = get_task_queue()
        for task in queue:
            if task.get("id") == task_id:
                task["status"] = status
                if result is not None:
                    task["result"] = result
                task["updated_at"] = datetime.now(timezone.utc).isoformat()
                atomic_write_json(TASK_QUEUE_PATH, queue)
                logger.info("Task status updated", extra={"task_id": task_id, "status": status})
                return task
    return None


def get_pending_tasks() -> list[dict[str, Any]]:
    """Return all tasks with status 'pending'."""
    return [t for t in get_task_queue() if t.get("status") == "pending"]


def get_running_tasks() -> list[dict[str, Any]]:
    """Return all tasks with status 'running'."""
    return [t for t in get_task_queue() if t.get("status") == "running"]


def get_completed_tasks(limit: int = 10) -> list[dict[str, Any]]:
    """Return the most recent completed tasks."""
    completed = [t for t in get_task_queue() if t.get("status") == "completed"]
    return completed[-limit:] if limit > 0 else completed
