"""
State layer CRUD — operational truth: fleet registry, task queue, credentials.

Real-time updates with lock-file coordination. This is the "nervous system"
of the PicoCloth fleet.

Citation: Graph Digital 4-layer memory — State as Nervous System
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from picocloth_cli.core.constants import STATE_DIR
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import atomic_write_json, lock_file, read_json_safe

logger = get_logger(__name__)


def read_state(key: str) -> Any:
    """Read a state file by key."""
    path = STATE_DIR / f"{key}.json"
    return read_json_safe(path, default=None)


def write_state(key: str, data: Any) -> None:
    """Write a state file atomically with lock protection."""
    path = STATE_DIR / f"{key}.json"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with lock_file(path):
        atomic_write_json(path, data)
    logger.debug("State written", extra={"key": key})


def update_fleet_node(node_id: str, info: dict[str, Any]) -> None:
    """Update a single node's entry in fleet-state.json."""
    from picocloth_cli.fleet.state import get_fleet_state, save_fleet_state

    state = get_fleet_state()
    state["nodes"][node_id] = {
        **info,
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
    }
    save_fleet_state(state)
