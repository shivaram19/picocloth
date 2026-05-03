"""
Digital twin snapshot creation and management.

Triggers twin creation when context usage reaches the threshold,
compresses conversation into structured JSON, and emits events
to the fleet EventBus.

Citation: PicoCloth Digital Twin Protocol (docs/ARCHITECTURE.md)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picocloth_cli.core.constants import DIGITAL_TWINS_DIR
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import atomic_write_json

logger = get_logger(__name__)


def create_twin_snapshot(
    node_id: str,
    session_key: str,
    context_usage: dict[str, Any],
    conversation: list[dict[str, Any]],
    extracted_facts: list[dict[str, Any]],
    active_subagents: list[dict[str, Any]] | None = None,
    trigger: str = "context_budget_75_percent",
) -> Path:
    """Create a digital twin snapshot before context compaction.

    Args:
        node_id: Node identifier, e.g., "node-a" or "picocloth-cli"
        session_key: Session or conversation identifier
        context_usage: Dict with used_tokens, total_tokens, used_percent
        conversation: Full conversation snapshot as list of turns
        extracted_facts: Facts extracted from the conversation
        active_subagents: Currently running subagents
        trigger: What triggered the twin creation

    Returns:
        Path to the created twin file.
    """
    twin_dir = DIGITAL_TWINS_DIR / node_id
    twin_dir.mkdir(parents=True, exist_ok=True)

    twin_id = f"{node_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    twin = {
        "twin_id": twin_id,
        "node_id": node_id,
        "session_key": session_key,
        "trigger": trigger,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context_usage": context_usage,
        "conversation_snapshot": conversation,
        "extracted_facts": extracted_facts,
        "active_subagents": active_subagents or [],
        "compaction_summary": None,  # Filled post-compaction
    }

    twin_path = twin_dir / f"{twin_id}.json"
    atomic_write_json(twin_path, twin)

    logger.info("Digital twin snapshot created", extra={
        "twin_id": twin_id,
        "node_id": node_id,
        "trigger": trigger,
        "path": str(twin_path),
    })

    return twin_path


def add_compaction_summary(twin_path: Path, summary: str) -> None:
    """Add a post-compaction summary to an existing twin snapshot."""
    if not twin_path.exists():
        logger.warning("Twin file not found for summary", extra={"path": str(twin_path)})
        return

    with open(twin_path, "r", encoding="utf-8") as f:
        twin = json.load(f)

    twin["compaction_summary"] = summary
    twin["compaction_timestamp"] = datetime.now(timezone.utc).isoformat()

    atomic_write_json(twin_path, twin)
    logger.info("Compaction summary added to twin", extra={"twin_id": twin.get("twin_id")})
