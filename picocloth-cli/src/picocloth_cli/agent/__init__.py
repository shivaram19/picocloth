"""Agent spawning and lifecycle management."""

from picocloth_cli.agent.memory_slice import build_memory_slice
from picocloth_cli.agent.package import (
    ExecutionContext,
    MemorySlice,
    SpawnPackage,
    TaskSpec,
)
from picocloth_cli.agent.registry import (
    get_active_agents,
    get_agent,
    get_agent_tree,
    list_agents,
    register_agent,
    update_agent_status,
)
from picocloth_cli.agent.spawner import (
    get_spawn_summary,
    poll_task_completion,
    select_target_node,
    spawn_agent,
)

__all__ = [
    # Package
    "SpawnPackage",
    "TaskSpec",
    "MemorySlice",
    "ExecutionContext",
    # Memory Slice
    "build_memory_slice",
    # Spawner
    "spawn_agent",
    "select_target_node",
    "poll_task_completion",
    "get_spawn_summary",
    # Registry
    "register_agent",
    "update_agent_status",
    "get_agent",
    "list_agents",
    "get_active_agents",
    "get_agent_tree",
]
