"""
Project layer CRUD — durable facts, decisions, and entities.

The project layer stores structured, append-only JSON/JSONL data.
All writes are timestamped and include source attribution.

Citation: Graph Digital 4-layer memory — Project as Knowledge Graph
Citation: Claude Code file-lock coordination (Anthropic, Feb 2026)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picocloth_cli.core.constants import PROJECT_DIR
from picocloth_cli.core.exceptions import MemoryError
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import atomic_write_json, append_jsonl, lock_file, read_json_safe, read_jsonl

logger = get_logger(__name__)

CATEGORIES = ["facts", "decisions", "entities", "outreach"]


def list_categories() -> list[str]:
    """List available project categories."""
    return CATEGORIES


def read_record(category: str, key: str) -> Any:
    """Read a record from project memory.

    Tries JSON first, then JSONL.
    """
    if category not in CATEGORIES:
        raise MemoryError(f"Unknown category: {category}. Known: {CATEGORIES}")

    json_path = PROJECT_DIR / category / f"{key}.json"
    if json_path.exists():
        return read_json_safe(json_path)

    jsonl_path = PROJECT_DIR / category / f"{key}.jsonl"
    if jsonl_path.exists():
        return read_jsonl(jsonl_path)

    return None


def write_record(
    category: str,
    key: str,
    data: Any,
    *,
    source: str = "picocloth-cli",
    append: bool = False,
) -> None:
    """Write a record to project memory.

    Args:
        category: e.g., "facts", "decisions", "entities"
        key: File key (without extension)
        data: Data to write
        source: Attribution source
        append: If True, append as JSONL; if False, overwrite JSON
    """
    if category not in CATEGORIES:
        raise MemoryError(f"Unknown category: {category}. Known: {CATEGORIES}")

    dir_path = PROJECT_DIR / category
    dir_path.mkdir(parents=True, exist_ok=True)

    # Enrich with metadata
    enriched = {
        "data": data,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if append:
        append_jsonl(dir_path / f"{key}.jsonl", enriched)
        logger.info("Project record appended", extra={"category": category, "key": key})
    else:
        with lock_file(dir_path / f"{key}.json"):
            atomic_write_json(dir_path / f"{key}.json", enriched)
        logger.info("Project record written", extra={"category": category, "key": key})


def list_records(category: str) -> list[dict[str, Any]]:
    """List all record keys in a category."""
    if category not in CATEGORIES:
        raise MemoryError(f"Unknown category: {category}")

    dir_path = PROJECT_DIR / category
    if not dir_path.exists():
        return []

    records = []
    for f in sorted(dir_path.iterdir()):
        if f.suffix in (".json", ".jsonl"):
            records.append({
                "key": f.stem,
                "type": f.suffix,
                "size": f.stat().st_size,
            })
    return records
