# Rich Search Protocol: Optimizing PicoCloth for Deep Knowledge Discovery
**Date:** 2026-05-25  
**Philosophy:** Don't fight SEO. Out-search it.  
**Method:** Retrospective optimization of search patterns based on extraction yield.

---

## 1. The Insight

Anti-SEO is a losing battle. The winning strategy is **search sophistication**:
- Better queries → better sources → richer facts → higher confidence
- Track what works → double down → build institutional search memory

**Academic basis:** Information Foraging Theory (Pirolli & Card, 1999)
> "Experts don't forage randomly. They follow scent trails of high-yield patches."

Expert searchers (from JMIR 2025 study) focus on:
1. **External references** — dense citation = rich patch
2. **Publication dates** — recency signals active expertise
3. **Trusted URLs** — .edu, .gov, established institutions
4. **Scientometrics** — journal ranking, citation count, h-index

Our job: Encode these expert behaviors into PicoCloth's search protocol.

---

## 2. Retrospective Learning Loop

```
┌─────────────────────────────────────────────────────────────┐
│  SEARCH → EXTRACT → SCORE → LEARN → OPTIMIZE → REPEAT      │
│                                                             │
│  1. Search with query Q → get results R                     │
│  2. Extract facts from R → get facts F                      │
│  3. Score: avg_confidence(F), facts_per_result, tier_dist   │
│  4. Learn: which Q patterns yielded highest scores?         │
│  5. Optimize: update query templates, source priorities     │
│  6. Repeat with optimized Q'                                │
└─────────────────────────────────────────────────────────────┘
```

**Key metric:** `Knowledge Yield = facts_extracted × avg_confidence / search_cost`

This is tracked per query pattern and per source domain in `shared/memory/search-yield.jsonl`.

---

## 3. Query Optimization Patterns

### 3.1 Site-Specific Targeting (High-Yield Patches)

Instead of broad search, target known high-yield domains:

| Knowledge Type | Primary Patch | Query Pattern | Yield Boost |
|---------------|---------------|---------------|-------------|
| Academic research | arXiv, Google Scholar | `site:arxiv.org "topic" after:2024` | +40% |
| Technical deep-dives | GitHub, Hacker News | `site:github.com "topic" OR site:news.ycombinator.com` | +35% |
| Business intelligence | SEC, Crunchbase | `site:sec.gov "topic" OR site:crunchbase.com` | +30% |
| Government data | Census, WHO, BLS | `site:census.gov OR site:who.int "topic"` | +45% |
| Expert blogs | Self-hosted, RSS-enabled | `"topic" inurl:blog -site:medium.com -site:substack.com` | +25% |
| Primary sources | Court records, FOIA | `filetype:pdf "topic" site:gov` | +50% |

### 3.2 Query Expansion Strategy

**Step 1: Terminology Mapping**
```
User query: "AI agent market size"
↓
Academic terms: "autonomous agent", "LLM agent", "agentic system"
Business terms: "AI agent revenue", "agent platform TAM"
Technical terms: "agent framework adoption", "agent orchestration"
```

**Step 2: Parallel Query Execution**
Execute 3-5 variant queries simultaneously, then merge results.

**Step 3: Citation Chaining**
When a high-confidence fact is found, search for:
- `"author name" "topic"` — follow the expert
- Papers that cite the source — forward chaining
- Papers the source cites — backward chaining

### 3.3 Temporal Intelligence

```
Recent events:     after:2026-01-01
Historical trends: 2020..2024
Emerging field:    after:2024 (filter out outdated SEO content)
Established field: any time (classic papers matter)
```

### 3.4 Filetype Targeting

```
Research papers:   filetype:pdf
Datasets:          filetype:csv OR filetype:xlsx
Presentations:     filetype:pptx (conference slides often richer than articles)
Code:            site:github.com
Raw data:        filetype:json "topic"
```

---

## 4. Source Diversification Engine

### 4.1 Multi-Platform Search

Don't rely on one search engine. PicoCloth should query:

```python
SEARCH_PLATFORMS = {
    "general": "duckduckgo",        # Broad coverage, privacy-respecting
    "academic": "google_scholar",   # Peer-reviewed papers
    "technical": "hn_algolia",      # Hacker News discussions
    "social": "reddit_search",      # r/MachineLearning, r/programming
    "code": "github_search",        # Repos, issues, discussions
    "preprint": "arxiv_api",        # Latest research before peer review
    "business": "sec_edgar",        # SEC filings for public companies
    "archive": "wayback_machine",   # Historical versions of pages
}
```

### 4.2 Community-Driven Discovery

