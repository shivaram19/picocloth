# Execution Plan: Integration — CLI + MCP + Testing + Commit

This plan ties all gap-filling components together into a coherent system.

---

## Step 6.1: Update `ExtractEngine` in `extract.py` Tool

**File**: `picocloth-cli/src/picocloth_cli/tools/extract.py`

### 6.1.1 Add `validate_citations` parameter to `run()`

**Current signature**:
```python
def run(self, inputs: list[dict[str, Any]], topic: str = "") -> tuple[list[ExtractedFact], ExtractReport]:
```

**New signature**:
```python
def run(
    self,
    inputs: list[dict[str, Any]],
    topic: str = "",
    validate_citations: bool = False,
    verify: bool = False,
) -> tuple[list[ExtractedFact], ExtractReport]:
```

**Implementation**:
After `self.xref.cross_reference(all_facts)` and before deduplication:
```python
# Citation validation
if validate_citations:
    from picocloth_cli.tools.citation_validator import CitationValidator
    validator = CitationValidator(check_reachability=False)
    reports = validator.validate_batch(all_facts)
    for fact, report in zip(all_facts, reports):
        fact.verified_by["citation_validation"] = report.to_dict()
        health = report.citation_health_score
        fact.confidence = round(fact.confidence * health, 2)
        fact.confidence_breakdown["citation_health"] = health

# Fleet verification (local simulation)
if verify:
    from picocloth_cli.tools.verification_pool import FleetVerificationPool
    pool = FleetVerificationPool()
    results = pool.verify_batch(all_facts, strategy="weighted")
    for fact, result in zip(all_facts, results):
        fact.verified_by["fleet_verification"] = result.to_dict()
        if result.verdict == "VERIFIED":
            fact.confidence = round(min(0.98, fact.confidence + 0.05), 2)
        elif result.verdict == "REFUTED":
            fact.confidence = round(max(0.0, fact.confidence - 0.20), 2)
```

**Acceptance criteria**:
- [ ] `run(validate_citations=True)` attaches citation reports
- [ ] `run(verify=True)` attaches verification results
- [ ] Both default to False (no performance impact)
- [ ] Confidence adjustments are conservative

### 6.1.2 Add `to_bibliography()` method

```python
def to_bibliography(self, path: Path | str, style: str = "inline-url") -> None:
    """Generate formatted bibliography from extracted facts."""
    from picocloth_cli.tools.citation_validator import CitationValidator
    validator = CitationValidator()
    bib = validator.generate_bibliography(self.facts, style=style)
    Path(path).write_text(bib, encoding="utf-8")
```

**Acceptance criteria**:
- [ ] Generates bibliography in 3 styles
- [ ] Deduplicates sources
- [ ] Assigns sequential reference numbers

---

## Step 6.2: Update `extract.py` Commands

**File**: `picocloth-cli/src/picocloth_cli/commands/extract.py`

### 6.2.1 Add flags to `from_file`

Add parameters:
```python
validate_citations: bool = typer.Option(False, "--validate-citations"),
verify: bool = typer.Option(False, "--verify"),
bibliography: Path = typer.Option(None, "--bibliography", "-b"),
```

Pass through to `engine.run(..., validate_citations=validate_citations, verify=verify)`.

If `bibliography`, call `engine.to_bibliography(bibliography)`.

### 6.2.2 Add flags to `search`

Same flags as `from_file`.

### 6.2.3 Rewrite `verify` command

**Current**: Generic MCP spawn_task.
**New**: Use `FleetVerificationPool`.

```python
@app.command()
def verify(
    fact_id: str = typer.Argument(..., help="Fact ID to verify"),
    strategy: str = typer.Option("weighted", "--strategy", help="weighted|unanimous|threshold"),
    nodes: str = typer.Option("all", "--nodes", help="Nodes to ask"),
    simulate: bool = typer.Option(False, "--simulate", help="Local simulation without fleet"),
) -> None:
    # 1. Load fact from memory
    memory_dir = Path(PICOCLOTH_DIR) / "shared" / "memory" / "facts"
    fact = None
    for fpath in memory_dir.glob("*.jsonl"):
        with open(fpath) as f:
            for line in f:
                d = json.loads(line)
                if d.get("fact_id") == fact_id:
                    fact = ExtractedFact.from_dict(d)
                    break
        if fact:
            break
    
    if not fact:
        console.print(f"[red]Fact {fact_id} not found[/red]")
        raise typer.Exit(1)
    
    # 2. Verify
    from picocloth_cli.tools.verification_pool import FleetVerificationPool
    pool = FleetVerificationPool()
    
    available_nodes = None
    if nodes != "all":
        available_nodes = [n.strip() for n in nodes.split(",")]
    
    result = pool.verify_fact(fact, strategy=strategy, available_nodes=available_nodes)
    
    # 3. Display Rich output
    _print_verification_result(result)
    
    # 4. Store back
    fact.verified_by["fleet_verification"] = result.to_dict()
    # ... write back to memory
```

