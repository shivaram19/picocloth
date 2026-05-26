---
title: Real-Time Web Search
trigger: research_task, fact_check, competitive_analysis, trend_spotting
author: PicoCloth
provider: duckduckgo + serper
---

# Real-Time Web Search Protocol

## When to Use
- Current events, news, or rapidly changing information
- Competitive intelligence (pricing, features, launches)
- Academic paper discovery
- Verifying claims with primary sources
- Finding the latest framework versions or API docs

## Workflow

1. **Decompose query**
   - Break complex questions into 3-5 targeted search queries
   - Use site-specific filters when appropriate: `site:arxiv.org`, `site:github.com`, `site:sec.gov`

2. **Search broadly**
   - Execute all queries in parallel
   - Capture top 10 results per query
   - Record timestamp of search (information decays)

3. **Read deeply**
   - Fetch full text of top 3 most relevant results
   - Extract key facts with confidence scores (0.0-1.0)
   - Record source URL, author, publication date

4. **Synthesize**
   - Cross-reference multiple sources
   - Flag contradictions between sources
   - Distinguish fact from opinion
   - Write findings to `shared/project/facts/{topic}-{date}.jsonl`

5. **Report to fleet**
   - Update `shared/state/fleet-state.json` with search completion
   - Broadcast key findings via MCP `fleet_broadcast`
   - Append to `shared/project/outreach/research-briefs/` if actionable

## Search Providers

| Provider | Best For | Rate Limit |
|----------|----------|------------|
| **DuckDuckGo** | General queries, privacy-respecting | No key needed |
| **Serper.dev** | Google Search API, structured JSON | 2,500 free queries/mo |
| **Tavily** | AI-optimized search with summaries | 1,000 free queries/mo |
| **Bing Search API** | Enterprise, high volume | Paid |

## Fact Recording Format

```jsonl
{"timestamp": "2026-05-24T20:30:00Z", "topic": "AI agent market size", "fact": "Global AI agent market projected at $216B by 2030", "confidence": 0.85, "source": "https://www.mckinsey.com/...", "node": "consultant-growth"}
```

## Red Flags
- Source older than 1 year for tech topics → re-verify
- Single source for controversial claim → find corroboration
- Anonymous source for major claim → downgrade confidence
- Press release without independent coverage → treat as biased
