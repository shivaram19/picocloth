# Execution Plan: Gap 13 — Indie Web / Expert Blog Discovery

## Research Backing
- Schultheiß et al. (2022): "Non-optimized, but high-quality content may be outranked by optimized content." SEO dominates commercial search.
- Marginalia Search (Viktor Lofgren): Independent DIY search engine prioritizing "grass fed, free range HTML." Complements corporate search.
- "Searching the indieweb" (Dec 2025): Corporate web is doomed, indieweb thriving. Need tools to surface real people, real projects.
- SearXNG: Metasearch engine aggregating multiple sources. No tracking, self-hostable.

## File
`picocloth-cli/src/picocloth_cli/tools/indie_discovery.py`

---

## Step 4.1: Design `IndieSource` Data Model

```python
@dataclass
class IndieSource:
    name: str
    url: str
    domain: str
    category: str  # expert_blog, newsletter, academic_indie, self_hosted, community
    topics: list[str]  # e.g., ["ai", "ml", "systems"]
    rss_url: str = ""
    quality_score: float = 0.0  # 0.0-1.0 computed heuristics
    discovery_method: str = ""  # registry, hn_algolia, marginalia
    last_checked: str = ""
```

**Acceptance criteria**:
- [ ] Model serializes to/from JSON cleanly
- [ ] `quality_score` is computed, not stored as fixed value

---

## Step 4.2: Build Embedded Registry

**File**: `shared/doctrine/indie-web-registry.json`

**Initial categories**:
```json
{
  "expert_blogs": [
    {"name": "Paul Graham", "url": "http://paulgraham.com", "topics": ["startups", "programming"], "rss": "http://paulgraham.com/rss.html"},
    {"name": "Joel Spolsky", "url": "https://www.joelonsoftware.com", "topics": ["software", "business"], "rss": "..."},
    {"name": "Martin Fowler", "url": "https://martinfowler.com", "topics": ["architecture", "agile"], "rss": "..."},
    {"name": "Dan Luu", "url": "https://danluu.com", "topics": ["systems", "performance"], "rss": "..."},
    {"name": "Julia Evans", "url": "https://jvns.ca", "topics": ["systems", "learning"], "rss": "..."}
  ],
  "newsletters": [
    {"name": "TLDR", "url": "https://tldr.tech", "topics": ["tech", "ai"]},
    {"name": "Bytes", "url": "https://bytes.dev", "topics": ["javascript", "frontend"]}
  ],
  "academic_indies": [
    {"name": " distill.pub", "url": "https://distill.pub", "topics": ["ml", "visualization"]},
    {"name": "Papers We Love", "url": "https://paperswelove.org", "topics": ["research", "cs"]}
  ],
  "communities": [
    {"name": "Lobsters", "url": "https://lobste.rs", "topics": ["programming", "tech"]},
    {"name": "Hacker News", "url": "https://news.ycombinator.com", "topics": ["startups", "tech"]}
  ]
}
```

**Acceptance criteria**:
- [ ] Registry file is valid JSON
- [ ] At least 15 high-quality sources across categories
- [ ] Sources are genuinely indie/expert (not corporate blogs)

---

## Step 4.3: Write `IndieWebDiscoveryEngine`

**Class structure**:
```python
class IndieWebDiscoveryEngine:
    def __init__(self, registry_path: Path | None = None):
        self.registry = self._load_registry(registry_path)
    
    def discover(self, topic: str, limit: int = 10) -> list[IndieSource]:
        # 1. Search registry for topic matches
        # 2. Search HN Algolia for related discussions
        # 3. Score all sources by quality heuristics
        # 4. Return top N
        pass
    
    def search_hn(self, topic: str, limit: int = 5) -> list[IndieSource]:
        # Call HN Algolia API (no auth needed)
        # Filter for high-point stories
        # Convert to IndieSource objects
        pass
    
    def score_source(self, source: IndieSource) -> float:
        # Quality heuristics:
        # - Has RSS feed (+0.2)
        # - Old domain / no CDN tracking (+0.1)
        # - Plain HTML / no heavy JS (+0.2)
        # - Personal domain (+0.1)
        # - High engagement on HN (+0.2)
        # - Not on known corporate domain list (+0.2)
        pass
    
    def _load_registry(self, path: Path | None) -> dict:
        # Load JSON registry, fallback to embedded minimal set
        pass
```

**HN Algolia integration**:
```python
import urllib.request
import json

def search_hn(self, topic: str, limit: int = 5) -> list[IndieSource]:
    url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(topic)}&tags=story&numericFilters=points>10"
    req = urllib.request.Request(url, headers={"User-Agent": "PicoCloth-IndieDiscovery/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    sources = []
    for hit in data.get("hits", [])[:limit]:
        sources.append(IndieSource(
            name=hit.get("title", "Untitled"),
            url=hit.get("url", ""),
            domain=urllib.parse.urlparse(hit.get("url", "")).netloc,
            category="community",
            topics=[topic],
            discovery_method="hn_algolia",
            quality_score=min(1.0, hit.get("points", 0) / 100),
        ))
    return sources
```

