"""
Spawn/Resume Package Specification.

Structured snapshot following the AgentSpawn paper's spawn package spec.
Each package contains everything needed for an agent to resume work:
identity, memory slice, skills, execution context, and task specification.

Citation: AgentSpawn "Spawn Package Spec" (arXiv:2602.07072v1, Section 5.1)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from picocloth_cli.intent.classifier import Intent
from picocloth_cli.intent.complexity import ComplexityMetrics


class TaskSpec(BaseModel):
    """Specification of a task to be executed by a spawned agent."""

    goal: str = Field(..., description="High-level goal statement")
    constraints: list[str] = Field(default_factory=list, description="Hard constraints")
    success_criteria: list[str] = Field(default_factory=list, description="Completion criteria")
    deadline: str | None = Field(None, description="Optional ISO deadline")
    priority: str = Field("normal", description="low | normal | high | critical")


class MemorySlice(BaseModel):
    """Selective memory transfer from parent to child agent.

    Citation: AgentSpawn Memory Slicing Algorithm (arXiv:2602.07072v1, Section 5.2)
    """

    episodic: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Recent conversation turns (last N)",
    )
    semantic: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Relevant facts from project/ memory",
    )
    working: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Active tool calls, in-flight subagents",
    )


class ExecutionContext(BaseModel):
    """Runtime environment for the spawned agent."""

    cwd: str = Field(..., description="Working directory")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    allowed_tools: list[str] = Field(default_factory=list, description="Tool whitelist")
    forbidden_paths: list[str] = Field(default_factory=list, description="Path blacklist")


class SpawnPackage(BaseModel):
    """Complete spawn package for runtime agent creation.

    This is the primary data structure used when dynamically spawning agents
    in the PicoCloth fleet. It ensures memory continuity and skill inheritance
    across spawn boundaries.
    """

    spawn_id: str = Field(default_factory=lambda: f"spawn-{uuid.uuid4().hex[:12]}")
    parent_id: str | None = Field(None, description="Parent agent ID (None for root)")
    node: str = Field(..., description="Target node ID, e.g., node-b")

    intent_type: str = Field(..., description="Classified intent type")
    raw_input: str = Field(..., description="Original user input")

    memory_slice: MemorySlice = Field(default_factory=MemorySlice)
    skills: list[str] = Field(default_factory=list, description="Doctrine skill IDs to load")
    execution_context: ExecutionContext = Field(default_factory=lambda: ExecutionContext(cwd="/tmp"))
    task_spec: TaskSpec = Field(default_factory=lambda: TaskSpec(goal=""))
    complexity: dict[str, float] = Field(default_factory=dict, description="Complexity metrics that triggered spawn")

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = Field("1.0", description="Spawn package schema version")

    @classmethod
    def from_intent(
        cls,
        intent: Intent,
        complexity: ComplexityMetrics,
        node: str,
        parent_id: str | None = None,
    ) -> SpawnPackage:
        """Factory method to create a spawn package from a classified intent."""
        return cls(
            parent_id=parent_id,
            node=node,
            intent_type=intent.intent_type.value,
            raw_input=intent.raw_input,
            task_spec=TaskSpec(
                goal=intent.parameters.get("task", intent.raw_input),
                priority="normal",
            ),
            complexity=complexity.__dict__,
        )

    def save(self, path: Path) -> None:
        """Serialize the spawn package to disk atomically."""
        from picocloth_cli.utils.files import atomic_write_json
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, self.model_dump(mode="json"))

    @classmethod
    def load(cls, path: Path) -> SpawnPackage:
        """Deserialize a spawn package from disk."""
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
