"""
Fact extraction from digital twin snapshots.

Extracts durable facts from twin archives using both rule-based markers
(preference, decision, constraint patterns) and structured field access.

Extracted facts are written to shared/project/facts/ for cross-session
persistence.

Citation: PicoCloth Digital Twin Guardian Hook (hooks/digital_twin_guardian.py)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picocloth_cli.core.constants import DIGITAL_TWINS_DIR, PROJECT_DIR
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import append_jsonl

logger = get_logger(__name__)

# Rule-based fact markers (same as Digital Twin Guardian)
FACT_PATTERNS = [
    (r"\b(I |we )?(prefer|like|use|choose|opt for)\b", "preference", 0.85),
    (r"\b(we |let['']s )?(decided?|agreed?|chose|settled on|concluded)\b", "decision", 0.90),
    (r"\b(must|should|needs? to|requires?|has to|obligation)\b", "constraint", 0.80),
    (r"\b(don['']t|never|always|avoid|ensure|guarantee)\b", "policy", 0.75),
    (r"\b(important|critical|essential|key|primary|main)\b", "priority", 0.70),
]


def extract_facts_from_twin(twin: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract facts from a single digital twin snapshot.

    Returns:
        List of fact dicts with key, content, type, confidence, source.
    """
    facts = []
    snapshot = twin.get("conversation_snapshot", [])
    twin_id = twin.get("twin_id", "unknown")

    for turn in snapshot:
        content = str(turn.get("content", ""))
        for pattern, fact_type, base_confidence in FACT_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                # Extract the sentence containing the match
                sentences = re.split(r'(?<=[.!?])\s+', content)
                for sentence in sentences:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        fact = {
                            "key": f"{fact_type}_{hash(sentence) % 10000:04d}",
                            "content": sentence.strip(),
                            "type": fact_type,
                            "confidence": base_confidence,
                            "source": f"twin:{twin_id}",
                            "timestamp": twin.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        }
                        facts.append(fact)
                        break  # One fact per pattern per turn

    # Also extract from structured extracted_facts field
    existing = twin.get("extracted_facts", [])
    for f in existing:
        facts.append({
            "key": f.get("key", "unknown"),
            "content": f.get("content", ""),
            "type": "extracted",
            "confidence": f.get("confidence", 0.5),
            "source": f"twin:{twin_id}",
            "timestamp": twin.get("timestamp", datetime.now(timezone.utc).isoformat()),
        })

    return facts


def extract_all_facts(
    node_id: str | None = None,
    *,
    save: bool = True,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Extract facts from all digital twins, optionally saving to project/facts/.

    Args:
        node_id: Filter by node. None = all nodes.
        save: If True, append extracted facts to project/facts/auto_extracted.jsonl
        limit: Maximum twins to process

    Returns:
        Flat list of all extracted facts.
    """
    from picocloth_cli.twin.search import search_twins

    twins = search_twins("", node_id=node_id, limit=limit)
    all_facts = []

    for twin in twins:
        facts = extract_facts_from_twin(twin)
        all_facts.extend(facts)

    if save and all_facts:
        facts_file = PROJECT_DIR / "facts" / "auto_extracted.jsonl"
        facts_file.parent.mkdir(parents=True, exist_ok=True)
        for fact in all_facts:
            append_jsonl(facts_file, fact)
        logger.info("Facts extracted and saved", extra={
            "count": len(all_facts),
            "destination": str(facts_file),
        })

    return all_facts
