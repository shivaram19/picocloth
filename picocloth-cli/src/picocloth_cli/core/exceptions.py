"""
Custom exception hierarchy for PicoCloth-CLI.

A well-structured exception tree enables precise error handling, clean
user-facing messages, and detailed debugging. Each layer of the CLI
(fleet, intent, memory, agent) defines its own exceptions inheriting
from the base PicoClothError.

Citation: Microsoft Agent Framework 1.0 middleware hooks pattern
"""

from pathlib import Path


class PicoClothError(Exception):
    """Base exception for all PicoCloth-CLI errors."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# Fleet layer errors
# ---------------------------------------------------------------------------


class FleetError(PicoClothError):
    """Errors related to fleet communication or node management."""


class NodeNotFoundError(FleetError):
    """Requested node does not exist in the fleet registry."""


class NodeOfflineError(FleetError):
    """Requested node is registered but not responding."""


class MCPConnectionError(FleetError):
    """Failed to establish MCP transport connection."""


class TaskQueueError(FleetError):
    """Failed to read from or write to the shared task queue."""


# ---------------------------------------------------------------------------
# Intent layer errors
# ---------------------------------------------------------------------------


class IntentError(PicoClothError):
    """Errors related to intent classification or resolution."""


class IntentClassificationError(IntentError):
    """Failed to classify user input into a known intent."""


class IntentResolutionError(IntentError):
    """Classified intent could not be resolved to an executable action."""


class LowConfidenceError(IntentError):
    """Intent classification confidence fell below the threshold."""

    def __init__(
        self,
        message: str,
        *,
        confidence: float,
        threshold: float,
        candidates: list[dict] | None = None,
    ) -> None:
        super().__init__(message)
        self.confidence = confidence
        self.threshold = threshold
        self.candidates = candidates or []


# ---------------------------------------------------------------------------
# Agent layer errors
# ---------------------------------------------------------------------------


class AgentError(PicoClothError):
    """Errors related to agent spawning, execution, or registry."""


class SpawnDepthExceededError(AgentError):
    """Maximum spawn depth reached; cannot create further child agents."""

    def __init__(self, message: str, *, current_depth: int, max_depth: int) -> None:
        super().__init__(message)
        self.current_depth = current_depth
        self.max_depth = max_depth


class AgentRegistryError(AgentError):
    """Failed to read from or write to the agent registry."""


class MemorySliceError(AgentError):
    """Failed to construct a memory slice for agent spawning."""


# ---------------------------------------------------------------------------
# Memory layer errors
# ---------------------------------------------------------------------------


class MemoryError(PicoClothError):
    """Errors related to shared memory access or compaction."""


class MemoryLayerError(MemoryError):
    """Invalid memory layer specified or layer inaccessible."""


class LockFileError(MemoryError):
    """Failed to acquire or release a lock file for atomic memory access."""

    def __init__(self, message: str, *, lock_path: Path, timeout: float) -> None:
        super().__init__(message)
        self.lock_path = lock_path
        self.timeout = timeout


class CompactionError(MemoryError):
    """Error during the graduated compaction pipeline."""


class SchemaValidationError(MemoryError):
    """Memory data did not match the expected Pydantic schema."""


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class ConfigError(PicoClothError):
    """Errors related to CLI configuration loading or validation."""
