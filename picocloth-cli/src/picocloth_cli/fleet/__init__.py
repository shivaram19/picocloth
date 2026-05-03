"""Fleet communication layer: MCP client, state management, launcher."""

from picocloth_cli.fleet.client import MCPFleetClient, MCPResult
from picocloth_cli.fleet.launcher import (
    async_launch_fleet,
    async_stop_fleet,
    get_fleet_status,
    launch_fleet,
    stop_fleet,
)
from picocloth_cli.fleet.state import (
    append_task,
    get_completed_tasks,
    get_fleet_state,
    get_node_status,
    get_pending_tasks,
    get_running_tasks,
    get_task_queue,
    save_fleet_state,
    save_task_queue,
    update_task_status,
)

__all__ = [
    # Client
    "MCPFleetClient",
    "MCPResult",
    # Launcher
    "launch_fleet",
    "stop_fleet",
    "get_fleet_status",
    "async_launch_fleet",
    "async_stop_fleet",
    # State
    "get_fleet_state",
    "save_fleet_state",
    "get_node_status",
    "get_task_queue",
    "save_task_queue",
    "append_task",
    "update_task_status",
    "get_pending_tasks",
    "get_running_tasks",
    "get_completed_tasks",
]
