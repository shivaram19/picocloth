# Steering PicoCloth: From SEO Surface to Rich Knowledge Depth
**Date:** 2026-05-25  
**Research scope:** parallel-agent-skills deep-dive + anti-SEO academic research + indie web discovery  
**Status:** ACTIVE STEERING — implementation in progress

---

## 1. The Problem: The Web is SEO-Poisoned

### Academic Evidence
**Schultheiß, Häußler & Lewandowski (2022)** — ACM SIGIR CHIIR:
> "Since non-optimized, but high-quality content may be outranked by optimized content of lower quality, trusted sources should be prioritized in rankings."

Participants rated **non-optimized pages as higher expertise** than SEO-optimized pages. The non-optimized pages were described as "more competent and reputable."

**Information Foraging Theory** (Pirolli & Card, 1999; extended by Schweiger & Cress, 2019):
- Experts engage with **fewer credibility cues but with higher frequency**
- Key cues: **external references, publication dates, trusted URLs, scientometrics**
- Experts focus on **academic patches** and transition between search engines and academic sources
- Novices wander across low-cue patches and get distracted by ads/clickbait

### The SEO Trap
Modern search engines surface:
- Content farms (Medium, generic "ultimate guides")
- Affiliate marketing posts disguised as reviews
- LLM-generated SEO slop (increasingly common in 2025-2026)
- Aggregator sites that add zero original insight
- Press releases repackaged as "news"

What they BURY:
- Personal expert blogs with years of deep expertise
- Academic preprints (arXiv, bioRxiv, SSRN)
- GitHub repos with living documentation
- Government primary sources (SEC, Census, WHO)
- Niche newsletters and specialist forums
- The "indie web" — self-hosted, non-commercial content

### parallel-agent-skills: What They Got Wrong
After deep-dive into https://github.com/parallel-web/parallel-agent-skills:

| Capability | parallel-agent-skills | What They Miss |
|------------|----------------------|----------------|
| **Search** | `parallel-cli search` — generic web | No anti-SEO filtering, no indie web discovery |
| **Extract** | `parallel-cli extract` — raw page text | No structured fact extraction, no triples |
| **Deep Research** | `parallel-cli research` — narrative report | No atomic fact decomposition, no verifiable claims |
| **Verify** | None | No cross-reference, no corroboration scoring |
| **Memory** | None | No persistence between queries |
| **Multi-agent** | None | Single-agent pipeline only |
| **Source quality** | `--exclude-domains` manual | No automatic content farm detection |
| **Cost model** | Commercial SaaS, per-query billing | Not fleet-native, not MCP-integrated |
| **Citation** | Inline markdown links | No structured provenance, no confidence scores |
| **Temporal** | `--after-date` only | No fact validity windows, no supersession tracking |

**Their core error:** They built a faster search wrapper, not a knowledge discovery engine.

---

## 2. The Solution: PicoCloth Rich Knowledge Protocol

### Philosophy
> "Don't search the web. Forage for knowledge."

SEO-optimized content is designed for **algorithms**. Rich knowledge is designed for **humans**.
Our job is to build signals that detect human-designed content and deprioritize algorithm-designed content.

### The 7 Signals of Rich Knowledge

Based on research synthesis:

| Signal | SEO Content | Rich Knowledge | Detection Method |
|--------|-------------|----------------|------------------|
| **1. Authorship** | Anonymous or ghostwritten | Named expert with credentials | Author extraction + domain expertise check |
| **2. Citations** | Few or self-referential | Dense external references | Reference count + outbound domain diversity |
| **3. Date freshness** | Updated date manipulated | Clear publication + revision dates | Date consistency check |
| **4. Commercial intent** | Affiliate links, CTAs everywhere | No monetization, pure knowledge | Link pattern analysis |
| **5. Depth vs length** | Long but shallow (2000+ words of fluff) | Dense, technical, assumes expertise | Information density score |
| **6. Community validation** | Bot comments, fake engagement | Hacker News, Lobste.rs, specialist forum links | Backlink source analysis |
| **7. Indie web markers** | Corporate CMS, cookie banners | Self-hosted, RSS feeds, webmentions | Domain tech fingerprint |

### Content Farm Detection Heuristics

```python
CONTENT_FARM_SIGNALS = {
    "high_ad_density": "Detect excessive ad slots vs content ratio",
    "affiliate_link_density": "Amazon/affiliate links per 1000 words",
    "listicle_structure": "X Ways to Y, Ultimate Guide patterns",
    "placeholder_text": "Lorem ipsum, boilerplate intros",
    "duplicate_fragments": "Same paragraph across multiple articles",
    "low_external_citation": "<2 outbound links to non-affiliate sources",
    "author_profile_missing": "No author bio or generic 'Editorial Team'",
    "cookie_banner_complexity": "Massive consent dialog = corporate tracking",
}
```

