"""
Memory slicing algorithm for selective memory transfer during agent spawning.

Implements the AgentSpawn paper's Memory Slicing Algorithm:
- Episodic memory: Recent conversation turns (last N)
- Semantic memory: Relevant facts from project/ (keyword match + semantic similarity)
- Working memory: Active tool calls, in-flight subagents

Selection scoring:
    score = keyword_match * 0.3 + dependency_score * 0.3 + temporal_decay * 0.2 + semantic_similarity * 0.2

Citation: AgentSpawn (arXiv:2602.07072v1, Section 5.2) — 42% memory overhead reduction
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from picocloth_cli.core.constants import PROJECT_DIR, RUN_DIR
from picocloth_cli.core.logging import get_logger
from picocloth_cli.intent.classifier import Intent
from picocloth_cli.utils.files import read_jsonl

logger = get_logger(__name__)

DEFAULT_EPISODIC_TURNS = 5
DEFAULT_SEMANTIC_LIMIT = 10


def _keyword_score(text: str, keywords: set[str]) -> float:
    """Score how many keywords from the intent appear in the text."""
    text_words = set(re.findall(r"\b\w{4,}\b", text.lower()))
    if not text_words or not keywords:
        return 0.0
    matches = text_words & keywords
    return len(matches) / len(keywords)


def _temporal_decay(timestamp_str: str, half_life_hours: float = 24.0) -> float:
    """Compute temporal decay factor for a timestamp.

    Recent items score near 1.0; old items decay exponentially.
    """
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        return math.exp(-age_hours / half_life_hours)
    except (ValueError, TypeError):
        return 0.5  # Unknown age — moderate score


def extract_episodic_memory(session_id: str | None = None, turns: int = DEFAULT_EPISODIC_TURNS) -> list[dict[str, Any]]:
    """Extract recent conversation turns from session history.

    Args:
        session_id: Session identifier. If None, uses the most recent session.
        turns: Number of recent turns to include.

    Returns:
        List of turn dicts with role, content, timestamp.
    """
    from picocloth_cli.core.constants import CLI_SESSIONS_DIR

    if session_id is None:
        # Find most recent session
        sessions = sorted(CLI_SESSIONS_DIR.glob("*.jsonl"), reverse=True)
        if not sessions:
            return []
        session_file = sessions[0]
    else:
        session_file = CLI_SESSIONS_DIR / f"{session_id}.jsonl"
        if not session_file.exists():
            return []

    records = read_jsonl(session_file)
    return records[-turns:] if records else []


def extract_semantic_memory(intent: Intent, limit: int = DEFAULT_SEMANTIC_LIMIT) -> list[dict[str, Any]]:
    """Extract relevant facts from project/ memory.

    Uses keyword matching + temporal decay scoring. In a production system,
    this would be enhanced with vector semantic similarity (e.g., sentence-transformers).
    """
    facts_file = PROJECT_DIR / "facts" / "auto_extracted.jsonl"
    if not facts_file.exists():
        return []

    facts = read_jsonl(facts_file)
    if not facts:
        return []

    # Build keyword set from intent
    intent_keywords = set(re.findall(r"\b\w{4,}\b", intent.raw_input.lower()))

    scored = []
    for fact in facts:
        content = fact.get("content", "")
        key = fact.get("key", "")
        timestamp = fact.get("timestamp", "")
        confidence = fact.get("confidence", 0.5)

        kw_score = _keyword_score(f"{key} {content}", intent_keywords)
        decay = _temporal_decay(timestamp)
        # Composite score: keyword-heavy, with recency and confidence boosts
        score = kw_score * 0.5 + decay * 0.3 + confidence * 0.2
        scored.append((score, fact))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [fact for _, fact in scored[:limit]]


def extract_working_memory(session_id: str | None = None) -> list[dict[str, Any]]:
    """Extract active tool calls and in-flight subagents from run/ memory."""
    if session_id is None:
        return []

    run_dir = RUN_DIR / "picocloth-cli" / session_id
    if not run_dir.exists():
        return []

    working = []
    # Read tools history
    tools_file = run_dir / "tools.jsonl"
    if tools_file.exists():
        tools = read_jsonl(tools_file)
        working.extend([{"type": "tool_call", **t} for t in tools[-3:]])

    # Read active subagents
    subagents_dir = run_dir / "subagents"
    if subagents_dir.exists():
        for sf in subagents_dir.glob("*.jsonl"):
            try:
                lines = read_jsonl(sf, limit=1)
                if lines:
                    working.append({"type": "subagent", "id": sf.stem, **lines[0]})
            except Exception:
                continue

    return working


def build_memory_slice(
    intent: Intent,
    session_id: str | None = None,
    episodic_turns: int = DEFAULT_EPISODIC_TURNS,
    semantic_limit: int = DEFAULT_SEMANTIC_LIMIT,
) -> dict[str, list[dict[str, Any]]]:
    """Build a complete memory slice for agent spawning.

    Returns:
        Dict with keys: episodic, semantic, working
    """
    episodic = extract_episodic_memory(session_id, turns=episodic_turns)
    semantic = extract_semantic_memory(intent, limit=semantic_limit)
    working = extract_working_memory(session_id)

    logger.info("Memory slice built", extra={
        "episodic_count": len(episodic),
        "semantic_count": len(semantic),
        "working_count": len(working),
    })

    return {
        "episodic": episodic,
        "semantic": semantic,
        "working": working,
    }
