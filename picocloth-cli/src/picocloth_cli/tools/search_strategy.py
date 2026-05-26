"""
PicoCloth Search Strategy Engine
================================
Three modes of discovery, encoded from first principles:

  CLEVERLY   → Query optimization, pattern recognition, platform intelligence
  CURIOUSLY  → Exploratory branching, scent-following, serendipitous discovery  
  TARGETEDLY → Precision strikes: site, filetype, author, date, exact phrase

Citations:
  - Pirolli & Card (1999): Information Foraging Theory
  - Schweiger & Cress (2019): Expert vs novice search behavior
  - Bioptic Agent (2025): Completeness-oriented search control
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)

# ── Platform Registry ────────────────────────────────────────
# High-yield patches per knowledge type. Experts don't search randomly;
# they go directly to where the prey congregates.

PLATFORM_REGISTRY = {
    # Academic knowledge
    "arxiv": {
        "base_url": "https://arxiv.org/search/?query={query}&searchtype=all",
        "api_url": "http://export.arxiv.org/api/query?search_query={query}&start=0&max_results={limit}",
        "best_for": ["research", "technical", "cutting_edge"],
        "yield_tier": 1,
    },
    "google_scholar": {
        "base_url": "https://scholar.google.com/scholar?q={query}",
        "best_for": ["peer_reviewed", "citations", "academic"],
        "yield_tier": 1,
    },
    "semantic_scholar": {
        "base_url": "https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit={limit}",
        "best_for": ["research", "citation_chaining", "related_work"],
        "yield_tier": 1,
    },
    # Technical knowledge
    "hn_algolia": {
        "base_url": "https://hn.algolia.com/?q={query}",
        "api_url": "https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage={limit}",
        "best_for": ["technical", "practical", "community_validated"],
        "yield_tier": 1,
    },
    "github": {
        "base_url": "https://github.com/search?q={query}&type=repositories",
        "api_url": "https://api.github.com/search/repositories?q={query}&per_page={limit}",
        "best_for": ["code", "implementation", "open_source"],
        "yield_tier": 2,
    },
    "stackoverflow": {
        "base_url": "https://stackoverflow.com/search?q={query}",
        "best_for": ["practical", "bug_fixes", "how_to"],
        "yield_tier": 2,
    },
    # Business intelligence
    "sec_edgar": {
        "base_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=10-K",
        "api_url": "https://www.sec.gov/Archives/edgar/daily-index/form-idx",
        "best_for": ["financial", "public_company", "regulatory"],
        "yield_tier": 1,
    },
    "crunchbase": {
        "base_url": "https://www.crunchbase.com/discover/{query}",
        "best_for": ["startup", "funding", "market_map"],
        "yield_tier": 2,
    },
    # Government / primary
    "census": {
        "base_url": "https://data.census.gov/search?q={query}",
        "best_for": ["demographics", "economic_data", "us_statistics"],
        "yield_tier": 1,
    },
    "who": {
        "base_url": "https://www.who.int/search?q={query}",
        "best_for": ["health", "global_health", "epidemiology"],
        "yield_tier": 1,
    },
    # General
    "duckduckgo": {
        "base_url": "https://duckduckgo.com/?q={query}",
        "best_for": ["general", "news", "broad_discovery"],
        "yield_tier": 2,
    },
}

# ── Query Templates ──────────────────────────────────────────
# Pre-optimized patterns derived from expert search behavior research.

QUERY_TEMPLATES = {
    # ── CLEVERLY: Pattern-optimized queries ──────────────────
    "clever": {
        "academic_discovery": [
            "site:arxiv.org \"{topic}\" after:{year}",
            "\"{topic}\" filetype:pdf site:arxiv.org OR site:openreview.net",
            "\"{topic}\" inurl:paper OR inurl:publication",
        ],
        "technical_practical": [
            "site:github.com \"{topic}\" stars:>100",
            "site:news.ycombinator.com \"{topic}\"",
            "\"{topic}\" site:stackoverflow.com is:question score:>10",
        ],
        "business_intelligence": [
            "site:sec.gov \"{company}\" 10-K OR 10-Q",
            "\"{topic}\" market size revenue CAGR filetype:pdf",
            "site:crunchbase.com \"{company}\" funding",
        ],
        "expert_opinion": [
            "\"{topic}\" interview OR \"thoughts on\" OR \"lessons learned\"",
            "\"{topic}\" criticism OR limitations OR \"what went wrong\"",
            "site:news.ycombinator.com \"{topic}\" comments",
        ],
    },
    # ── CURIOUSLY: Exploratory, scent-following queries ──────
    "curious": {
        "adjacent_concepts": [
            "\"{topic}\" related to OR compared with OR alternative",
            "\"{topic}\" history evolution timeline",
            "\"{topic}\" unexpected use case OR hack OR workaround",
        ],
        "people_and_stories": [
            "who created \"{topic}\" OR who invented \"{topic}\"",
            "\"{topic}\" founder story OR origin story",
            "\"{topic}\" controversy OR debate OR disagreement",
        ],
        "cross_domain": [
            "\"{topic}\" applied to healthcare OR finance OR education",
            "\"{topic}\" interdisciplinary OR cross-functional",
            "\"{topic}\" unexpected industry OR sector",
        ],
        "emerging_signals": [
            "\"{topic}\" 2026 OR \"upcoming\" OR \"next generation\"",
            "\"{topic}\" twitter thread OR blog post OR newsletter",
            "\"{topic}\" github trending OR new repository",
        ],
    },
    # ── TARGETEDLY: Precision strikes ────────────────────────
    "targeted": {
        "exact_phrase": [
            "\"{exact_phrase}\"",
            "\"{exact_phrase}\" -site:pinterest.com -site:medium.com",
        ],
        "site_specific": [
            "site:{domain} \"{topic}\"",
            "site:{domain} \"{topic}\" filetype:pdf",
        ],
        "author_specific": [
            "\"{author}\" \"{topic}\"",
            "author:\"{author}\" \"{topic}\"",
        ],
        "date_bounded": [
            "\"{topic}\" after:{start_date} before:{end_date}",
            "\"{topic}\" {year}",
        ],
        "filetype_specific": [
            "\"{topic}\" filetype:pdf",
            "\"{topic}\" filetype:pptx OR filetype:ppt",
            "\"{topic}\" filetype:csv OR filetype:xlsx",
        ],
        "citation_chaining": [
            "\"{paper_title}\" citations",
            "papers that cite \"{paper_title}\"",
            "related:arxiv.org/abs/{arxiv_id}",
        ],
    },
}

# ── Terminology Expansion ────────────────────────────────────
# Map lay terms to expert terminology for cross-domain discovery.

TERMINOLOGY_MAP = {
    "AI agent": ["autonomous agent", "LLM agent", "agentic system", "AI assistant", "cognitive agent"],
    "market size": ["TAM", "SAM", "SOM", "market revenue", "industry valuation", "addressable market"],
    "growth": ["CAGR", "growth rate", "expansion", "scaling", "trajectory"],
    "startup": ["early-stage company", "venture-backed", "seed stage", "Series A", "unicorn"],
    "blockchain": ["distributed ledger", "consensus mechanism", "smart contract", "DeFi", "Web3"],
    "cloud": ["IaaS", "PaaS", "SaaS", "serverless", "container orchestration"],
}


@dataclass
class SearchPlan:
    """A structured plan for multi-platform knowledge discovery."""
    topic: str
    mode: str  # clever, curious, targeted, or hybrid
    queries: list[dict] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    expected_yield_tier: int = 2
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "mode": self.mode,
            "queries": self.queries,
            "platforms": self.platforms,
            "expected_yield_tier": self.expected_yield_tier,
            "rationale": self.rationale,
        }


class SearchStrategyEngine:
    """Builds optimized search plans based on topic and discovery mode."""

    def __init__(self, yield_db_path: Path | None = None) -> None:
        self.yield_db_path = yield_db_path or Path("shared/memory/search-yield.jsonl")
        self.yield_db_path.parent.mkdir(parents=True, exist_ok=True)

    # ── CLEVERLY: Pattern-optimized search ───────────────────

    def plan_clever(self, topic: str, knowledge_type: str = "general") -> SearchPlan:
        """Build a clever search plan: optimized patterns for high-yield discovery."""
        templates = QUERY_TEMPLATES["clever"]
        year = datetime.now(timezone.utc).year

        # Select template set based on knowledge type
        if knowledge_type in ("research", "technical", "academic"):
            template_set = templates["academic_discovery"] + templates["technical_practical"]
            platforms = ["arxiv", "google_scholar", "hn_algolia", "github"]
        elif knowledge_type in ("business", "market", "financial"):
            template_set = templates["business_intelligence"]
            platforms = ["sec_edgar", "crunchbase", "duckduckgo"]
        else:
            template_set = (
                templates["academic_discovery"][:1]
                + templates["technical_practical"][:1]
                + templates["expert_opinion"]
            )
            platforms = ["duckduckgo", "hn_algolia", "arxiv"]

        # Expand terminology
        expanded_terms = self._expand_terms(topic)

        queries = []
        for template in template_set:
            for term in expanded_terms[:3]:  # Top 3 variations
                q = template.format(topic=term, year=year, company=term)
                queries.append({
                    "query": q,
                    "template": template,
                    "term_variant": term,
                    "platform": platforms[0],
                    "rationale": f"Clever pattern: {self._describe_template(template)}",
                })

        return SearchPlan(
            topic=topic,
            mode="clever",
            queries=queries[:6],  # Cap to avoid cost explosion
            platforms=platforms,
            expected_yield_tier=1,
            rationale=f"Clever mode: Using pattern-optimized queries across {len(platforms)} platforms with {len(expanded_terms)} term variations.",
        )

    # ── CURIOUSLY: Exploratory discovery ─────────────────────

    def plan_curious(self, topic: str, depth: int = 2) -> SearchPlan:
        """Build a curious search plan: exploratory, scent-following, serendipitous."""
        templates = QUERY_TEMPLATES["curious"]
        year = datetime.now(timezone.utc).year

        queries = []

        # Adjacent concepts
        for template in templates["adjacent_concepts"]:
            q = template.format(topic=topic, year=year)
            queries.append({
                "query": q,
                "template": template,
                "discovery_vector": "adjacent",
                "platform": "duckduckgo",
                "rationale": "Curious: Find what lives next to this topic",
            })

        # People and stories
        for template in templates["people_and_stories"]:
            q = template.format(topic=topic)
            queries.append({
                "query": q,
                "template": template,
                "discovery_vector": "human",
                "platform": "duckduckgo",
                "rationale": "Curious: Find the people behind the topic",
            })

        # Cross-domain
        for template in templates["cross_domain"]:
            q = template.format(topic=topic)
            queries.append({
                "query": q,
                "template": template,
                "discovery_vector": "cross_domain",
                "platform": "duckduckgo",
                "rationale": "Curious: Find unexpected applications",
            })

        # Emerging signals (technical communities)
        for template in templates["emerging_signals"]:
            q = template.format(topic=topic, year=year)
            queries.append({
                "query": q,
                "template": template,
                "discovery_vector": "emerging",
                "platform": "hn_algolia",
                "rationale": "Curious: Find what's happening NOW",
            })

        return SearchPlan(
            topic=topic,
            mode="curious",
            queries=queries,
            platforms=["duckduckgo", "hn_algolia"],
            expected_yield_tier=2,
            rationale="Curious mode: Exploratory vectors — adjacent, human, cross-domain, emerging — to find what structured search misses.",
        )

    # ── TARGETEDLY: Precision strikes ────────────────────────

    def plan_targeted(
        self,
        topic: str,
        exact_phrase: str | None = None,
        domain: str | None = None,
        author: str | None = None,
        date_range: tuple[str, str] | None = None,
        filetype: str | None = None,
    ) -> SearchPlan:
        """Build a targeted search plan: precision strikes on known high-value targets."""
        templates = QUERY_TEMPLATES["targeted"]
        year = datetime.now(timezone.utc).year

        queries = []
        platforms = []

        if exact_phrase:
            for template in templates["exact_phrase"]:
                q = template.format(exact_phrase=exact_phrase, topic=topic)
                queries.append({
                    "query": q,
                    "template": template,
                    "precision_type": "exact_phrase",
                    "platform": "duckduckgo",
                    "rationale": f"Targeted: Exact phrase '{exact_phrase}'",
                })

        if domain:
            for template in templates["site_specific"]:
                q = template.format(domain=domain, topic=topic)
                queries.append({
                    "query": q,
                    "template": template,
                    "precision_type": "site",
                    "platform": domain.split(".")[0] if "." in domain else "duckduckgo",
                    "rationale": f"Targeted: Site-specific on {domain}",
                })
            platforms.append("custom")

        if author:
            for template in templates["author_specific"]:
                q = template.format(author=author, topic=topic)
                queries.append({
                    "query": q,
                    "template": template,
                    "precision_type": "author",
                    "platform": "google_scholar",
                    "rationale": f"Targeted: Following author '{author}'",
                })
            platforms.append("google_scholar")

        if date_range:
            start, end = date_range
            for template in templates["date_bounded"]:
                q = template.format(topic=topic, start_date=start, end_date=end, year=start[:4])
                queries.append({
                    "query": q,
                    "template": template,
                    "precision_type": "date",
                    "platform": "duckduckgo",
                    "rationale": f"Targeted: Date-bounded {start} to {end}",
                })

        if filetype:
            for template in templates["filetype_specific"]:
                q = template.format(topic=topic)
                queries.append({
                    "query": q,
                    "template": template,
                    "precision_type": "filetype",
                    "platform": "duckduckgo",
                    "rationale": f"Targeted: Filetype {filetype}",
                })

        return SearchPlan(
            topic=topic,
            mode="targeted",
            queries=queries,
            platforms=platforms or ["duckduckgo"],
            expected_yield_tier=1,
            rationale=f"Targeted mode: {len(queries)} precision strikes using exact phrase, site, author, date, or filetype constraints.",
        )

    # ── HYBRID: The Full Stack ───────────────────────────────

    def plan_hybrid(self, topic: str, knowledge_type: str = "general") -> list[SearchPlan]:
        """Build all three plans and execute them in optimal order."""
        return [
            self.plan_targeted(topic),           # 1. Precision first (cheapest)
            self.plan_clever(topic, knowledge_type),  # 2. Pattern optimization
            self.plan_curious(topic),            # 3. Exploratory sweep
        ]

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _expand_terms(topic: str) -> list[str]:
        """Expand topic with expert terminology variants."""
        terms = [topic]
        for key, variants in TERMINOLOGY_MAP.items():
            if key.lower() in topic.lower():
                for v in variants:
                    terms.append(topic.lower().replace(key.lower(), v))
        return terms[:5]

    @staticmethod
    def _describe_template(template: str) -> str:
        """Human-readable description of a query template."""
        if "site:" in template:
            return "site-specific targeting"
        if "filetype:" in template:
            return "document type filtering"
        if "after:" in template:
            return "recency-bounded"
        if "author:" in template or "who" in template:
            return "author/expert following"
        if "OR" in template:
            return "multi-source union"
        return "keyword optimization"

    # ── Yield Tracking ───────────────────────────────────────

    def record_yield(self, plan: SearchPlan, results_count: int, facts_count: int, avg_confidence: float) -> None:
        """Record search yield for retrospective optimization."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "topic": plan.topic,
            "mode": plan.mode,
            "platforms": plan.platforms,
            "queries_count": len(plan.queries),
            "results_count": results_count,
            "facts_count": facts_count,
            "avg_confidence": avg_confidence,
            "knowledge_yield": round(facts_count * avg_confidence / max(1, len(plan.queries)), 3),
        }
        with open(self.yield_db_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def get_top_yielding_patterns(self, topic_prefix: str = "", limit: int = 5) -> list[dict]:
        """Get the highest-yielding search patterns from retrospective data."""
        if not self.yield_db_path.exists():
            return []

        records = []
        with open(self.yield_db_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    if not topic_prefix or topic_prefix.lower() in r.get("topic", "").lower():
                        records.append(r)
                except json.JSONDecodeError:
                    continue

        # Group by mode, compute average yield
        mode_stats: dict[str, dict] = {}
        for r in records:
            mode = r["mode"]
            if mode not in mode_stats:
                mode_stats[mode] = {"total_yield": 0, "count": 0, "avg_confidence": 0}
            mode_stats[mode]["total_yield"] += r.get("knowledge_yield", 0)
            mode_stats[mode]["count"] += 1
            mode_stats[mode]["avg_confidence"] += r.get("avg_confidence", 0)

        ranked = []
        for mode, stats in mode_stats.items():
            if stats["count"] > 0:
                ranked.append({
                    "mode": mode,
                    "avg_yield": round(stats["total_yield"] / stats["count"], 3),
                    "avg_confidence": round(stats["avg_confidence"] / stats["count"], 3),
                    "runs": stats["count"],
                })

        ranked.sort(key=lambda x: x["avg_yield"], reverse=True)
        return ranked[:limit]
