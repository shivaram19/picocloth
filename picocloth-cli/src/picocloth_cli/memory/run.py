"""
Run layer CRUD — ephemeral working memory per execution session.

Created at turn start, archived or discarded at turn end. Stores
active context, tool call history, and subagent transcripts.

Citation: Graph Digital 4-layer memory — Run as Working Memory
Citation: Claude Code sidechain transcript design (arXiv:2604.14228v1)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picocloth_cli.core.constants import CLI_RUN_DIR
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import atomic_write_json, append_jsonl, read_jsonl

logger = get_logger(__name__)


def get_session_dir(session_id: str) -> Path:
    """Get or create the run directory for a session."""
    session_dir = CLI_RUN_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def write_context(session_id: str, context: dict[str, Any]) -> None:
    """Write the active context window for a session."""
    session_dir = get_session_dir(session_id)
    atomic_write_json(session_dir / "context.json", context)


def read_context(session_id: str) -> dict[str, Any] | None:
    """Read the active context window for a session."""
    session_dir = get_session_dir(session_id)
    path = session_dir / "context.json"
    if path.exists():
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def append_tool_call(session_id: str, tool_call: dict[str, Any]) -> None:
    """Append a tool call to the session's tool history."""
    session_dir = get_session_dir(session_id)
    append_jsonl(session_dir / "tools.jsonl", {
        **tool_call,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def get_tool_calls(session_id: str, limit: int = 0) -> list[dict[str, Any]]:
    """Read tool call history for a session."""
    session_dir = get_session_dir(session_id)
    return read_jsonl(session_dir / "tools.jsonl", limit=limit)


def create_subagent_transcript(session_id: str, spawn_id: str) -> Path:
    """Create a sidechain transcript file for a subagent.

    Citation: Claude Code sidechain transcript design prevents parent
    context inflation by storing subagent conversations separately.
    """
    session_dir = get_session_dir(session_id)
    subagents_dir = session_dir / "subagents"
    subagents_dir.mkdir(parents=True, exist_ok=True)
    return subagents_dir / f"{spawn_id}.jsonl"


def append_subagent_turn(session_id: str, spawn_id: str, turn: dict[str, Any]) -> None:
    """Append a turn to a subagent's sidechain transcript."""
    transcript_path = create_subagent_transcript(session_id, spawn_id)
    append_jsonl(transcript_path, {
        **turn,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def get_subagent_transcript(session_id: str, spawn_id: str, limit: int = 0) -> list[dict[str, Any]]:
    """Read a subagent's sidechain transcript."""
    session_dir = get_session_dir(session_id)
    transcript_path = session_dir / "subagents" / f"{spawn_id}.jsonl"
    return read_jsonl(transcript_path, limit=limit)


def archive_session(session_id: str) -> Path:
    """Archive a session's run directory to compaction-archive."""
    from picocloth_cli.core.constants import COMPACTION_ARCHIVE_DIR

    session_dir = get_session_dir(session_id)
    archive_dir = COMPACTION_ARCHIVE_DIR / "picocloth-cli"
    archive_dir.mkdir(parents=True, exist_ok=True)

    import shutil
    dest = archive_dir / session_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(session_dir, dest)

    logger.info("Session archived", extra={"session": session_id, "dest": str(dest)})
    return dest
