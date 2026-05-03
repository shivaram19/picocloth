"""
Agent registry for tracking spawned agents across the fleet.

Maintains shared/state/agent-registry.json with:
- Active agents: PID, node assignment, spawn depth, status
- Completed agents: result summaries, completion time
- Failed agents: error traces, failure reason

Citation: Microsoft Agent Framework 1.0 checkpointing/hydration pattern
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picocloth_cli.core.constants import STATE_DIR
from picocloth_cli.core.exceptions import AgentRegistryError
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import atomic_write_json, lock_file, read_json_safe

logger = get_logger(__name__)

AGENT_REGISTRY_PATH = STATE_DIR / "agent-registry.json"


def _load_registry() -> dict[str, Any]:
    """Load the agent registry from shared state."""
    return read_json_safe(AGENT_REGISTRY_PATH, default={
        "agents": [],
        "version": "1.0",
        "last_updated": datetime.now(timezone.utc).isoformat(),
    })


def _save_registry(registry: dict[str, Any]) -> None:
    """Save the agent registry atomically with lock protection."""
    registry["last_updated"] = datetime.now(timezone.utc).isoformat()
    with lock_file(AGENT_REGISTRY_PATH):
        atomic_write_json(AGENT_REGISTRY_PATH, registry)


def register_agent(
    agent_id: str,
    node: str,
    goal: str,
    *,
    parent_id: str | None = None,
    spawn_depth: int = 0,
    status: str = "spawning",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Register a new agent in the fleet registry.

    Returns:
        The created agent entry dict.
    """
    registry = _load_registry()

    entry = {
        "id": agent_id,
        "node": node,
        "goal": goal,
        "parent_id": parent_id,
        "spawn_depth": spawn_depth,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }

    registry["agents"].append(entry)
    _save_registry(registry)

    logger.info("Agent registered", extra={
        "agent_id": agent_id,
        "node": node,
        "depth": spawn_depth,
    })
    return entry


def update_agent_status(
    agent_id: str,
    status: str,
    *,
    result: Any = None,
    error: str | None = None,
) -> dict[str, Any] | None:
    """Update the status of a registered agent.

    Returns:
        The updated entry, or None if not found.
    """
    registry = _load_registry()
    for agent in registry.get("agents", []):
        if agent.get("id") == agent_id:
            agent["status"] = status
            agent["updated_at"] = datetime.now(timezone.utc).isoformat()
            if result is not None:
                agent["result"] = result
            if error is not None:
                agent["error"] = error
            _save_registry(registry)
            logger.info("Agent status updated", extra={"agent_id": agent_id, "status": status})
            return agent
    return None


def get_agent(agent_id: str) -> dict[str, Any] | None:
    """Get a single agent entry by ID."""
    registry = _load_registry()
    for agent in registry.get("agents", []):
        if agent.get("id") == agent_id:
            return agent
    return None


def list_agents(
    *,
    status_filter: str | None = None,
    node_filter: str | None = None,
    parent_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List agents with optional filtering."""
    registry = _load_registry()
    agents = registry.get("agents", [])

    if status_filter:
        agents = [a for a in agents if a.get("status") == status_filter]
    if node_filter:
        agents = [a for a in agents if a.get("node") == node_filter]
    if parent_id is not None:
        agents = [a for a in agents if a.get("parent_id") == parent_id]

    return agents[-limit:]


def get_active_agents() -> list[dict[str, Any]]:
    """Return all agents with status 'spawning' or 'running'."""
    return list_agents(status_filter="spawning") + list_agents(status_filter="running")


def get_agent_tree(agent_id: str) -> dict[str, Any]:
    """Build a tree representation of an agent and its descendants."""
    root = get_agent(agent_id)
    if root is None:
        return {}

    def build_tree(parent_id: str) -> list[dict[str, Any]]:
        children = list_agents(parent_id=parent_id)
        return [
            {
                **child,
                "children": build_tree(child["id"]),
            }
            for child in children
        ]

    return {
        **root,
        "children": build_tree(agent_id),
    }