**Acceptance criteria**:
- [ ] `discover()` returns sources from registry + HN
- [ ] `score_source()` returns 0.0-1.0
- [ ] HN search handles network errors gracefully
- [ ] `python3 -m py_compile indie_discovery.py` passes

---

## Step 4.4: Integrate with `SearchStrategyEngine`

**File**: `picocloth-cli/src/picocloth_cli/tools/search_strategy.py`

**Changes**:
1. Import `IndieWebDiscoveryEngine`
2. Add `plan_indie()` method:
```python
def plan_indie(self, topic: str, limit: int = 10) -> SearchPlan:
    """Build discovery plan targeting indie web sources."""
    engine = IndieWebDiscoveryEngine()
    sources = engine.discover(topic, limit)
    
    queries = []
    for src in sources:
        # Build site-specific search queries
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
    
    return SearchPlan(
        topic=topic,
        mode="indie",
        rationale=f"Indie web discovery: {len(sources)} expert sources identified",
        queries=queries,
        platforms=[s.domain for s in sources],
        terminology=[topic],
        expected_yield_tier=1,  # Indie sources are high-yield
    )
```

**Acceptance criteria**:
- [ ] `plan_indie()` returns `SearchPlan` with indie-specific queries
- [ ] Queries are site-targeted (`site:domain`)
- [ ] RSS feeds included when available

---

## Step 4.5: Add `discover` CLI Command

**File**: `picocloth-cli/src/picocloth_cli/commands/search.py`

**New command**:
```python
@app.command()
def discover(
    topic: str = typer.Argument(..., help="Topic to discover indie sources for"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max sources"),
    hn: bool = typer.Option(True, "--hn/--no-hn", help="Search Hacker News"),
    extract_facts: bool = typer.Option(False, "--extract", "-x", help="Extract facts from discovered sources"),
):
    """Discover expert blogs, newsletters, and indie web sources."""
    # 1. Create IndieWebDiscoveryEngine
    # 2. engine.discover(topic, limit, include_hn=hn)
    # 3. Display Rich table: Source | Category | Quality | Domain
    # 4. If --extract, run ExtractEngine on each source
```

**Rich display**:
- Header: "🔭 Indie Web Discovery: {topic}"
- Table: Name | Category | Quality | Domain | Topics
- Color coding: Green = quality > 0.7, Yellow = 0.4-0.7, Red = < 0.4
- Footer: "{N} sources found. Use --extract to pull facts."

**Acceptance criteria**:
- [ ] `picocloth search discover "distributed systems"` shows sources
- [ ] `--no-hn` skips HN search (faster)
- [ ] `--extract` runs extraction on discovered URLs
- [ ] Results can be piped to `extract from-file`

---

## Step 4.6: Register `fleet_discover` MCP Tool

**File**: `mcp-fleet-server/server.py`

**Add to `TOOLS`**:
```python
"fleet_discover": {
    "description": "Discover indie web sources for a topic",
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "limit": {"type": "integer", "default": 10}
        },
        "required": ["topic"]
    }
}
```

**Handler**: Read embedded registry, filter by topic, return sources.

**Acceptance criteria**:
- [ ] Returns JSON array of IndieSource dicts
- [ ] Works offline (uses embedded registry)

---

## Step 4.7: Skill Documentation

**File**: `shared/doctrine/skills/indie-discovery.md`

**Contents**:
- Schultheiß et al. SEO vs quality findings
- Marginalia Search philosophy
- Quality heuristics explained
- Registry curation guidelines
- CLI usage: `search discover`, `--extract`, `--no-hn`

**Acceptance criteria**:
- [ ] Document explains WHY indie sources matter
- [ ] Quality scoring rubric documented
- [ ] Contributing guide for adding new sources to registry

---

## Step 4.8: Test & Commit

**Test commands**:
```bash
cd /Users/shivaramgoud/picocloth-work
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/indie_discovery.py
python3 -c "
from picocloth_cli.tools.indie_discovery import IndieWebDiscoveryEngine
engine = IndieWebDiscoveryEngine()
sources = engine.discover('python', limit=3)
print(f'Found {len(sources)} sources')
for s in sources:
    print(f'  {s.name} ({s.domain}) - score: {s.quality_score}')
"
```

**Commit message**:
```
feat(discovery): Indie Web Discovery Engine v1.0

- Expert blog registry with 15+ high-quality indie sources
- HN Algolia integration for community-discovered content
- Quality heuristics: RSS, plain HTML, domain age, engagement
- Site-targeted search queries (site:domain)
- CLI: search discover --extract --no-hn
- MCP: fleet_discover tool registered

Research: Schultheiß et al. (2022), Marginalia Search,
IndieWeb community, SearXNG
```
