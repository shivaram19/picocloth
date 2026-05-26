---
title: Real-Time Web Search + Extract
trigger: research_task, fact_check, competitive_analysis, trend_spotting, deep_research
author: PicoCloth
provider: duckduckgo + serper + THEE
version: 2.0
---

# Real-Time Web Search + Extraction Protocol

## When to Use
- Current events, news, or rapidly changing information
- Competitive intelligence (pricing, features, launches)
- Academic paper discovery
- Verifying claims with primary sources
- Finding latest framework versions or API docs
- **Deep research**: multi-source synthesis with structured fact extraction

## Workflow (v2.0: Search → Extract → Verify → Store)

### Step 1: Decompose Query
- Break complex questions into 3-5 targeted search queries
- Use site-specific filters: `site:arxiv.org`, `site:github.com`, `site:sec.gov`

### Step 2: Search Broadly
- Execute all queries in parallel
- Capture top 10 results per query
- Record timestamp (information decays)

### Step 3: EXTRACT (THEE — Tiered Hybrid Extract Engine)
**This is the critical upgrade from v1.0.**

Run extracted search results through THEE:

```bash
picocloth extract search "your topic" --limit 10 --store --broadcast
```

Or programmatically via MCP:
```json
{
  "method": "tools/call",
  "params": {
    "name": "fleet_extract",
    "arguments": {
      "results": [...],
      "topic": "AI agent market",
      "tier": "hybrid",
      "store": true,
      "broadcast": true
    }
  }
}
```

**THEE produces structured triples:**
```json
{
  "triple": {
    "entity": "Global AI agent market",
    "relation": "projected_value",
    "claim": "$216 billion by 2030"
  },
  "confidence": 0.85,
  "sources": [{"domain": "mckinsey.com", "tier": 1}],
  "corroborated_by": ["fact_id_2"],
  "temporal": {"valid_from": "2026", "valid_until": null}
}
```

**Extraction Tiers:**
| Tier | Method | Coverage | Cost | When to Use |
|------|--------|----------|------|-------------|
| **fast** | Regex + heuristics | ~65% | ₹0 | High-volume, time-sensitive |
| **deep** | LLM atomic decomposition | ~20% | ~₹2-5/result | Complex claims, deep research |
| **hybrid** | Both combined | ~85% | Mixed | Default for consultant work |

### Step 4: Read Deeply
- Fetch full text of top 3 most relevant results
- Extract key facts with confidence scores (0.0-1.0)
- Record source URL, author, publication date

### Step 5: Verify
- **Cross-reference**: Compare claims across multiple sources
- **Fleet voting**: Spawn verification tasks to other consultant nodes
  ```bash
  picocloth extract verify --fact-id abc123 --nodes all
  ```
- **Temporal check**: Is this fact still valid? Check `valid_from`/`valid_until`

### Step 6: Synthesize & Store
- Write verified facts to `shared/memory/facts/{topic}.jsonl`
- Update `shared/state/fleet-state.json` with search completion
- Broadcast key findings via MCP `fleet_broadcast`
- Append to `shared/project/outreach/research-briefs/` if actionable

## Fact Recording Format (v2.0)

```jsonl
{"fact_id": "a1b2c3d4", "topic": "AI agent market size", "triple": {"entity": "Global AI agent market", "relation": "projected_value", "claim": "$216B by 2030"}, "confidence": 0.85, "sources": [{"url": "https://mckinsey.com/...", "domain": "mckinsey.com", "tier": 1}], "corroborated_by": ["e5f6g7h8"], "extracted_at": "2026-05-25T00:00:00Z", "extracted_by": "consultant-academic"}
```

## Search Providers

| Provider | Best For | Rate Limit |
|----------|----------|------------|
| **DuckDuckGo** | General queries, privacy-respecting | No key needed |
| **Serper.dev** | Google Search API, structured JSON | 2,500 free queries/mo |
| **Tavily** | AI-optimized search with summaries | 1,000 free queries/mo |
| **Bing Search API** | Enterprise, high volume | Paid |

## Red Flags
- Source older than 1 year for tech topics → re-verify via THEE
- Single source for controversial claim → find corroboration
- Anonymous source for major claim → downgrade confidence
- Press release without independent coverage → treat as biased
- **NEW**: Fact with `contradicts` array → trigger fleet verification vote

## Academic Foundations
- **FActScore** (Min et al., 2023): atomic fact decomposition
- **SAFE** (Wei et al., 2024): search-augmented verification
- **VeriScore** (Song et al., 2024): verifiable claim extraction
- **Mem0** (Apr 2025): ADD/UPDATE/DELETE/NOOP memory operations
- **Nature 2026** (s41598-026-41862-z): multi-agent credibility scoring
- **VERITAS-NLI** (2025): 84.3% accuracy via web + NLI
