# Skill: Indie Web Discovery v1.0

## Research

- **Schultheiß et al. (2022)**: "Non-optimized, but high-quality content may be outranked by optimized content." SEO-optimized content dominates commercial search results, systematically pushing expert blogs and personal sites down.

- **Marginalia Search** (Viktor Lofgren): Independent DIY search engine that prioritizes "grass fed, free range HTML." Designed as a "minority report that keeps [corporate searches] honest." No tracking, no data sharing.

- **"Searching the indieweb"** (Dec 2025): "Corporate web is doomed, but the indieweb is thriving." Need for accessible tools to surface content from real people, not just platforms.

- **SearXNG**: Metasearch engine aggregating multiple sources. No tracking, self-hostable.

## Architecture

```
Topic → Registry Search → HN Algolia Search → Quality Heuristic Scoring
→ Ranked Sources → Site-Targeted Queries
```

**Quality heuristics** (designed to surface genuine expert content):
- Has RSS feed (+0.2) — active publishing signal
- Non-corporate domain (+0.2) — excludes Medium, LinkedIn, etc.
- Expert blog / academic category (+0.15)
- HN community validation (+0.2) — high engagement
- Topic depth match (+0.15)

**Registry categories**:
- `expert_blogs` — practitioner-written technical blogs
- `newsletters` — curated expert newsletters
- `academic_indies` — independent academic publishing
- `communities` — discussion forums (HN, Lobsters)

## CLI Usage

```bash
# Discover indie sources for a topic
picocloth search discover "distributed systems"

# Skip HN search (faster)
picocloth search discover "topic" --no-hn

# Discover and extract facts
picocloth search discover "topic" --extract
```

## MCP Tool

- **Tool**: `fleet_discover`
- **Parameters**: `topic` (string), `limit` (integer)
- **Returns**: `{sources: [{name, url, category, topics}]}`

## Why This Design

We chose a **curated registry + HN search** hybrid instead of a general web crawler because:
1. Crawling is expensive and violates our "$10 hardware" constraint
2. Expert blogs are stable — they don't change domains frequently
3. HN Algolia provides community validation without crawling

We chose **site-targeted queries** (`site:domain`) because they bypass SEO-optimized results and search directly within expert sites.
