"""
Retrospective Optimizer (RO) v1.0
=================================
Query reformulation and template optimization from historical yield data.

Backed by research:
  - ConvSearch-R1 (Zhu et al., May 2025, arXiv:2505.15776): Self-driven
    query reformulation via RL. Two-stage: SDPWU + RGRL. 10%+ improvement
    on TopiOCQA with 3B model. Rank-incentive reward shaping.
  - Nogueira & Cho (2017, EMNLP): RL query reformulation with 5-20%
    recall improvement. "Only a small subset of terms are useful."
  - Retroformer / TRICE (2024): Agents learn from retrospective execution
    feedback. Credit assignment across long tool-use chains.
  - Pirolli & Card (1999): Information Foraging Theory — optimize
    information gain per unit cost. "Information scent" guides patches.

Design principle: Extends existing SearchStrategyEngine yield DB rather
than replacing it. Reads `shared/memory/search-yield.jsonl`, enriches
with template scoring, writes back.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)

# ── Topic Type Classifier ────────────────────────────────────
# Simple keyword-based classifier for routing query templates.
# Citation: Nogueira & Cho — different query types need different terms.

TOPIC_TYPE_KEYWORDS = {
    "research": ["paper", "study", "arxiv", "survey", "review", "method", "algorithm", "dataset", "benchmark"],
    "technical": ["tutorial", "guide", "how to", "implementation", "code", "github", "docs", "api"],
    "business": ["market", "revenue", "growth", "funding", "startup", "investment", "competitor", "strategy"],
    "general": [],  # Fallback
}


# ── Data Models ──────────────────────────────────────────────

@dataclass
class YieldRecord:
    """Enriched yield record for retrospective analysis."""
    timestamp: str
    topic: str
    mode: str
    platforms: list[str]
    queries_count: int
    results_count: int
    facts_count: int
    avg_confidence: float
    knowledge_yield: float
    templates: list[str] = field(default_factory=list)
    topic_type: str = "general"
    platform_yields: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "topic": self.topic,
            "mode": self.mode,
            "platforms": self.platforms,
            "queries_count": self.queries_count,
            "results_count": self.results_count,
            "facts_count": self.facts_count,
            "avg_confidence": self.avg_confidence,
            "knowledge_yield": self.knowledge_yield,
            "templates": self.templates,
            "topic_type": self.topic_type,
            "platform_yields": self.platform_yields,
        }


@dataclass
class ReformulationSuggestion:
    """A suggested query reformulation."""
    suggested_query: str
    source_template: str
    expected_yield: float
    confidence: float
    rationale: str


# ── Core Optimizer ───────────────────────────────────────────

class RetrospectiveOptimizer:
    """Learns from historical search yield to suggest better queries.

    Usage:
        optimizer = RetrospectiveOptimizer()
        optimizer.record(plan, results_count=15, facts_count=7, avg_confidence=0.72)
        suggestions = optimizer.suggest_reformulation("AI market")
    """

    DECAY_DAYS = 30  # Exponential decay half-life (Pirolli & Card recency bias)

    def __init__(self, yield_db_path: Path | None = None) -> None:
        self.yield_db_path = yield_db_path or Path("shared/memory/search-yield.jsonl")
        self.yield_db_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        plan: Any,  # SearchPlan
        results_count: int,
        facts_count: int,
        avg_confidence: float,
    ) -> None:
        """Record an enriched yield record.

        Reward function (ConvSearch-R1 style):
            R = facts_count × avg_confidence / queries_count
        """
        templates = [q.get("query", "") for q in getattr(plan, "queries", [])]
        topic_type = self._classify_topic_type(getattr(plan, "topic", ""))
        queries_count = max(1, len(getattr(plan, "queries", [])))

        # Per-platform yield (simplified: distribute equally)
        platforms = getattr(plan, "platforms", ["duckduckgo"])
        platform_yields = {}
        if platforms:
            per_platform = round(facts_count * avg_confidence / len(platforms), 3)
            for p in platforms:
                platform_yields[p] = per_platform

        record = YieldRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            topic=getattr(plan, "topic", ""),
            mode=getattr(plan, "mode", "unknown"),
            platforms=platforms,
            queries_count=queries_count,
            results_count=results_count,
            facts_count=facts_count,
            avg_confidence=round(avg_confidence, 3),
            knowledge_yield=round(facts_count * avg_confidence / queries_count, 3),
            templates=templates,
            topic_type=topic_type,
            platform_yields=platform_yields,
        )

        with open(self.yield_db_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

        logger.info(
            "Yield recorded: topic=%s mode=%s yield=%.3f",
            record.topic, record.mode, record.knowledge_yield,
        )

    def suggest_reformulation(
        self,
        topic: str,
        current_queries: list[str] | None = None,
        limit: int = 5,
    ) -> list[ReformulationSuggestion]:
        """Suggest reformulated queries based on historical yield.

        Strategy:
        1. Classify topic type
        2. Load historical records for similar topics
        3. Apply temporal decay weighting
        4. Identify high-yield templates
        5. Generate suggestions by substituting topic into templates
        """
        topic_type = self._classify_topic_type(topic)
        records = self._load_records()

        if not records:
            # No history — return generic high-yield templates
            return self._fallback_suggestions(topic, topic_type, limit)

        # Filter to similar topic type (or exact topic match)
        relevant = [
            r for r in records
            if r.topic_type == topic_type
            or topic.lower() in r.topic.lower()
            or r.topic.lower() in topic.lower()
        ]

        if not relevant:
            relevant = records  # Use all history if no match

        # Score templates by time-decayed yield
        template_scores: dict[str, list[tuple[float, float]]] = {}
        for r in relevant:
            decay = self._compute_decay(r.timestamp)
            weighted_yield = r.knowledge_yield * decay
            for tmpl in r.templates:
                normalized = self._normalize_template(tmpl)
                if normalized not in template_scores:
                    template_scores[normalized] = []
                template_scores[normalized].append((weighted_yield, decay))

        if not template_scores:
            return self._fallback_suggestions(topic, topic_type, limit)

        # Compute average weighted score per template
        ranked = []
        for tmpl, scores in template_scores.items():
            total_weight = sum(s[1] for s in scores)
            if total_weight == 0:
                continue
            avg_yield = sum(s[0] for s in scores) / total_weight
            runs = len(scores)
            ranked.append((tmpl, avg_yield, runs))

        ranked.sort(key=lambda x: x[1], reverse=True)

        # Generate suggestions by substituting topic
        suggestions = []
        for tmpl, avg_yield, runs in ranked[:limit]:
            suggested = self._substitute_topic(tmpl, topic)
            if suggested and suggested not in [s.suggested_query for s in suggestions]:
                suggestions.append(ReformulationSuggestion(
                    suggested_query=suggested,
                    source_template=tmpl,
                    expected_yield=round(avg_yield, 3),
                    confidence=min(1.0, 0.5 + runs * 0.05),  # More runs = higher confidence
                    rationale=f"Template yielded {avg_yield:.2f} facts/query in {runs} run(s)",
                ))

        # Pad with fallbacks if needed
        if len(suggestions) < limit:
            fallbacks = self._fallback_suggestions(topic, topic_type, limit - len(suggestions))
            suggestions.extend(fallbacks)

        return suggestions[:limit]

    def get_top_templates(self, topic_type: str = "", limit: int = 5) -> list[dict]:
        """Get highest-yielding query templates."""
        records = self._load_records()
        if topic_type:
            records = [r for r in records if r.topic_type == topic_type]

        template_scores: dict[str, list[float]] = {}
        for r in records:
            for tmpl in r.templates:
                normalized = self._normalize_template(tmpl)
                template_scores.setdefault(normalized, []).append(r.knowledge_yield)

        ranked = []
        for tmpl, yields in template_scores.items():
            ranked.append({
                "template": tmpl,
                "avg_yield": round(sum(yields) / len(yields), 3),
                "runs": len(yields),
            })

        ranked.sort(key=lambda x: x["avg_yield"], reverse=True)
        return ranked[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Summary statistics for the yield database."""
        records = self._load_records()
        if not records:
            return {"total_records": 0, "message": "No yield data yet"}

        total_yield = sum(r.knowledge_yield for r in records)
        avg_yield = total_yield / len(records)
        mode_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        for r in records:
            mode_counts[r.mode] = mode_counts.get(r.mode, 0) + 1
            type_counts[r.topic_type] = type_counts.get(r.topic_type, 0) + 1

        return {
            "total_records": len(records),
            "avg_knowledge_yield": round(avg_yield, 3),
            "total_facts_extracted": sum(r.facts_count for r in records),
            "mode_distribution": mode_counts,
            "topic_type_distribution": type_counts,
            "best_mode": max(mode_counts, key=mode_counts.get) if mode_counts else None,
        }

    # ── Internal helpers ─────────────────────────────────────

    def _load_records(self) -> list[YieldRecord]:
        records = []
        if not self.yield_db_path.exists():
            return records
        with open(self.yield_db_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    records.append(YieldRecord(**d))
                except (json.JSONDecodeError, TypeError):
                    continue
        return records

    def _classify_topic_type(self, topic: str) -> str:
        topic_lower = topic.lower()
        scores = {}
        for ttype, keywords in TOPIC_TYPE_KEYWORDS.items():
            if not keywords:
                continue
            scores[ttype] = sum(1 for kw in keywords if kw in topic_lower)
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                return best
        return "general"

    def _compute_decay(self, timestamp_str: str) -> float:
        """Temporal decay: recent searches weighted higher.

        Formula: decay = 0.5^(days_ago / DECAY_DAYS)
        """
        try:
            ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except Exception:
            return 0.5  # Moderate decay for unparseable timestamps

        days_ago = (datetime.now(timezone.utc) - ts).total_seconds() / 86400
        return 0.5 ** (days_ago / self.DECAY_DAYS)

    def _normalize_template(self, template: str) -> str:
        """Normalize a query template for deduplication.

        Replace specific topic terms with placeholders.
        """
        # Simple normalization: lower, strip, collapse spaces
        tmpl = template.lower().strip()
        tmpl = re.sub(r"\s+", " ", tmpl)
        # Replace quoted phrases with placeholder
        tmpl = re.sub(r'"[^"]+"', '"{topic}"', tmpl)
        return tmpl

    def _substitute_topic(self, template: str, topic: str) -> str:
        """Substitute a topic into a template."""
        if "{topic}" in template:
            return template.replace("{topic}", topic)
        # If template has no placeholder, append topic
        return f"{topic} {template}"

    def _fallback_suggestions(
        self,
        topic: str,
        topic_type: str,
        limit: int,
    ) -> list[ReformulationSuggestion]:
        """Generic high-yield templates when no history exists."""
        fallbacks = {
            "research": [
                f'{topic} site:arxiv.org "survey"',
                f'{topic} "systematic review" 2025 2026',
                f'{topic} benchmark dataset comparison',
            ],
            "technical": [
                f'{topic} tutorial implementation github',
                f'{topic} best practices guide 2026',
                f'{topic} docs examples',
            ],
            "business": [
                f'{topic} market size revenue 2026',
                f'{topic} funding investment growth',
                f'{topic} competitor analysis strategy',
            ],
            "general": [
                f'{topic} latest news 2026',
                f'{topic} expert analysis opinion',
                f'{topic} comprehensive overview',
            ],
        }

        templates = fallbacks.get(topic_type, fallbacks["general"])
        suggestions = []
        for tmpl in templates[:limit]:
            suggestions.append(ReformulationSuggestion(
                suggested_query=tmpl,
                source_template="fallback",
                expected_yield=0.5,  # Neutral expectation
                confidence=0.3,
                rationale="Generic high-yield template (no historical data)",
            ))
        return suggestions