### Rich Source Boost Heuristics

```python
RICH_SOURCE_BOOST = {
    "self_hosted": "No WordPress.com, Medium, Substack subdomain",
    "rss_available": "RSS/Atom feed detected at /feed, /rss",
    "webmentions": "Webmention.io or similar indie web protocol",
    "https_plus": "HTTPS + HSTS + strong TLS (signals technical care)",
    "academic_domain": ".edu, .ac.uk, arxiv.org, pubmed",
    "government_domain": ".gov, who.int, sec.gov",
    "github_source": "github.com with README + commits + issues",
    "hacker_news_refs": "Referenced on news.ycombinator.com",
    "age_of_domain": ">5 years old via WHOIS",
    "archive_presence": "Multiple captures on web.archive.org",
}
```

---

## 3. Implementation: Anti-SEO THEE v1.1

### Tier 1 Enhancement: Quality-Weighted Regex
Current THEE v1.0 extracts facts from all sources equally.
v1.1 adds **source quality pre-filtering**:

```
Search Results
    │
    ▼
┌─────────────────────────────┐
│ SOURCE QUALITY CLASSIFIER   │
│ ├─ Content farm? → DEPRIORITIZE (-0.3 confidence)  │
│ ├─ Indie web? → BOOST (+0.2 confidence)            │
│ ├─ Academic? → BOOST (+0.15 confidence)            │
│ └─ Government? → BOOST (+0.15 confidence)          │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ FACT EXTRACTION (THEE)      │
└─────────────────────────────┘
```

### Tier 3 NEW: Rich Source Discovery
A dedicated discovery layer that FINDS sources before extraction:

```bash
picocloth discover rich "AI agent architectures 2026"
```

This command:
1. Searches DuckDuckGo
2. Queries Hacker News Algolia API for related discussions
3. Checks arXiv for recent preprints
4. Scans GitHub trending repos
5. Searches specialist subreddits (r/MachineLearning)
6. Returns a **curated source list** ranked by rich-knowledge signals

### Fleet Multi-Agent Discovery
Each consultant node specializes in a discovery channel:

| Node | Discovery Channel | Why |
|------|-------------------|-----|
| consultant-academic | arXiv, Google Scholar, Semantic Scholar | Research papers |
| consultant-growth | Crunchbase, PitchBook, SEC filings | Business intelligence |
| consultant-solutions | GitHub, Hacker News, Lobste.rs | Technical depth |
| consultant-trainer | Course platforms, documentation, textbooks | Educational quality |
| curious-kimi | Contrarian sources, critique posts, hacker forums | Questioning consensus |

---

## 4. Roadmap

### Phase 1: Anti-SEO Signals (NOW)
- [ ] Add `SourceQualityClassifier` to THEE
- [ ] Add content farm detection heuristics
- [ ] Add indie web / rich source boost
- [ ] Update `TRUST_TIERS` with anti-SEO dimensions

### Phase 2: Rich Source Discovery (NEXT)
- [ ] `picocloth discover` CLI command
- [ ] HN Algolia integration
- [ ] arXiv API integration
- [ ] GitHub trending API
- [ ] Specialist forum search

### Phase 3: Fleet Specialization (FUTURE)
- [ ] Per-node discovery specialization
- [ ] Cross-node source validation
- [ ] Expert curation voting
- [ ] Personal knowledge graph construction

---

## 5. Citations

1. Schultheiß, S., Häußler, H., & Lewandowski, D. (2022). "Does Search Engine Optimization come along with high-quality content?" ACM SIGIR CHIIR.
2. Schweiger, S. & Cress, U. (2019). "Attitude confidence and source credibility in information foraging with social tags." PLOS ONE.
3. Pirolli, P. & Card, S. (1999). "Information Foraging." Psychological Review.
4. Wei et al. (2025). "BrowseComp: Benchmarking browser-based agents."
5. Bioptic Agent (2025). "Wide Search AI Agents for Drug Asset Scouting." 79.7% F1 vs Perplexity 44.2%.
6. LiveResearchBench (2025). "Multi-agent families lead on average."
7. IndieWeb Community (2025-2026). https://indieweb.org
8. parallel-agent-skills (2026). https://github.com/parallel-web/parallel-agent-skills
