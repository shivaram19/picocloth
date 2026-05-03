"""
Runtime agent spawner for PicoCloth-CLI.

Handles the full lifecycle of dynamic agent creation:
1. Determine target node based on intent + complexity
2. Build memory slice from parent context
3. Create spawn package in node's workspace
4. Write task to shared task queue with lock-file coordination
5. Monitor task completion via polling
6. Return summary-only result to parent

Spawn depth limit: 3 levels (parent → child → grandchild)

Citations:
- AgentSpawn runtime spawning (arXiv:2602.07072v1)
- Claude Code summary-only return (Anthropic, Feb 2026)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picocloth_cli.agent.memory_slice import build_memory_slice
from picocloth_cli.agent.package import ExecutionContext, MemorySlice, SpawnPackage, TaskSpec
from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import MAX_SPAWN_DEPTH, NODE_ROLES, NODES, STATE_DIR
from picocloth_cli.core.exceptions import AgentError, SpawnDepthExceededError
from picocloth_cli.core.logging import get_logger
from picocloth_cli.fleet.state import append_task, get_task_queue, update_task_status
from picocloth_cli.intent.classifier import Intent
from picocloth_cli.intent.complexity import ComplexityMetrics
from picocloth_cli.utils.files import atomic_write_json

logger = get_logger(__name__)


def select_target_node(intent: Intent) -> str:
    """Select the optimal node for a given intent based on role matching.

    Mapping derived from PicoCloth node role definitions:
    - node-a: Curiosity Brain (research, analysis)
    - node-b: Executor Builder (code, deployment)
    - node-c: Memory Guardian (archival, knowledge graph)
    - node-d: Safety Auditor (validation, budget)
    - node-e: Document Parser (PDF, spec extraction)
    - node-f: Contradiction Detector (mismatch finding)
    - node-g: RFI Drafter (professional writing)
    - node-h: Knowledge Graph Builder (entity extraction)
    - node-i: Fleet Router (classification, load balancing)
    - node-j: Metrics Collector (tracking, alerts)
    """
    from picocloth_cli.intent.classifier import IntentType

    mapping = {
        IntentType.ORCHESTRATE: "node-i",
        IntentType.DELEGATE: "node-b",
        IntentType.QUERY: "node-c",
        IntentType.CHAT: "node-a",
        IntentType.BUILD: "node-b",
        IntentType.ANALYZE: "node-a",
    }

    # Check for explicit node references in intent parameters
    explicit = intent.parameters.get("target_node")
    if explicit and explicit in NODES:
        return explicit

    # Check for keyword-based routing
    text = intent.raw_input.lower()
    if any(kw in text for kw in ["contradiction", "mismatch", "compare", "spec"]):
        return "node-f"
    if any(kw in text for kw in ["pdf", "document", "parse", "extract text"]):
        return "node-e"
    if any(kw in text for kw in ["rfi", "draft", "professional", "formal"]):
        return "node-g"
    if any(kw in text for kw in ["entity", "relationship", "knowledge graph", "graph"]):
        return "node-h"
    if any(kw in text for kw in ["metric", "token", "cost", "latency", "track"]):
        return "node-j"
    if any(kw in text for kw in ["safety", "budget", "validate", "audit"]):
        return "node-d"

    return mapping.get(intent.intent_type, "node-a")


def spawn_agent(
    intent: Intent,
    complexity: ComplexityMetrics,
    parent_id: str | None = None,
    current_depth: int = 0,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Spawn a new agent dynamically based on intent and complexity.

    Args:
        intent: Classified user intent.
        complexity: Complexity metrics that triggered spawning.
        parent_id: Parent agent ID (None for root-level spawning).
        current_depth: Current spawn depth level.
        session_id: Active CLI session ID for memory continuity.

    Returns:
        Dict with spawn_id, task_id, target_node, and status.

    Raises:
        SpawnDepthExceededError: If max depth would be exceeded.
    """
    if current_depth >= MAX_SPAWN_DEPTH:
        raise SpawnDepthExceededError(
            f"Cannot spawn: maximum depth {MAX_SPAWN_DEPTH} reached.",
            current_depth=current_depth,
            max_depth=MAX_SPAWN_DEPTH,
        )

    target = select_target_node(intent)
    spawn_id = f"agent-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{hash(intent.raw_input) % 10000:04d}"

    # Build memory slice
    slice_data = build_memory_slice(intent, session_id=session_id)
    memory_slice = MemorySlice(
        episodic=slice_data["episodic"],
        semantic=slice_data["semantic"],
        working=slice_data["working"],
    )

    # Create spawn package
    package = SpawnPackage(
        spawn_id=spawn_id,
        parent_id=parent_id,
        node=target,
        intent_type=intent.intent_type.value,
        raw_input=intent.raw_input,
        memory_slice=memory_slice,
        skills=[],  # TODO: load relevant skills from doctrine/
        execution_context=ExecutionContext(
            cwd=str(Path(f"node-{target[-1]}") / "workspace" / "agents"),
        ),
        task_spec=TaskSpec(
            goal=intent.parameters.get("task", intent.raw_input),
            priority="high" if complexity.overall > 0.8 else "normal",
        ),
        complexity=complexity.__dict__,
    )

    # Save package to node's workspace
    workspace = Path(f"node-{target[-1]}") / "workspace" / "agents"
    workspace.mkdir(parents=True, exist_ok=True)
    package_path = workspace / f"{spawn_id}.json"
    package.save(package_path)

    # Append to shared task queue
    task = append_task(
        target_node=target,
        task=f"[AGENT:{spawn_id}] {package.task_spec.goal}",
        priority=package.task_spec.priority,
        sender="picocloth-cli",
    )

    logger.info("Agent spawned", extra={
        "spawn_id": spawn_id,
        "task_id": task["id"],
        "target": target,
        "depth": current_depth + 1,
        "complexity": complexity.overall,
    })

    return {
        "spawn_id": spawn_id,
        "task_id": task["id"],
        "target_node": target,
        "depth": current_depth + 1,
        "package_path": str(package_path),
        "status": "spawning",
    }


async def poll_task_completion(
    task_id: str,
    *,
    interval: float = 2.0,
    timeout: float = 300.0,
) -> dict[str, Any] | None:
    """Poll the task queue until a task completes or times out.

    Returns:
        The completed task dict, or None on timeout.
    """
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        queue = get_task_queue()
        for task in queue:
            if task.get("id") == task_id:
                status = task.get("status")
                if status in ("completed", "failed", "cancelled"):
                    return task
        await asyncio.sleep(interval)

    logger.warning("Task polling timed out", extra={"task_id": task_id})
    return None


def get_spawn_summary(spawn_id: str) -> str:
    """Generate a summary-only result for a completed spawn.

    This prevents the 7× token inflation that occurs when subagents
    return full transcripts to their parents.
    """
    # TODO: In production, this would query Langfuse or the node gateway
    # for a structured summary of the agent's work.
    return f"Agent {spawn_id} completed. See node workspace for full output."
