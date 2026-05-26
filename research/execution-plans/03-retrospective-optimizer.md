# Execution Plan: Gap 11 — Yield Tracking & Retrospective Optimization

## Research Backing
- ConvSearch-R1 (Zhu et al., May 2025, arXiv:2505.15776): Self-driven query reformulation via RL. 10%+ improvement on TopiOCQA with 3B model.
- Nogueira & Cho (2017, EMNLP): RL query reformulation with 5-20% recall improvement. "Only a small subset of terms are useful."
- Retroformer / TRICE: Agents learn from retrospective execution feedback.
- Pirolli & Card (1999): Information Foraging Theory — optimize gain per unit cost.

## Key Design Constraint
`SearchStrategyEngine` already has basic yield tracking (`record_yield`, `get_top_yielding_patterns`). `RetrospectiveOptimizer` **extends** this data rather than replacing it.

## File
`picocloth-cli/src/picocloth_cli/tools/retrospective_optimizer.py`

---

## Step 3.1: Design `RetrospectiveOptimizer` Data Model

**Reads**: `shared/memory/search-yield.jsonl` (existing format from SearchStrategyEngine)
**Writes**: `shared/memory/search-yield.jsonl` (enriched records with template scores)

**Enriched record format** (extends existing):
```json
{
  "timestamp": "2026-05-25T...",
  "topic": "AI market size",
  "mode": "clever",
  "platforms": ["arxiv", "hn"],
  "queries_count": 3,
  "results_count": 15,
  "facts_count": 7,
  "avg_confidence": 0.72,
  "knowledge_yield": 1.68,
  "templates": ["{topic} market size 2026", "{topic} revenue growth rate"],
  "topic_type": "business",
  "platform_yields": {"arxiv": 0.5, "hn": 1.2}
}
```

**Acceptance criteria**:
- [ ] Record format backward-compatible with existing `search-yield.jsonl`
- [ ] New fields optional — old records still parseable

---

## Step 3.2: Write `RetrospectiveOptimizer` Core

**Class structure**:
```python
class RetrospectiveOptimizer:
    def __init__(self, yield_db_path: Path | None = None):
        self.yield_db_path = yield_db_path or Path("shared/memory/search-yield.jsonl")
        self.decay_days = 30  # Exponential decay half-life
    
    def record(self, plan, results_count, facts_count, avg_confidence, templates=None):
        # Write enriched record to yield_db
        pass
    
    def suggest_reformulation(self, topic: str, current_plan: SearchPlan) -> list[str]:
        # 1. Classify topic type
        # 2. Look up historical yields for similar topics
        # 3. Identify high-yield templates
        # 4. Suggest reformulated queries
        pass
    
    def get_top_templates(self, topic_type: str, limit: int = 5) -> list[dict]:
        # Return highest-yielding query templates with scores
        pass
    
    def _classify_topic_type(self, topic: str) -> str:
        # Heuristic: research|technical|business|general
        pass
    
    def _compute_time_decayed_score(self, records: list[dict]) -> float:
        # Pirolli & Card: recent searches weighted higher
        pass
```

**Reward function** (ConvSearch-R1 style):
```
R = facts_count × avg_confidence / queries_count
```

With temporal decay:
```
R_decayed = R × 0.5^(days_ago / 30)
```

**Acceptance criteria**:
- [ ] `record()` appends enriched data to existing JSONL
- [ ] `suggest_reformulation()` returns 3-5 reformulated queries
- [ ] `_compute_time_decayed_score()` weights recent data higher
- [ ] `python3 -m py_compile retrospective_optimizer.py` passes

---

## Step 3.3: Integrate with `SearchStrategyEngine`

**File**: `picocloth-cli/src/picocloth_cli/tools/search_strategy.py`

**Changes**:
1. Import `RetrospectiveOptimizer`
2. In `SearchStrategyEngine.__init__`, create `self.optimizer = RetrospectiveOptimizer()`
3. In `record_yield()`, pass templates to optimizer:
```python
def record_yield(self, plan, results_count, facts_count, avg_confidence):
    templates = [q["query"] for q in plan.queries]
    self.optimizer.record(plan, results_count, facts_count, avg_confidence, templates)
    # Also keep existing direct write for backward compatibility
    existing_record = {...}
    with open(self.yield_db_path, "a") as f:
        f.write(json.dumps(existing_record) + "\n")
```
4. Add `suggest_optimization(topic)` method that delegates to optimizer:
```python
def suggest_optimization(self, topic: str) -> list[dict]:
    """Get reformulation suggestions for a topic."""
    return self.optimizer.suggest_reformulation(topic, None)
```