High-quality content often surfaces on:
- **Hacker News** — technical depth, expert commentary
- **Lobste.rs** — smaller, more curated than HN
- **Reddit niche subs** — r/MachineLearning, r/rust, r/homelab
- **GitHub issues/discussions** — living documentation, real problems
- **Stack Overflow** — practical, battle-tested knowledge
- **Specialist forums** — depending on domain

**Strategy:** Search these platforms DIRECTLY, not through Google.

### 4.3 Expert Blog Discovery

Instead of searching for topics, search for **experts who write about topics**:

```
"top experts in [topic]"
"best blogs about [topic]"
site:news.ycombinator.com "who writes about [topic]"
```

Then follow their:
- Personal blogs (self-hosted, not Medium/Substack)
- GitHub repos
- Twitter/X threads (for emerging thoughts)
- Conference talks (YouTube, but filter for actual talks not SEO videos)

---

## 5. Retrospective Yield Tracking

### 5.1 What to Track

Per search session:
```json
{
  "query": "AI agent market size 2026",
  "query_patterns": ["site:arxiv.org", "after:2025"],
  "sources_queried": ["duckduckgo", "hn_algolia"],
  "results_count": 15,
  "facts_extracted": 23,
  "avg_confidence": 0.72,
  "tier_distribution": {"1": 8, "2": 10, "3": 5},
  "top_yielding_domains": ["mckinsey.com", "arxiv.org", "github.com"],
  "knowledge_yield": 1.10,
  "timestamp": "2026-05-25T00:00:00Z"
}
```

### 5.2 How to Use Retrospective Data

**Weekly review:**
1. Which query patterns produced highest knowledge yield?
2. Which domains consistently produce high-confidence facts?
3. Which search platforms underperform for our use cases?

**Optimization:**
- Boost high-yield domains in future searches
- Deprioritize low-yield platforms (not anti-SEO — just efficiency)
- Create query templates from successful patterns
- Share findings across consultant nodes via MCP

---

## 6. Integration into PicoCloth

### 6.1 New CLI Commands

```bash
# Rich search with multi-platform diversification
picocloth search rich "AI agent market 2026" \
  --platforms academic,technical,business \
  --chain-citations \
  --extract --store

# Retrospective yield report
picocloth search report --last-week

# Query pattern suggestion based on topic
picocloth search suggest "blockchain consensus mechanisms"
```

### 6.2 THEE v1.2: Yield-Aware Extraction

```python
class YieldAwareExtractor:
    """Extracts facts while tracking source yield for retrospective optimization."""
    
    def extract(self, results, topic):
        facts = super().extract(results, topic)
        
        # Track yield
        yield_record = {
            "topic": topic,
            "results_count": len(results),
            "facts_count": len(facts),
            "avg_confidence": sum(f.confidence for f in facts) / len(facts),
            "domain_yield": self._compute_domain_yield(facts),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._append_yield_record(yield_record)
        
        return facts
```

### 6.3 Consultant Node Specialization

Each node maintains a **search strategy profile**:

```json
{
  "consultant-academic": {
    "preferred_platforms": ["arxiv", "google_scholar", "semantic_scholar"],
    "query_templates": [
      "site:arxiv.org \"{topic}\" after:{year}",
      "\"{topic}\" filetype:pdf citation"
    ],
    "expert_authors": ["Yoshua Bengio", "Yann LeCun"]
  },
  "consultant-growth": {
    "preferred_platforms": ["sec_edgar", "crunchbase", "pitchbook"],
    "query_templates": [
      "site:sec.gov \"{company}\" 10-K",
      "\"{topic}\" market size revenue"
    ]
  }
}
```

---

## 7. Why This Beats parallel-agent-skills

| Dimension | parallel-agent-skills | PicoCloth Rich Search |
|-----------|----------------------|----------------------|
| Search model | Single-engine, generic | Multi-platform, specialized |
| Query intelligence | User-provided only | Auto-expansion + template optimization |
| Source discovery | Passive (what search returns) | Active (target high-yield patches) |
| Learning | None | Retrospective yield tracking |
| Expert emulation | None | Information foraging theory encoded |
| Citation chaining | None | Forward + backward chaining |
| Cost optimization | Flat per-query | Yield-optimized (spend where it works) |

---

## 8. Citations

1. Pirolli, P. & Card, S. (1999). "Information Foraging." Psychological Review.
2. Schweiger, S. & Cress, U. (2019). "Attitude confidence and source credibility in information foraging." PLOS ONE.
3. JMIR (2025). "Multimodal Analysis of Online Information Foraging." e64901.
4. Schultheiß et al. (2022). "Does SEO correlate with quality?" ACM SIGIR CHIIR.
5. Bioptic Agent (2025). "Wide Search AI Agents." 79.7% F1 via completeness-oriented search.