### 6.2.4 Add `validate-citations` command

As specified in `02-citation-validator.md`.

**Acceptance criteria**:
- [ ] All 4 commands compile and import cleanly
- [ ] `--validate-citations` flag works on both `search` and `from_file`
- [ ] `--verify` flag works on both `search` and `from_file`
- [ ] `verify` command shows Rich vote table
- [ ] `validate-citations` command shows Rich error table

---

## Step 6.3: Update `search.py` Commands

**File**: `picocloth-cli/src/picocloth_cli/commands/search.py`

### 6.3.1 Add `discover` command

As specified in `04-indie-discovery.md`.

### 6.3.2 Add `optimize` command

As specified in `03-retrospective-optimizer.md`.

### 6.3.3 Add `watch` and `watch-daemon` commands

As specified in `05-topic-monitor.md`.

### 6.3.4 Auto-record yield after execution

In `_execute_plan()` (or after search execution), add:
```python
from picocloth_cli.tools.search_strategy import SearchStrategyEngine
strategy = SearchStrategyEngine()
strategy.record_yield(plan, len(results), len(facts), report.avg_confidence)
```

**Note**: `_execute_plan()` is currently a placeholder. Need to implement actual execution.

**Minimal execution**:
```python
def _execute_plan(plan: Any, store: bool) -> None:
    if not HAS_DDGS:
        console.print("[yellow]duckduckgo-search not installed. Install to execute.[/yellow]")
        return
    
    results = []
    with DDGS() as ddgs:
        for q in plan.queries[:3]:  # Limit to top 3 for cost control
            try:
                r = list(ddgs.text(q["query"], max_results=5))
                results.extend(r)
            except Exception as e:
                logger.warning("Search failed for %s: %s", q["query"], e)
    
    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return
    
    # Extract facts
    from picocloth_cli.tools.extract import ExtractEngine
    engine = ExtractEngine(api_key=_get_api_key(), tier="hybrid")
    facts, report = engine.run(results, topic=plan.topic)
    
    # Record yield
    from picocloth_cli.tools.search_strategy import SearchStrategyEngine
    strategy = SearchStrategyEngine()
    strategy.record_yield(plan, len(results), len(facts), report.avg_confidence)
    
    console.print(f"[green]✓[/green] Extracted {len(facts)} facts (avg conf: {report.avg_confidence})")
    
    if store and facts:
        # ... store via MCP or local
        pass
```

**Acceptance criteria**:
- [ ] `_execute_plan()` is no longer a placeholder
- [ ] Yield auto-recorded after every execution
- [ ] Cost-limited: max 3 queries × 5 results = 15 results per plan

---

## Step 6.4: Update MCP Fleet Server

**File**: `mcp-fleet-server/server.py`

### 6.4.1 Add new tools to `TOOLS` dict

```python
"fleet_verify": { ... },           # from 01-verification-pool.md
"fleet_validate_citations": { ... }, # from 02-citation-validator.md
"fleet_discover": { ... },          # from 04-indie-discovery.md
"fleet_optimize": { ... },          # from 03-retrospective-optimizer.md
```

### 6.4.2 Add handler functions

