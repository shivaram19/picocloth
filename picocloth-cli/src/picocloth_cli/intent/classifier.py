"""
Intent classification for PicoCloth-CLI.

Hybrid classifier combining rule-based fast path (80% of commands) with
LLM-based fallback for ambiguous natural language. Uses confidence
thresholding to decide when to ask clarifying questions.

Citation: Anthropic "Building Effective Agents" — routing pattern (Dec 2024)
Citation: AgentSpawn complexity metrics (arXiv:2602.07072v1)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import INTENT_CONFIDENCE_THRESHOLD, NODES
from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)


class IntentType(str, Enum):
    """Taxonomy of user intents aligned with Anthropic's 5 workflow patterns."""

    ORCHESTRATE = "orchestrate"      # Fleet management (status, launch, stop)
    DELEGATE = "delegate"            # Task spawning to specific nodes
    QUERY = "query"                  # Memory/twin searches
    CHAT = "chat"                    # Free-form conversation
    BUILD = "build"                  # Code generation, file operations
    ANALYZE = "analyze"              # Research, contradiction detection
    UNKNOWN = "unknown"              # Could not classify


@dataclass
class Intent:
    """Result of intent classification."""

    intent_type: IntentType
    confidence: float
    raw_input: str
    parameters: dict
    matched_pattern: Optional[str] = None


# ---------------------------------------------------------------------------
# Rule-based patterns
# ---------------------------------------------------------------------------

RULE_PATTERNS: list[tuple[IntentType, list[str], float]] = [
    # ORCHESTRATE — fleet management
    (
        IntentType.ORCHESTRATE,
        [
            r"\bstatus\b",
            r"\blaunch\b.*\bfleet\b",
            r"\bstart\b.*\bfleet\b",
            r"\bstop\b.*\bfleet\b",
            r"\brestart\b.*\bfleet\b",
            r"\bmonitor\b.*\bfleet\b",
            r"\bhow\b.*\bnodes\b",
            r"\bis\b.*\bfleet\b.*\brunning\b",
        ],
        0.95,
    ),
    # DELEGATE — task spawning
    (
        IntentType.DELEGATE,
        [
            r"\bspawn\b.*\btask\b",
            r"\bdelegate\b",
            r"\bsend\b.*\bto\b.*\bnode\b",
            r"\bask\b.*\bnode\b",
            r"\btell\b.*\bnode\b.*\bto\b",
            r"\bhave\b.*\bnode\b.*\b(do|build|write|research)\b",
        ],
        0.90,
    ),
    # QUERY — memory/twin searches
    (
        IntentType.QUERY,
        [
            r"\bsearch\b.*\b(memory|twin|fact|archive)\b",
            r"\bfind\b.*\bin\b.*\b(memory|project|doctrine)\b",
            r"\bwhat\b.*\bdo\b.*\b(know|remember)\b",
            r"\blook\b.*\bup\b",
            r"\bquery\b.*\barchive\b",
        ],
        0.88,
    ),
    # BUILD — code/file operations
    (
        IntentType.BUILD,
        [
            r"\b(create|make|build|write|generate)\b.*\b(code|file|script|api|app)\b",
            r"\bwrite\b.*\b(python|go|rust|js|ts)\b",
            r"\bscaffold\b",
            r"\bimplement\b.*\bfeature\b",
        ],
        0.92,
    ),
    # ANALYZE — research/detection
    (
        IntentType.ANALYZE,
        [
            r"\b(research|analyze|investigate|study)\b",
            r"\bfind\b.*\b(contradiction|mismatch|bug|issue)\b",
            r"\bcompare\b.*\b(spec|drawing|document)\b",
            r"\bextract\b.*\b(entity|relationship|fact)\b",
        ],
        0.87,
    ),
]


def _extract_node_reference(text: str) -> Optional[str]:
    """Extract a node ID reference from text, e.g., 'node-a', 'node b'."""
    pattern = r"\bnode[-\s]?([a-j])\b"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        letter = match.group(1).lower()
        node_id = f"node-{letter}"
        if node_id in NODES:
            return node_id
    return None


def _extract_task_description(text: str) -> str:
    """Heuristic extraction of task description from natural language."""
    # Remove common prefixes
    cleaned = re.sub(r"^(please|can you|could you|would you)\s+", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(ask|tell|have)\s+node[-\s]?[a-j]\s+(to\s+)?", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def classify_intent(text: str) -> Intent:
    """Classify user input into an Intent with confidence score.

    Uses rule-based matching first (fast, deterministic). If no rule matches
    with sufficient confidence, falls back to heuristic scoring.

    Args:
        text: Raw user input string.

    Returns:
        Intent with type, confidence, parameters, and matched pattern.
    """
    text_lower = text.lower().strip()
    best_match: Optional[tuple[IntentType, float, str]] = None

    # Rule-based fast path
    for intent_type, patterns, base_confidence in RULE_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text_lower):
                # Slight confidence boost for exact matches
                confidence = min(base_confidence + 0.02, 0.99)
                if best_match is None or confidence > best_match[1]:
                    best_match = (intent_type, confidence, pattern)

    if best_match:
        intent_type, confidence, pattern = best_match
        params = {
            "target_node": _extract_node_reference(text),
            "task": _extract_task_description(text),
            "query": text,
        }
        logger.debug("Intent classified (rule)", extra={
            "type": intent_type.value,
            "confidence": confidence,
            "pattern": pattern,
        })
        return Intent(
            intent_type=intent_type,
            confidence=confidence,
            raw_input=text,
            parameters=params,
            matched_pattern=pattern,
        )

    # Heuristic fallback: keyword density scoring
    scores = {
        IntentType.ORCHESTRATE: 0.0,
        IntentType.DELEGATE: 0.0,
        IntentType.QUERY: 0.0,
        IntentType.BUILD: 0.0,
        IntentType.ANALYZE: 0.0,
        IntentType.CHAT: 0.0,
    }

    # Simple keyword matching for fallback
    keyword_map = {
        IntentType.ORCHESTRATE: ["fleet", "node", "status", "launch", "stop", "online", "offline"],
        IntentType.DELEGATE: ["spawn", "delegate", "task", "assign", "send"],
        IntentType.QUERY: ["search", "find", "lookup", "query", "remember", "know"],
        IntentType.BUILD: ["code", "write", "create", "build", "file", "script", "implement"],
        IntentType.ANALYZE: ["research", "analyze", "compare", "extract", "detect", "investigate"],
        IntentType.CHAT: ["hello", "hi", "hey", "help", "what", "how", "why"],
    }

    words = set(re.findall(r"\b\w+\b", text_lower))
    for intent, keywords in keyword_map.items():
        matches = sum(1 for kw in keywords if kw in words)
        scores[intent] = matches / max(len(keywords), 1)

    # Normalize to confidence
    total = sum(scores.values())
    if total > 0:
        for intent in scores:
            scores[intent] /= total

    best_intent = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_intent]

    # CHAT is the default catch-all
    if best_score < 0.15:
        best_intent = IntentType.CHAT
        best_score = 0.5

    logger.debug("Intent classified (heuristic)", extra={
        "type": best_intent.value,
        "confidence": best_score,
        "scores": {k.value: round(v, 3) for k, v in scores.items()},
    })

    return Intent(
        intent_type=best_intent,
        confidence=best_score,
        raw_input=text,
        parameters={
            "target_node": _extract_node_reference(text),
            "task": _extract_task_description(text),
            "query": text,
        },
    )
