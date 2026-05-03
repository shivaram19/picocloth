"""
Complexity metrics for adaptive agent spawning decisions.

Implements the four complexity dimensions from the AgentSpawn paper:
- File count (number of files referenced)
- Cyclomatic complexity (AST-based or heuristic)
- Uncertainty (entropy of intent classification)
- Unfamiliarity (Jaccard distance from known patterns)

When complexity exceeds the threshold, a new agent is spawned dynamically.

Citation: AgentSpawn paper (arXiv:2602.07072v1), Section 4.2
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import SPAWN_COMPLEXITY_THRESHOLD
from picocloth_cli.core.logging import get_logger
from picocloth_cli.intent.classifier import Intent

logger = get_logger(__name__)


@dataclass
class ComplexityMetrics:
    """Complexity score breakdown for a given user intent."""

    file_count: float       # 0.0 - 1.0, normalized
    cyclomatic: float       # 0.0 - 1.0, heuristic
    uncertainty: float      # 0.0 - 1.0, entropy of intent distribution
    unfamiliarity: float    # 0.0 - 1.0, Jaccard distance from doctrine
    overall: float          # Weighted composite score

    def should_spawn(self, threshold: float = SPAWN_COMPLEXITY_THRESHOLD) -> bool:
        """Return True if this intent warrants dynamic agent spawning."""
        return self.overall >= threshold


def _count_referenced_files(text: str) -> int:
    """Count likely file references in the intent text."""
    # Match common file patterns
    patterns = [
        r"\b[\w\-]+\.(py|js|ts|go|rs|java|cpp|c|h|yaml|yml|json|toml|md|txt|sh)\b",
        r"\b(file|path|directory|folder|module|package)\s+['\"]?([\w\-/\.]+)['\"]?",
    ]
    count = 0
    for pat in patterns:
        count += len(re.findall(pat, text, re.IGNORECASE))
    return count


def _normalize_file_count(count: int) -> float:
    """Normalize file count to 0.0-1.0 scale.

    Score saturates at 10 files (high complexity).
    """
    return min(count / 10.0, 1.0)


def _estimate_cyclomatic_complexity(text: str) -> float:
    """Heuristic cyclomatic complexity from intent text.

    Since we don't have source code at intent time, we estimate from
    linguistic markers of complexity: conditionals, loops, parallel tasks.
    """
    complexity_markers = [
        r"\b(if|when|unless|provided|assuming)\b",
        r"\b(for each|for every|loop|iterate|while)\b",
        r"\b(and\s+also|in addition|meanwhile|concurrently|parallel)\b",
        r"\b(compare|contrast|difference|versus|vs)\b",
        r"\b(validate|verify|check|test|ensure)\b",
    ]
    count = sum(len(re.findall(pat, text, re.IGNORECASE)) for pat in complexity_markers)
    # Saturate at 5 markers
    return min(count / 5.0, 1.0)


def _compute_uncertainty(intent: Intent) -> float:
    """Compute uncertainty from intent classification confidence.

    High confidence → low uncertainty.
    Low confidence → high uncertainty (may need spawning for safety).
    """
    # Invert and scale: confidence 0.95 → uncertainty 0.05
    return max(0.0, 1.0 - intent.confidence)


def _compute_unfamiliarity(text: str) -> float:
    """Compute unfamiliarity as Jaccard distance from known doctrine patterns.

    Reads shared/doctrine/skills/ for known keywords and measures overlap.
    """
    from picocloth_cli.core.constants import DOCTRINE_DIR

    known_keywords: set[str] = set()
    skills_dir = DOCTRINE_DIR / "skills"
    if skills_dir.exists():
        for f in skills_dir.glob("*.md"):
            try:
                content = f.read_text().lower()
                words = set(re.findall(r"\b\w{4,}\b", content))
                known_keywords.update(words)
            except Exception:
                continue

    if not known_keywords:
        # No doctrine loaded — assume moderate unfamiliarity
        return 0.5

    input_words = set(re.findall(r"\b\w{4,}\b", text.lower()))
    if not input_words:
        return 0.5

    intersection = input_words & known_keywords
    union = input_words | known_keywords
    jaccard = len(intersection) / len(union) if union else 0.0
    unfamiliarity = 1.0 - jaccard

    # Scale: small vocab overlap is normal; only high unfamiliarity matters
    return min(unfamiliarity * 3.0, 1.0)


def evaluate_complexity(intent: Intent) -> ComplexityMetrics:
    """Evaluate the complexity of a user intent for spawning decisions.

    Returns a ComplexityMetrics with all four dimensions and a composite
    score. If overall >= SPAWN_COMPLEXITY_THRESHOLD, dynamic spawning
    is recommended.
    """
    text = intent.raw_input

    fc = _normalize_file_count(_count_referenced_files(text))
    cc = _estimate_cyclomatic_complexity(text)
    un = _compute_uncertainty(intent)
    uf = _compute_unfamiliarity(text)

    # Weighted composite (weights from AgentSpawn heuristic tuning)
    weights = {
        "file_count": 0.25,
        "cyclomatic": 0.25,
        "uncertainty": 0.20,
        "unfamiliarity": 0.30,
    }
    overall = (
        weights["file_count"] * fc +
        weights["cyclomatic"] * cc +
        weights["uncertainty"] * un +
        weights["unfamiliarity"] * uf
    )

    metrics = ComplexityMetrics(
        file_count=round(fc, 3),
        cyclomatic=round(cc, 3),
        uncertainty=round(un, 3),
        unfamiliarity=round(uf, 3),
        overall=round(overall, 3),
    )

    logger.debug("Complexity evaluated", extra={
        "overall": metrics.overall,
        "file_count": metrics.file_count,
        "cyclomatic": metrics.cyclomatic,
        "uncertainty": metrics.uncertainty,
        "unfamiliarity": metrics.unfamiliarity,
        "should_spawn": metrics.should_spawn(),
    })

    return metrics
