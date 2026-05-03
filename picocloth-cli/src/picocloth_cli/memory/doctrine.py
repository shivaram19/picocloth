"""
Doctrine layer access — immutable skills, schemas, and policies.

The doctrine layer is read-only for worker nodes. It contains the
"constitution" of the fleet: skills (markdown with YAML frontmatter),
tool definitions, behavioral policies, and character modules.

Citation: Graph Digital 4-layer memory — Doctrine as Constitution
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from picocloth_cli.core.constants import DOCTRINE_DIR
from picocloth_cli.core.exceptions import MemoryError
from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)


def list_skills() -> list[dict[str, Any]]:
    """List all skill definitions in doctrine/skills/."""
    skills_dir = DOCTRINE_DIR / "skills"
    if not skills_dir.exists():
        return []

    skills = []
    for f in sorted(skills_dir.glob("*.md")):
        try:
            content = f.read_text()
            # Parse YAML frontmatter if present
            meta = _parse_frontmatter(content)
            skills.append({
                "id": f.stem,
                "path": str(f.relative_to(DOCTRINE_DIR)),
                "title": meta.get("title", f.stem),
                "description": meta.get("description", ""),
                "tags": meta.get("tags", []),
            })
        except Exception as exc:
            logger.warning("Failed to read skill", extra={"file": str(f), "error": str(exc)})

    return skills


def read_skill(skill_id: str) -> dict[str, Any]:
    """Read a skill definition by ID."""
    skill_path = DOCTRINE_DIR / "skills" / f"{skill_id}.md"
    if not skill_path.exists():
        raise MemoryError(f"Skill not found: {skill_id}")

    content = skill_path.read_text()
    meta = _parse_frontmatter(content)
    return {
        "id": skill_id,
        "path": str(skill_path),
        "meta": meta,
        "content": content,
    }


def list_policies() -> list[dict[str, Any]]:
    """List all policies in doctrine/policies/."""
    policies_dir = DOCTRINE_DIR / "policies"
    if not policies_dir.exists():
        return []
    return [
        {"id": f.stem, "path": str(f.relative_to(DOCTRINE_DIR))}
        for f in sorted(policies_dir.glob("*.md"))
    ]


def list_schemas() -> list[dict[str, Any]]:
    """List all schemas in doctrine/schemas/."""
    schemas_dir = DOCTRINE_DIR / "schemas"
    if not schemas_dir.exists():
        return []
    return [
        {"id": f.stem, "path": str(f.relative_to(DOCTRINE_DIR))}
        for f in sorted(schemas_dir.glob("*.json"))
    ]


def _parse_frontmatter(content: str) -> dict[str, Any]:
    """Extract YAML frontmatter from markdown content."""
    import yaml

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                pass
    return {}
