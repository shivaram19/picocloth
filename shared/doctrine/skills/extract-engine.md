---
title: Extract Engine (THEE)
trigger: web_search_complete, research_raw_data, fact_extraction_needed
author: PicoCloth
version: 1.0
---

# Extract Engine Skill — THEE v1.0

## What Is THEE?

**T**iered **H**ybrid **E**xtract **E**ngine — structured knowledge extraction from raw web search results.

Turns this:
```json
{"title": "AI Market to Hit $216B", "snippet": "The global AI agent market is projected to reach $216 billion by 2030, growing at 47% CAGR..."}
```

Into this:
```json
{"triple": {"entity": "Global AI agent market", "relation": "projected_value", "claim": "$216 billion by 2030"}, "confidence": 0.85, "sources": [{"domain": "mckinsey.com", "tier": 1}]}
```

## Why Triples?

Academic research in Open Information Extraction (OIE) proves that `(subject, relation, object)` triples are the optimal structured representation for:
- Knowledge graph construction
- Cross-reference and conflict detection
- Temporal reasoning
- Multi-hop queries

Citations: Neural OIE (Cornell), IMoJIE (Kolluru et al., 2020), OpenIE6

## Three Tiers

### Tier 1: Fast Lane (Regex + Heuristics)
- **Cost**: ₹0
- **Latency**: <50ms per result
- **Coverage**: ~65% of common fact types
- **Handles**: statistics, financials, dates, quotes, comparisons, funding rounds
- **Academic basis**: TEXTRUNNER, REVERB, ClausIE rule-based OIE systems

### Tier 2: Deep Lane (LLM Atomic Decomposition)
- **Cost**: ~₹2-5 per result (gpt-4o-mini)
- **Latency**: 1-3s per result
- **Coverage**: Complex claims regex misses
- **Handles**: implicit facts, nuanced claims, multi-sentence assertions
- **Academic basis**: FActScore (Min et al., 2023), VeriScore (Song et al., 2024)

### Tier 3: Verify Lane (Fleet Multi-Agent)
- **Cost**: Fleet compute time
- **Latency**: 5-10s
- **Coverage**: High-confidence validation
- **Handles**: contradiction resolution, corroboration voting
- **Academic basis**: Nature s41598-026-41862-z (2026) multi-agent scoring

## Mem0-Style Memory Operations

When facts enter shared memory, THEE performs one of four operations:

| Operation | Condition | Action |
|-----------|-----------|--------|
| **ADD** | New entity+relation pair | Append to memory |
| **UPDATE** | Same entity+relation, higher confidence | Mark old as superseded, replace |
| **DELETE** | Explicit contradiction with overwhelming confidence | Remove old fact |
| **NOOP** | Duplicate or near-duplicate already exists | Skip |

**Citation**: Mem0 research paper (Apr 2025 ArXiv). Achieves 91% latency reduction vs full-context.

## Confidence Scoring

```
confidence = source_tier_score + corroboration_boost + recency_boost + llm_precision_bonus

source_tier_score:
  Tier 1 (academic/gov/established media): 0.70
  Tier 2 (reputable tech/business): 0.50
  Tier 3 (blogs/aggregators/social): 0.30

corroboration_boost: +0.05 per independent corroborating source (max 0.15)
recency_boost: +0.05 if published within 6 months
llm_precision_bonus: +0.05 for Tier 2 deep-lane facts
```

## Temporal Validity

Every fact carries temporal metadata:
- `valid_from`: When the fact became true (extracted from text or publication date)
- `valid_until`: When the fact was superseded (set on UPDATE)
- `superseded_by`: fact_id of the newer fact
- `extracted_at`: Timestamp of extraction

**Why this matters**: Zep/Graphiti research shows temporal knowledge graphs are essential for consultant-grade accuracy. A fact like "OpenAI revenue was $3.4B" is only valid for a specific time window.

## Usage from CLI

```bash
# Search + extract + store + broadcast
picocloth extract search "AI agent market 2026" --limit 10 --store --broadcast

# Extract from existing results
picocloth extract from-file results.json --topic "AI agents" --tier hybrid

# View stored facts
picocloth extract facts --topic "AI agents" --min-confidence 0.7

# Request fleet verification
picocloth extract verify --fact-id abc123 --nodes all
```

## Usage from Node Config

```json
"tools": {
  "extract": {
    "enabled": true,
    "mode": "hybrid",
    "auto_store": true,
    "confidence_threshold": 0.5
  }
}
```

## Usage via MCP

```json
{
  "method": "tools/call",
  "params": {
    "name": "fleet_extract",
    "arguments": {
      "results": [{"title": "...", "body": "...", "href": "..."}],
      "topic": "research topic",
      "tier": "hybrid",
      "store": true,
      "broadcast": false
    }
  }
}
```

## Academic Citations

1. Min et al. (2023). "FActScore: Fine-grained Atomicity for Factual Precision in LLMs."
2. Wei et al. (2024). "SAFE: Search-Augmented Factuality Evaluator." Google DeepMind.
3. Song et al. (2024). "VeriScore: Evaluating Verifiable Claims in Long-form Text."
4. Mem0 Research (Apr 2025). ArXiv. ADD/UPDATE/DELETE/NOOP memory ops.
5. Nature (Mar 2026). "Multi-agent systems and credibility-based scoring." s41598-026-41862-z
6. VERITAS-NLI (2025). "Validation and Extraction via Web Scraping and NLI." 84.3% accuracy.
7. Kolluru et al. (2020). "IMoJIE: Iterative Memory-Based Joint Information Extraction."
8. ArXiv 2506.18096v2. "Deep Research Agents: A Systematic Examination."
