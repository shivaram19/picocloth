"""
Chat session history management.

Persists conversation turns to ~/.picocloth/sessions/ for continuity
across CLI invocations. Supports listing, loading, and resuming sessions.

Citation: Claude Code sidechain transcript design (arXiv:2604.14228v1)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from picocloth_cli.core.constants import CLI_SESSIONS_DIR
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import read_jsonl

logger = get_logger(__name__)


def list_sessions() -> list[dict[str, Any]]:
    """List all saved chat sessions with metadata."""
    if not CLI_SESSIONS_DIR.exists():
        return []

    sessions = []
    for f in sorted(CLI_SESSIONS_DIR.glob("*.jsonl"), reverse=True):
        try:
            turns = read_jsonl(f)
            user_turns = [t for t in turns if t.get("role") == "user"]
            sessions.append({
                "id": f.stem,
                "turns": len(turns),
                "user_turns": len(user_turns),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
        except Exception as exc:
            logger.warning("Failed to read session", extra={"file": str(f), "error": str(exc)})

    return sessions


def load_session(session_id: str) -> list[dict[str, Any]]:
    """Load all turns from a session file."""
    session_file = CLI_SESSIONS_DIR / f"{session_id}.jsonl"
    if not session_file.exists():
        return []
    return read_jsonl(session_file)


def get_last_user_message(session_id: str) -> str | None:
    """Get the most recent user message from a session."""
    turns = load_session(session_id)
    for turn in reversed(turns):
        if turn.get("role") == "user":
            return turn.get("content")
    return None


def delete_session(session_id: str) -> bool:
    """Delete a session file. Returns True if deleted."""
    session_file = CLI_SESSIONS_DIR / f"{session_id}.jsonl"
    if session_file.exists():
        session_file.unlink()
        logger.info("Session deleted", extra={"session_id": session_id})
        return True
    return False
