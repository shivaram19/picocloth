# Skill: Retrospective Optimizer v1.0

## Research

- **ConvSearch-R1** (Zhu et al., May 2025, arXiv:2505.15776): Self-driven query reformulation via reinforcement learning. Two-stage pipeline: Self-Driven Policy Warm-Up (SDPWU) + Retrieval-Guided RL (RGRL). Achieved 10%+ improvement on TopiOCQA with a 3B parameter model.

- **Nogueira & Cho** (2017, EMNLP): RL query reformulation with 5-20% recall improvement. "Only a small subset of terms are useful for reformulation." RL-RNN-SEQ produces 3× shorter queries with comparable performance.

- **Retroformer / TRICE** (2024): Agents learn from retrospective execution feedback. Credit assignment across long tool-use chains.

- **Pirolli & Card** (1999): Information Foraging Theory — users optimize information gain per unit cost. Applied to search: reformulation should maximize yield per query.

## Architecture

```
Search Execution → Yield Recording → Temporal Decay → Template Scoring
→ Reformulation Suggestion → Optional Execution
```

**Reward function** (ConvSearch-R1 style):
```
R = facts_extracted × avg_confidence / queries_count
```

**Temporal decay** (Pirolli & Card recency bias):
```
R_decayed = R × 0.5^(days_ago / 30)
```

**Topic-type classification**: Queries are classified as research, technical, business, or general. Templates are matched within type for higher relevance.

## CLI Usage

```bash
# Get optimization suggestions for a topic
picocloth search optimize "AI market"

# Suggest and execute
picocloth search optimize "AI market" --execute

# View yield report
picocloth search yield-report

# Auto-records after every --execute search
picocloth search clever "topic" --execute
```

## MCP Tool

- **Tool**: `fleet_optimize`
- **Parameters**: `topic` (string), `limit` (integer)
- **Returns**: `{suggestions: ["query 1", "query 2", ...]}`

## Why This Design

We chose to **extend the existing yield DB** rather than create a separate database because `SearchStrategyEngine` already records yield data. The optimizer enriches this data with template-level scoring and temporal decay.

We use **temporal decay** because Pirolli & Card showed that information scent changes over time. A query that worked well 6 months ago may not work today.

We provide **fallback generic templates** when no history exists because cold-start is a real problem. The user gets value immediately, and the system learns from their usage.
