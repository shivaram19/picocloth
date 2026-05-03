"""
Intent resolution engine.

The central router that takes a classified Intent, evaluates its complexity,
and decides whether to execute a static command or dynamically spawn an agent.

Pipeline:
    User Input → Classifier → Intent + Confidence
                          ↓
                   Complexity Evaluator → Score
                          ↓
                   Router → Static Command OR Dynamic Spawn
                          ↓
                   Executor → Fleet client call OR Agent spawn

Citation: Task-Adaptive Multi-Agent Orchestration (arXiv:2602.16873)
Citation: Anthropic "Building Effective Agents" — orchestrator-workers pattern
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import MAX_SPAWN_DEPTH, NODE_ROLES, NODES
from picocloth_cli.core.exceptions import (
    FleetError,
    IntentError,
    IntentResolutionError,
    LowConfidenceError,
    SpawnDepthExceededError,
)
from picocloth_cli.core.logging import get_logger
from picocloth_cli.fleet.client import MCPFleetClient
from picocloth_cli.fleet.state import append_task
from picocloth_cli.intent.classifier import Intent, IntentType, classify_intent
from picocloth_cli.intent.complexity import ComplexityMetrics, evaluate_complexity

logger = get_logger(__name__)


@dataclass
class ResolutionResult:
    """Result of intent resolution."""

    success: bool
    action: str
    target_node: str | None
    message: str
    details: dict[str, Any]


class IntentEngine:
    """Central intent resolution engine for PicoCloth-CLI.

    Routes user intents to appropriate fleet actions based on classification
    and complexity analysis.
    """

    def __init__(self, default_node: str = "node-a", current_depth: int = 0) -> None:
        if default_node not in NODES:
            raise IntentError(f"Invalid default node: {default_node}")
        self.default_node = default_node
        self.current_depth = current_depth

    def resolve(self, text: str) -> ResolutionResult:
        """Resolve a user input string into an executable action.

        Args:
            text: Raw user input.

        Returns:
            ResolutionResult with action details.

        Raises:
            LowConfidenceError: If intent confidence is below threshold.
            IntentResolutionError: If the intent cannot be mapped to an action.
        """
        # Step 1: Classify
        intent = classify_intent(text)
        cfg = get_config()

        if intent.confidence < cfg.intent.confidence_threshold:
            raise LowConfidenceError(
                f"I'm not sure what you mean (confidence: {intent.confidence:.0%}). "
                f"Could you rephrase?",
                confidence=intent.confidence,
                threshold=cfg.intent.confidence_threshold,
                candidates=[{"type": intent.intent_type.value, "confidence": intent.confidence}],
            )

        # Step 2: Evaluate complexity
        complexity = evaluate_complexity(intent)

        # Step 3: Route
        if complexity.should_spawn() and self.current_depth < cfg.intent.max_spawn_depth:
            return self._spawn_agent(intent, complexity)
        else:
            return self._execute_direct(intent, complexity)

    def _spawn_agent(self, intent: Intent, complexity: ComplexityMetrics) -> ResolutionResult:
        """Dynamically spawn an agent to handle a complex intent."""
        if self.current_depth >= MAX_SPAWN_DEPTH:
            raise SpawnDepthExceededError(
                f"Maximum spawn depth ({MAX_SPAWN_DEPTH}) reached.",
                current_depth=self.current_depth,
                max_depth=MAX_SPAWN_DEPTH,
            )

        target = intent.parameters.get("target_node") or self._select_node_for_intent(intent)
        task = intent.parameters.get("task") or intent.raw_input

        try:
            result = append_task(target, task, priority="normal", sender="picocloth-cli")
            logger.info("Agent spawned for complex intent", extra={
                "task_id": result["id"],
                "target": target,
                "complexity": complexity.overall,
            })
            return ResolutionResult(
                success=True,
                action="spawn",
                target_node=target,
                message=f"Spawned agent on {target} (complexity: {complexity.overall:.0%}). Task: {result['id']}",
                details={
                    "task_id": result["id"],
                    "complexity": complexity.__dict__,
                    "spawn_depth": self.current_depth + 1,
                },
            )
        except Exception as exc:
            raise IntentResolutionError(f"Failed to spawn agent: {exc}") from exc

    def _execute_direct(self, intent: Intent, complexity: ComplexityMetrics) -> ResolutionResult:
        """Execute a simple intent directly without spawning."""
        target = intent.parameters.get("target_node") or self.default_node

        if intent.intent_type == IntentType.ORCHESTRATE:
            return ResolutionResult(
                success=True,
                action="orchestrate",
                target_node=None,
                message="Fleet status: use 'picocloth fleet status' for details.",
                details={"complexity": complexity.__dict__},
            )

        elif intent.intent_type == IntentType.DELEGATE:
            try:
                result = append_task(target, intent.parameters.get("task", intent.raw_input))
                return ResolutionResult(
                    success=True,
                    action="delegate",
                    target_node=target,
                    message=f"Task delegated to {target}: {result['id']}",
                    details={"task_id": result["id"]},
                )
            except Exception as exc:
                raise IntentResolutionError(f"Delegation failed: {exc}") from exc

        elif intent.intent_type == IntentType.QUERY:
            return ResolutionResult(
                success=True,
                action="query",
                target_node=None,
                message=f"Query mode: searching for '{intent.parameters.get('query', '')}'",
                details={"query": intent.parameters.get("query")},
            )

        elif intent.intent_type == IntentType.BUILD:
            return ResolutionResult(
                success=True,
                action="build",
                target_node=target,
                message=f"Build mode: delegating to {target}",
                details={"task": intent.parameters.get("task")},
            )

        elif intent.intent_type == IntentType.ANALYZE:
            # Route to contradiction detector or research node
            analyze_target = "node-f" if "contradiction" in intent.raw_input.lower() else target
            return ResolutionResult(
                success=True,
                action="analyze",
                target_node=analyze_target,
                message=f"Analysis mode: delegating to {analyze_target}",
                details={"task": intent.parameters.get("task")},
            )

        elif intent.intent_type == IntentType.CHAT:
            return ResolutionResult(
                success=True,
                action="chat",
                target_node=target,
                message="Chat mode: continuing conversation.",
                details={},
            )

        else:
            raise IntentResolutionError(f"Unrecognized intent type: {intent.intent_type}")

    def _select_node_for_intent(self, intent: Intent) -> str:
        """Select the best node for a given intent based on role matching."""
        mapping = {
            IntentType.ORCHESTRATE: "node-i",      # Fleet Router
            IntentType.DELEGATE: "node-b",         # Executor Builder
            IntentType.QUERY: "node-c",            # Memory Guardian
            IntentType.BUILD: "node-b",            # Executor Builder
            IntentType.ANALYZE: "node-a",          # Curiosity Brain
            IntentType.CHAT: "node-a",             # Curiosity Brain
        }
        return mapping.get(intent.intent_type, self.default_node)


# Convenience function for one-shot resolution
async def resolve_intent(text: str, default_node: str = "node-a") -> ResolutionResult:
    """Async entry point for intent resolution."""
    engine = IntentEngine(default_node=default_node)
    # Run synchronous resolve in thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, engine.resolve, text)
