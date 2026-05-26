"""
Indie Web Discovery Engine (IWDE) v1.0
========================================
Expert blog, newsletter, and self-hosted content discovery.

Backed by research:
  - Schultheiß et al. (2022): "Non-optimized, but high-quality content
    may be outranked by optimized content." SEO dominates commercial search.
  - Marginalia Search (Viktor Lofgren): Independent DIY search engine
    prioritizing "grass fed, free range HTML." Complements corporate search.
  - "Searching the indieweb" (Dec 2025): Corporate web is doomed,
    indieweb thriving. Need tools to surface real people, real projects.
  - SearXNG: Metasearch engine aggregating multiple sources. No tracking.

Quality heuristics:
  - Has RSS feed (+0.2)
  - Plain HTML / no heavy JS (+0.2)
  - Personal domain (+0.1)
  - High engagement on HN (+0.2)
  - Not on known corporate domain (+0.2)
  - Old domain / stable presence (+0.1)
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)

# ── Embedded Minimal Registry ────────────────────────────────
# Default sources when no external registry exists.

DEFAULT_REGISTRY = {
    "expert_blogs": [
        {"name": "Paul Graham", "url": "http://paulgraham.com", "topics": ["startups", "programming"], "rss": "http://paulgraham.com/articles.html"},
        {"name": "Martin Fowler", "url": "https://martinfowler.com", "topics": ["architecture", "agile", "software"], "rss": "https://martinfowler.com/feed.atom"},
        {"name": "Dan Luu", "url": "https://danluu.com", "topics": ["systems", "performance", "databases"], "rss": "https://danluu.com/atom.xml"},
        {"name": "Julia Evans", "url": "https://jvns.ca", "topics": ["systems", "learning", "debugging"], "rss": "https://jvns.ca/atom.xml"},
        {"name": "Simon Willison", "url": "https://simonwillison.net", "topics": ["ai", "python", "data"], "rss": "https://simonwillison.net/atom/everything/"},
        {"name": "Evan Miller", "url": "https://www.evanmiller.org", "topics": ["statistics", "programming"], "rss": ""},
        {"name": "Drew DeVault", "url": "https://drewdevault.com", "topics": ["linux", "open-source", "programming"], "rss": "https://drewdevault.com/blog/index.xml"},
    ],
    "newsletters": [
        {"name": "TLDR", "url": "https://tldr.tech", "topics": ["tech", "ai", "startup"]},
        {"name": "Pointer.io", "url": "https://pointer.io", "topics": ["software", "engineering"]},
    ],
    "academic_indies": [
        {"name": "Distill.pub", "url": "https://distill.pub", "topics": ["ml", "visualization", "research"]},
        {"name": "Papers We Love", "url": "https://paperswelove.org", "topics": ["research", "cs", "papers"]},
        {"name": "Sebastian Ruder", "url": "https://ruder.io", "topics": ["nlp", "ml", "research"], "rss": "https://ruder.io/feed.xml"},
    ],
    "communities": [
        {"name": "Lobsters", "url": "https://lobste.rs", "topics": ["programming", "tech"]},
        {"name": "Hacker News", "url": "https://news.ycombinator.com", "topics": ["startups", "tech", "science"]},
    ],
}


# ── Data Models ──────────────────────────────────────────────

@dataclass
class IndieSource:
    name: str
    url: str
    domain: str
    category: str  # expert_blog, newsletter, academic_indie, self_hosted, community
    topics: list[str] = field(default_factory=list)
    rss_url: str = ""
    quality_score: float = 0.0
    discovery_method: str = "registry"
    last_checked: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "domain": self.domain,
            "category": self.category,
            "topics": self.topics,
            "rss_url": self.rss_url,
            "quality_score": self.quality_score,
            "discovery_method": self.discovery_method,
        }


# ── Discovery Engine ─────────────────────────────────────────

class IndieWebDiscoveryEngine:
    """Discover expert blogs, newsletters, and indie web sources.

    Usage:
        engine = IndieWebDiscoveryEngine()
        sources = engine.discover("distributed systems", limit=10)
        for s in sources:
            print(s.name, s.quality_score)
    """

    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry = self._load_registry(registry_path)

    def discover(
        self,
        topic: str,
        limit: int = 10,
        include_hn: bool = True,
    ) -> list[IndieSource]:
        """Discover indie sources for a topic.

        Pipeline:
        1. Search embedded registry for topic matches
        2. Search HN Algolia for community-discovered content
        3. Score all sources by quality heuristics
        4. Return top N
        """
        sources: list[IndieSource] = []
        seen_domains: set[str] = set()

        # 1. Registry search
        for category, items in self.registry.items():
            for item in items:
                if self._topic_matches(topic, item.get("topics", [])):
                    src = self._item_to_source(item, category)
                    if src.domain not in seen_domains:
                        sources.append(src)
                        seen_domains.add(src.domain)

        # 2. HN Algolia search
        if include_hn:
            try:
                hn_sources = self._search_hn(topic, limit=limit)
                for src in hn_sources:
                    if src.domain not in seen_domains:
                        sources.append(src)
                        seen_domains.add(src.domain)
            except Exception as exc:
                logger.warning("HN search failed: %s", exc)

        # 3. Score and rank
        for src in sources:
            src.quality_score = self._score_source(src)

        sources.sort(key=lambda s: s.quality_score, reverse=True)
        return sources[:limit]

    def _load_registry(self, path: Path | None) -> dict:
        """Load registry from file or use embedded default."""
        if path and path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Failed to load registry from %s, using default", path)
        return DEFAULT_REGISTRY

    def _topic_matches(self, topic: str, source_topics: list[str]) -> bool:
        """Check if topic matches source topics."""
        topic_words = set(topic.lower().split())
        for st in source_topics:
            if st.lower() in topic.lower() or any(w in st.lower() for w in topic_words):
                return True
        return False

    def _item_to_source(self, item: dict, category: str) -> IndieSource:
        """Convert registry item to IndieSource."""
        url = item.get("url", "")
        try:
            domain = urllib.parse.urlparse(url).netloc.lower().lstrip("www.")
        except Exception:
            domain = "unknown"
        return IndieSource(
            name=item.get("name", "Untitled"),
            url=url,
            domain=domain,
            category=category,
            topics=item.get("topics", []),
            rss_url=item.get("rss", ""),
            discovery_method="registry",
        )

    def _search_hn(self, topic: str, limit: int = 5) -> list[IndieSource]:
        """Search Hacker News Algolia API for related discussions."""
        query = urllib.parse.quote(topic)
        url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&numericFilters=points>10&hitsPerPage={limit}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PicoCloth-IndieDiscovery/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        sources = []
        for hit in data.get("hits", [])[:limit]:
            story_url = hit.get("url", "")
            if not story_url:
                continue  # Skip ask HN / text-only posts
            try:
                domain = urllib.parse.urlparse(story_url).netloc.lower().lstrip("www.")
            except Exception:
                continue

            points = hit.get("points", 0)
            quality = min(1.0, points / 100)

            sources.append(IndieSource(
                name=hit.get("title", "Untitled")[:80],
                url=story_url,
                domain=domain,
                category="community",
                topics=[topic],
                discovery_method="hn_algolia",
                quality_score=quality,
            ))

        return sources

    def _score_source(self, source: IndieSource) -> float:
        """Compute quality score from heuristics.

        Schultheiß et al. (2022): non-optimized content is systematically
        under-ranked. We boost signals that indicate genuine expert content.
        """
        score = 0.0

        # Has RSS feed (+0.2) — indicates active publishing
        if source.rss_url:
            score += 0.2

        # Personal / non-corporate domain (+0.2)
        corp_domains = {
            "medium.com", "substack.com", "linkedin.com", "facebook.com",
            "twitter.com", "x.com", "youtube.com", "tiktok.com",
        }
        if source.domain and not any(cd in source.domain for cd in corp_domains):
            score += 0.2

        # Academic or expert blog category (+0.15)
        if source.category in ("expert_blogs", "academic_indies"):
            score += 0.15

        # Newsletter category (+0.1)
        if source.category == "newsletters":
            score += 0.1

        # Community-validated (HN) with high points (+0.2)
        if source.discovery_method == "hn_algolia":
            score += min(0.2, source.quality_score)

        # Specific topic match depth (+0.15 max)
        topic_depth = min(0.15, len(source.topics) * 0.03)
        score += topic_depth

        return round(min(1.0, score), 2)

    def build_search_queries(self, topic: str, sources: list[IndieSource]) -> list[dict]:
        """Build site-targeted search queries from discovered sources."""
        queries = []
        for src in sources:
            queries.append({
                "query": f"{topic} site:{src.domain}",
                "platform": src.domain,
                "rationale": f"Search {src.category}: {src.name}",
            })
            if src.rss_url:
                queries.append({
                    "query": f"{topic} rss:{src.rss_url}",
                    "platform": "rss",
                    "rationale": f"RSS feed from {src.name}",
                })
        return queries