**Acceptance criteria**:
- [ ] `SearchStrategyEngine` can suggest optimized queries
- [ ] Existing `record_yield()` still works
- [ ] No circular imports

---

## Step 3.4: Add `optimize` CLI Command

**File**: `picocloth-cli/src/picocloth_cli/commands/search.py`

**New command**:
```python
@app.command()
def optimize(
    topic: str = typer.Argument(..., help="Research topic to optimize"),
    limit: int = typer.Option(5, "--limit", "-n", help="Max suggestions"),
    execute: bool = typer.Option(False, "--execute", "-x", help="Run suggested searches"),
):
    """Suggest optimized search queries based on historical yield data."""
    # 1. Create RetrospectiveOptimizer
    # 2. Get top templates for topic
    # 3. Display Rich table: Template | Avg Yield | Runs | Suggested Reformulation
    # 4. If --execute, run each suggested query through ExtractEngine
```

**Rich display**:
- Summary: "Based on N historical searches for similar topics..."
- Table: Rank | Suggested Query | Expected Yield | Confidence | Source Template
- Highlight top 3 with different colors

**Acceptance criteria**:
- [ ] `picocloth search optimize "AI market"` shows suggestions
- [ ] Suggestions based on actual historical data
- [ ] `--execute` runs searches and extracts facts
- [ ] Yield recorded after execution

---

## Step 3.5: Auto-Record Yield from `search` and `extract` Commands

**Problem**: Currently yield is only recorded if explicitly called.
**Fix**: After every successful `picocloth extract search` or `picocloth extract from-file`, auto-record yield.

**Code change** in `commands/extract.py`:
```python
# After engine.run() in search() and from_file():
from picocloth_cli.tools.search_strategy import SearchStrategyEngine
strategy = SearchStrategyEngine()
strategy.record_yield(
    plan=type('P', (), {
        'topic': topic, 'mode': 'direct', 'platforms': ['duckduckgo'],
        'queries': [{'query': query}]
    })(),
    results_count=len(results),
    facts_count=len(facts),
    avg_confidence=report.avg_confidence,
)
```

**Better approach**: Create a simple `YieldRecorder` utility that doesn't need a full `SearchPlan`.

**Acceptance criteria**:
- [ ] Every `extract search` run records yield data
- [ ] Every `extract from-file` run records yield data
- [ ] No error if yield DB is missing

---

## Step 3.6: Register `fleet_optimize` MCP Tool

**File**: `mcp-fleet-server/server.py`

**Add to `TOOLS`**:
```python
"fleet_optimize": {
    "description": "Suggest optimized search queries based on yield history",
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "limit": {"type": "integer", "default": 5}
        },
        "required": ["topic"]
    }
}
```

**Handler**: Read `shared/project/facts/search-yield.jsonl` (or similar), aggregate, return top templates.

**Acceptance criteria**:
- [ ] Returns JSON array of suggested queries
- [ ] Works even with empty history (returns generic suggestions)

---

## Step 3.7: Skill Documentation

**File**: `shared/doctrine/skills/retrospective-optimizer.md`

**Contents**:
- ConvSearch-R1 two-stage pipeline (SDPWU + RGRL)
- Nogueira & Cho term selection strategy
- Reward function formula
- Temporal decay explanation
- CLI usage: `search optimize`, yield report

**Acceptance criteria**:
- [ ] Document explains RL connection without requiring RL expertise
- [ ] Formula for knowledge yield shown

---

## Step 3.8: Test & Commit

**Test commands**:
```bash
cd /Users/shivaramgoud/picocloth-work
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/retrospective_optimizer.py
python3 -c "
from picocloth_cli.tools.retrospective_optimizer import RetrospectiveOptimizer
ro = RetrospectiveOptimizer()
print('topic_type:', ro._classify_topic_type('AI market research'))
print('topic_type:', ro._classify_topic_type('python asyncio tutorial'))
"
```

**Commit message**:
```
feat(optimization): Retrospective Optimizer v1.0

- Extends existing yield DB with template-level scoring
- Topic-type classification (research|technical|business|general)
- Temporal decay weighting (30-day half-life)
- Query reformulation suggestions from historical yield
- CLI: search optimize --execute
- Auto-yield recording from extract search/from-file
- MCP: fleet_optimize tool registered

Research: ConvSearch-R1 (2025), Nogueira & Cho (2017),
Retroformer/TRICE, Pirolli & Card (1999)
```