```python
def verify_fact(fact: dict, strategy: str, nodes: list | None) -> dict:
    # Minimal inline implementation (server has no CLI dependency)
    # Use local simulation only
    votes = []
    for agent_id in nodes or ["curious-kimi"]:
        votes.append({
            "agent_id": agent_id,
            "verdict": "SUPPORT",  # Simplified
            "confidence": 0.7,
            "justification": "Fleet server simulation mode"
        })
    return {
        "fact_id": fact.get("fact_id"),
        "verdict": "VERIFIED",
        "confidence": 0.7,
        "votes": votes,
        "consensus_method": "fleet-server-simulated",
    }

def validate_citations(facts: list, check_urls: bool) -> dict:
    reports = []
    for fact in facts:
        errors = []
        sources = fact.get("sources", [])
        if not sources:
            errors.append({"type": "E6_MISSING_CITATION", "severity": "critical"})
        for s in sources:
            url = s.get("url", "")
            if not url.startswith(("http://", "https://")):
                errors.append({"type": "E2_INCOMPLETE_URL", "severity": "critical"})
        reports.append({"fact_id": fact.get("fact_id"), "errors": errors})
    return {"reports": reports}

def discover_sources(topic: str, limit: int) -> dict:
    # Read embedded registry from shared/doctrine/indie-web-registry.json
    registry_path = Path(SHARED_DIR, "doctrine", "indie-web-registry.json")
    sources = []
    if registry_path.exists():
        with open(registry_path) as f:
            registry = json.load(f)
        for category, items in registry.items():
            for item in items:
                if topic.lower() in " ".join(item.get("topics", [])).lower():
                    sources.append({**item, "category": category})
    return {"sources": sources[:limit]}

def optimize_queries(topic: str, limit: int) -> dict:
    # Read yield DB
    yield_path = Path(SHARED_DIR, "project", "facts", "search-yield.jsonl")
    suggestions = []
    if yield_path.exists():
        # Simple: return topics that yielded well historically
        pass
    # Fallback: generic suggestions
    suggestions = [
        f"{topic} latest research 2026",
        f"{topic} site:arxiv.org",
        f"{topic} expert analysis",
    ]
    return {"suggestions": suggestions[:limit]}
```

### 6.4.3 Update `handle_tool_call()`

```python
elif name == "fleet_verify":
    return verify_fact(arguments["fact"], arguments.get("strategy", "weighted"), arguments.get("nodes"))
elif name == "fleet_validate_citations":
    return validate_citations(arguments["facts"], arguments.get("check_urls", False))
elif name == "fleet_discover":
    return discover_sources(arguments["topic"], arguments.get("limit", 10))
elif name == "fleet_optimize":
    return optimize_queries(arguments["topic"], arguments.get("limit", 5))
```

**Acceptance criteria**:
- [ ] All 4 new tools registered in `TOOLS`
- [ ] All 4 tools handled in `handle_tool_call()`
- [ ] `mcp-fleet-server/server.py` compiles
- [ ] Server starts without errors

---

## Step 6.5: Write Skill Documentation

Create 5 skill docs in `shared/doctrine/skills/`:

| File | Source Plan |
|------|-------------|
| `verification-pool.md` | `01-verification-pool.md` Step 1.7 |
| `citation-validator.md` | `02-citation-validator.md` Step 2.6 |
| `retrospective-optimizer.md` | `03-retrospective-optimizer.md` Step 3.7 |
| `indie-discovery.md` | `04-indie-discovery.md` Step 4.7 |
| `topic-monitor.md` | `05-topic-monitor.md` Step 5.6 |

**Template for each**:
```markdown
# Skill: <Name> v1.0

## Research
- Paper 1: finding + citation
- Paper 2: finding + citation

## Architecture
[Diagram or description]

## CLI Usage
```bash
picocloth <command> <args>
```

## MCP Tool
- Tool name
- Parameters
- Example response

## Why This Design
[Explain key decisions backed by research]
```

**Acceptance criteria**:
- [ ] All 5 skill docs created
- [ ] Each doc has ≥2 research citations
- [ ] Each doc has CLI usage examples
- [ ] Each doc explains WHY, not just WHAT

---

## Step 6.6: Compile & Integration Test

### 6.6.1 Compile all new files

```bash
cd /Users/shivaramgoud/picocloth-work

# Core tools
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/verification_pool.py
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/citation_validator.py
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/retrospective_optimizer.py
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/indie_discovery.py
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/topic_monitor.py

# Commands
python3 -m py_compile picocloth-cli/src/picocloth_cli/commands/extract.py
python3 -m py_compile picocloth-cli/src/picocloth_cli/commands/search.py

# MCP server
python3 -m py_compile mcp-fleet-server/server.py
```

### 6.6.2 Import test

```bash
python3 -c "
from picocloth_cli.tools.verification_pool import FleetVerificationPool
from picocloth_cli.tools.citation_validator import CitationValidator
from picocloth_cli.tools.retrospective_optimizer import RetrospectiveOptimizer
from picocloth_cli.tools.indie_discovery import IndieWebDiscoveryEngine
from picocloth_cli.tools.topic_monitor import TopicMonitor
print('All imports OK')
"
```

### 6.6.3 End-to-end smoke test

