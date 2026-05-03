"""
Digital twin archive search.

Provides full-text search across shared/digital-twins/ with filtering
by node, date range, and trigger type. Returns relevance-ranked results.

Citation: PicoCloth Digital Twin Protocol (docs/ARCHITECTURE.md)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from picocloth_cli.core.constants import DIGITAL_TWINS_DIR, NODES
from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)


def search_twins(
    query: str,
    *,
    node_id: str | None = None,
    trigger_type: str | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search digital twin archives with multiple filters.

    Args:
        query: Full-text search string (case-insensitive)
        node_id: Filter by node (e.g., "node-a")
        trigger_type: Filter by trigger (e.g., "context_budget_75_percent")
        after: Only twins created after this datetime
        before: Only twins created before this datetime
        limit: Maximum results to return

    Returns:
        List of twin dicts with added _score and _path fields.
    """
    twin_dir = DIGITAL_TWINS_DIR
    if node_id:
        if node_id not in NODES and node_id != "picocloth-cli":
            logger.warning("Unknown node_id in twin search", extra={"node_id": node_id})
            return []
        twin_dir = twin_dir / node_id

    if not twin_dir.exists():
        return []

    query_lower = query.lower()
    scored_results = []

    for twin_file in twin_dir.rglob("*.json"):
        try:
            import json
            with open(twin_file, "r", encoding="utf-8") as f:
                twin = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        # Apply filters
        if trigger_type and twin.get("trigger") != trigger_type:
            continue

        twin_ts = twin.get("timestamp", "")
        if twin_ts:
            try:
                twin_dt = datetime.fromisoformat(twin_ts.replace("Z", "+00:00"))
                if after and twin_dt < after:
                    continue
                if before and twin_dt > before:
                    continue
            except ValueError:
                pass

        # Compute relevance score
        score = 0
        content = json.dumps(twin).lower()

        # Filename match
        if query_lower in twin_file.name.lower():
            score += 3

        # Exact phrase match in content
        if query_lower in content:
            score += 2

        # Keyword token matches
        query_tokens = set(query_lower.split())
        content_tokens = set(content.split())
        token_matches = query_tokens & content_tokens
        score += len(token_matches)

        # Timestamp recency boost (newer = higher)
        if twin_ts:
            try:
                twin_dt = datetime.fromisoformat(twin_ts.replace("Z", "+00:00"))
                age_days = (datetime.now(tz=twin_dt.tzinfo) - twin_dt).days
                score += max(0, 5 - age_days)  # +5 for today, decaying
            except ValueError:
                pass

        twin["_score"] = score
        twin["_path"] = str(twin_file.relative_to(DIGITAL_TWINS_DIR))
        scored_results.append(twin)

    scored_results.sort(key=lambda x: x["_score"], reverse=True)
    return scored_results[:limit]
