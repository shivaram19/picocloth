"""
Constants and path definitions for PicoCloth-CLI.

All paths are resolved relative to the PICOLOTH_DIR environment variable,
falling back to the project root discovered from the current file location.
This ensures the CLI works regardless of where it is invoked from.

Citation: Claude Code file-based memory hierarchy (arXiv:2604.14228v1)
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root discovery
# ---------------------------------------------------------------------------
# The CLI may be installed as a package (pip install -e) or run from source.
# We resolve PICOLOTH_DIR in this priority order:
#   1. PICOLOTH_DIR environment variable (explicit override)
#   2. Auto-discovered from this file's location (../../.. from picocloth-cli/src/)
# ---------------------------------------------------------------------------

_ENV_PICOCLOTH_DIR = os.environ.get("PICOLOTH_DIR")
if _ENV_PICOCLOTH_DIR:
    PICOCLOTH_DIR = Path(_ENV_PICOCLOTH_DIR).resolve()
else:
    # This file lives at: picocloth/picocloth-cli/src/picocloth_cli/core/constants.py
    # Going up 5 levels reaches the picocloth project root
    PICOCLOTH_DIR = Path(__file__).resolve().parents[4]

# ---------------------------------------------------------------------------
# Shared memory architecture — 4-layer design
# Citation: Graph Digital's Katelyn Skills OS; Hu et al. 2025 context/memory separation
# ---------------------------------------------------------------------------
SHARED_DIR = PICOCLOTH_DIR / "shared"
DOCTRINE_DIR = SHARED_DIR / "doctrine"
PROJECT_DIR = SHARED_DIR / "project"
STATE_DIR = SHARED_DIR / "state"
RUN_DIR = SHARED_DIR / "run"
DIGITAL_TWINS_DIR = SHARED_DIR / "digital-twins"
COMPACTION_ARCHIVE_DIR = SHARED_DIR / "compaction-archive"

# ---------------------------------------------------------------------------
# Node configuration
# Citation: AgentSpawn adaptive spawning (arXiv:2602.07072v1)
# ---------------------------------------------------------------------------
NODES = [f"node-{c}" for c in "abcdefghij"]
NODE_PORTS = [18790 + i for i in range(10)]
NODE_ROLES = {
    "node-a": "curiosity_brain",
    "node-b": "executor_builder",
    "node-c": "memory_guardian",
    "node-d": "safety_auditor",
    "node-e": "document_parser",
    "node-f": "contradiction_detector",
    "node-g": "rfi_drafter",
    "node-h": "knowledge_graph_builder",
    "node-i": "fleet_router",
    "node-j": "metrics_collector",
}

# ---------------------------------------------------------------------------
# Fleet server
# Citation: MCP Protocol Spec (modelcontextprotocol.io)
# ---------------------------------------------------------------------------
FLEET_SERVER_PATH = PICOCLOTH_DIR / "mcp-fleet-server" / "server.py"
FLEET_SHARED_DIR = SHARED_DIR

# ---------------------------------------------------------------------------
# User-local CLI directories
# Citation: OpenHands V1 SDK workspace isolation (arXiv:2511.03690v1)
# ---------------------------------------------------------------------------
PICOCLOTH_HOME = Path.home() / ".picocloth"
CLI_CONFIG_PATH = PICOCLOTH_HOME / "config.yaml"
CLI_SESSIONS_DIR = PICOCLOTH_HOME / "sessions"
CLI_LOGS_DIR = PICOCLOTH_HOME / "logs"
CLI_CACHE_DIR = PICOCLOTH_HOME / "cache"

# ---------------------------------------------------------------------------
# Runtime directories for CLI sessions
# Citation: Claude Code sidechain transcript design (arXiv:2604.14228v1)
# ---------------------------------------------------------------------------
CLI_RUN_DIR = RUN_DIR / "picocloth-cli"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_CONTEXT_WINDOW = 32768
DEFAULT_MAX_TOKENS = 2048
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_HEARTBEAT_INTERVAL = 30

# Intent classification confidence threshold
# Below this, we ask the user for clarification.
# Citation: Anthropic "Building Effective Agents" — routing pattern
INTENT_CONFIDENCE_THRESHOLD = 0.7

# Complexity threshold for adaptive spawning
# Above this, a new agent is spawned dynamically.
# Citation: AgentSpawn runtime spawning triggers (arXiv:2602.07072v1)
SPAWN_COMPLEXITY_THRESHOLD = 0.65

# Maximum spawn depth to prevent coordination overhead
# Citation: AgentSpawn Section 5.3 — coordination overhead analysis
MAX_SPAWN_DEPTH = 3

# Compaction trigger: context usage percentage
# Citation: PicoCloth default (matches digital twin guardian hook)
COMPACTION_THRESHOLD_PERCENT = 75