```bash
# 1. Test extraction with validation
python3 -c "
from picocloth_cli.tools.extract import ExtractEngine
engine = ExtractEngine()
facts, report = engine.run([
    {'href': 'https://example.com', 'title': 'Test', 'body': '50% of AI projects fail.'}
], topic='AI', validate_citations=True)
print(f'Facts: {len(facts)}, Report: {report}')
"

# 2. Test verification
python3 -c "
from picocloth_cli.tools.verification_pool import FleetVerificationPool
from picocloth_cli.tools.extract import ExtractEngine, ExtractedFact, FactTriple, Source
pool = FleetVerificationPool()
fact = ExtractedFact(
    fact_id='test1', topic='AI', triple=FactTriple('AI', 'statistic', '50% fail'),
    raw_text='50% fail', fact_type='statistic', fact_subtype='percentage',
    sources=[Source(url='https://example.com', domain='example.com', tier=2)],
    confidence=0.6
)
result = pool.verify_fact(fact, strategy='weighted')
print(f'Verdict: {result.verdict}, Confidence: {result.confidence}')
"

# 3. Test citation validation
python3 -c "
from picocloth_cli.tools.citation_validator import CitationValidator
v = CitationValidator()
class F:
    fact_id = 't1'
    sources = []
    triple = type('T', (), {'claim': 'test'})
    raw_text = 'test'
print(v.validate_fact(F()).to_dict())
"
```

**Acceptance criteria**:
- [ ] All files compile
- [ ] All imports succeed
- [ ] Smoke tests produce sensible output
- [ ] No unhandled exceptions

---

## Step 6.7: Git Commit

### 6.7.1 Stage files

```bash
cd /Users/shivaramgoud/picocloth-work
git add -A
```

### 6.7.2 Commit with detailed message

```bash
git commit -m "feat(gap-fill): Complete parallel-agent-skills gap filling v1.0

Fills 5 remaining gaps with research-backed implementations:

Gap 5 — Multi-Agent Verification
- FleetVerificationPool with heterogeneous agent dispatch
- Three consensus strategies: weighted (A-HMAD), unanimous, threshold
- Credibility tracker with 30-day exponential decay
- Deterministic simulation mode + fleet dispatch mode
- CLI: extract verify --strategy weighted|unanimous|threshold

Gap 9 — Citation Association Quality
- CitationValidator with E1-E8 error taxonomy (LiveResearchBench)
- URL canonicalization and duplicate detection
- Unsupported claim flagging heuristic
- Bibliography generation (3 styles)
- CLI: extract validate-citations --check-urls --fix

Gap 11 — Yield Tracking & Retrospective Optimization
- RetrospectiveOptimizer extends existing yield DB
- Query template-level scoring with temporal decay
- Topic-type classification for pattern matching
- CLI: search optimize --execute
- Auto-yield recording from extract commands

Gap 13 — Indie Web Discovery
- Expert blog registry with 15+ indie sources
- HN Algolia integration for community content
- Quality heuristics: RSS, plain HTML, engagement
- CLI: search discover --extract --no-hn

Gap 9 (Original) — Monitoring / Continuous Tracking
- TopicMonitor with JSONL persistence
- Diff algorithm: new facts, updates, contradictions
- CLI: search watch --list --run-now --remove
- CLI: search watch-daemon --once

MCP Integration:
- fleet_verify, fleet_validate_citations, fleet_discover, fleet_optimize
- Zero-dependency inline handlers in fleet server

Research:
- Six Sigma Agent (2026), A-HMAD (Springer 2025), MAV (Feb 2025)
- LiveResearchBench (2026), Deerflow+, DEFT Taxonomy
- ConvSearch-R1 (2025), Nogueira & Cho (2017), Retroformer
- Schultheiß et al. (2022), Marginalia Search
- Pirolli & Card (1999) Information Foraging Theory"
```

### 6.7.3 Verify commit

```bash
git log -1 --stat
git status
```

**Acceptance criteria**:
- [ ] Commit contains all new files
- [ ] Commit message references all 5 gaps
- [ ] Working tree clean after commit
- [ ] No large binary files accidentally included

---

## Rollback Plan

If anything breaks:
```bash
cd /Users/shivaramgoud/picocloth-work
git reset --soft HEAD~1  # Undo commit, keep changes
git checkout -- picocloth-cli/src/picocloth_cli/commands/extract.py  # Restore original command
git checkout -- picocloth-cli/src/picocloth_cli/commands/search.py   # Restore original command
git checkout -- mcp-fleet-server/server.py                          # Restore original server
# Keep new tools in picocloth-cli/src/picocloth_cli/tools/ for iterative fixing
```
