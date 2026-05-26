# Execution Plan: Gap 5 — Multi-Agent Verification

## Research Backing
- Six Sigma Agent (arXiv:2601.22290, Jan 2026): consensus-driven decomposed execution, atomic voting, dynamic scaling. ICE improved GPQA-diamond 46.9% → 68.2%.
- A-HMAD (Springer s44443-025-00353-3, 2025): heterogeneous debate with learned consensus. 78% vs 68% majority vote in disagreements — 31% relative error reduction.
- MAV (Feb 2025): "increasing verifiers rather than model size" as scaling dimension.
- Adversary-Resistant Multi-Agent (arXiv:2505.24239, Apr 2025): credibility scoring with self-refinement before voting.

## File
`picocloth-cli/src/picocloth_cli/tools/verification_pool.py`

## Status
✅ File created and compiles. Needs fixes before integration.

---

## Step 1.1: Fix Deterministic Simulation

**Problem**: `_dispatch_votes()` uses `random.random()` — non-deterministic.
**Fix**: Seed RNG from `fact_id` hash so same fact → same vote pattern.

**Code change** in `verification_pool.py`, method `_dispatch_votes`:
```python
import random
# Before generating votes, seed from fact content for determinism
seed = int(hashlib.sha256(fact_id.encode()).hexdigest(), 16) % (2**32)
rng = random.Random(seed)
# Replace all random.random() calls with rng.random()
```

**Acceptance criteria**:
- [ ] Same fact_id called twice returns identical votes
- [ ] Different fact_ids produce different vote patterns
- [ ] `python3 -m py_compile verification_pool.py` passes

---

## Step 1.2: Add MCP Fleet Dispatch Mode

**Problem**: `_dispatch_votes()` only simulates votes locally. Real verification needs MCP.
**Fix**: Add `dispatch_mode` parameter (`"simulate" | "fleet"`). When `"fleet"`, use `MCPFleetClient.spawn_task()` per agent.

**Code addition**:
```python
async def _dispatch_votes_fleet(
    self, fact: Any, agents: list[str]
) -> list[AgentVote]:
    """Dispatch actual verification tasks to fleet nodes via MCP."""
    from picocloth_cli.fleet.client import MCPFleetClient
    votes = []
    async with MCPFleetClient() as client:
        for agent_id in agents:
            result = await client.spawn_task(
                target_node=agent_id,
                task=f"Verify fact: {fact.triple.claim}\nSources: {[s.url for s in fact.sources]}\nReturn JSON: {{\"verdict\": \"SUPPORT|REFUTE|UNCERTAIN\", \"confidence\": 0.0-1.0, \"justification\": \"...\"}}",
                priority="high",
            )
            # Parse result... (production would parse actual node response)
            votes.append(AgentVote(...))
    return votes
```

**Acceptance criteria**:
- [ ] `verify_fact(fact, dispatch_mode="simulate")` works without fleet
- [ ] `verify_fact(fact, dispatch_mode="fleet")` spawns tasks via MCP
- [ ] Graceful fallback to simulate if fleet unavailable

---

## Step 1.3: Extend `ExtractedFact` for Verification Attachments

**Problem**: `verified_by` dict exists but verification results aren't attached.
**Fix**: In `ExtractEngine`, add method `attach_verification()` that stores `VerificationResult`.

**No schema change needed** — `ExtractedFact.verified_by` is already `dict[str, Any]`.

**Code addition** to `extract.py` tool, in `ExtractEngine` class:
```python
def attach_verification(
    self, facts: list[ExtractedFact], results: list[VerificationResult]
) -> None:
    result_map = {r.fact_id: r for r in results}
    for fact in facts:
        if fact.fact_id in result_map:
            fact.verified_by["fleet_verification"] = result_map[fact.fact_id].to_dict()
            # Update confidence with verification result
            v = result_map[fact.fact_id]
            if v.verdict == "VERIFIED":
                fact.confidence = round(min(0.98, fact.confidence + 0.05), 2)
            elif v.verdict == "REFUTED":
                fact.confidence = round(max(0.0, fact.confidence - 0.20), 2)
```

**Acceptance criteria**:
- [ ] `fact.verified_by["fleet_verification"]` contains `VerificationResult` dict
- [ ] Confidence is adjusted based on verification verdict
- [ ] Refuted facts are marked but not auto-deleted (user decides)

---

## Step 1.4: Update CLI `verify` Command

**File**: `picocloth-cli/src/picocloth_cli/commands/extract.py`

**Current**:
```python
def verify(fact_id: str, nodes: str = "all"):
    # Spawns generic MCP task
```

**New**:
```python
@app.command()
def verify(
    fact_id: str = typer.Argument(..., help="Fact ID to verify"),
    strategy: str = typer.Option("weighted", "--strategy", help="weighted|unanimous|threshold"),
    nodes: str = typer.Option("all", "--nodes", help="Nodes: all or comma-separated"),
    simulate: bool = typer.Option(False, "--simulate", help="Local simulation without fleet"),
):
    """Verify a fact using the Fleet Verification Pool."""
    # 1. Load fact from memory
    # 2. Create FleetVerificationPool
    # 3. Call pool.verify_fact(fact, strategy=strategy)
    # 4. Display vote table with Rich
    # 5. Store result back to memory
```

**Rich display**:
- Table of votes: Agent | Verdict | Confidence | Justification
- Final verdict banner (green=VERIFIED, red=REFUTED, yellow=DISPUTED)
- Credibility-weighted score
- Recommendation if `needs_deep_verification`

**Acceptance criteria**:
- [ ] `picocloth extract verify <fact_id>` runs weighted consensus by default
- [ ] `--strategy unanimous` requires all agents agree
- [ ] `--simulate` works without MCP fleet running
- [ ] Results stored back to `shared/memory/facts/`

---

## Step 1.5: Add `--verify` Flag to `search` and `from-file`

**Code change** in `commands/extract.py`:
- Add `verify: bool = typer.Option(False, "--verify")` to both `search` and `from-file`
- After extraction, if `verify=True`, run `FleetVerificationPool.verify_batch()`
- Store results via `_mcp_store_broadcast()` or local write

**Acceptance criteria**:
- [ ] `picocloth extract search "AI market" --verify` extracts THEN verifies
- [ ] Verified facts have `verified_by` populated in output JSONL

---

## Step 1.6: Register `fleet_verify` MCP Tool

**File**: `mcp-fleet-server/server.py`

**Add to `TOOLS`**:
```python
"fleet_verify": {
    "description": "Verify a fact using fleet multi-agent consensus",
    "parameters": {
        "type": "object",
        "properties": {
            "fact": {"type": "object", "description": "Fact object with fact_id, triple, sources"},
            "strategy": {"type": "string", "enum": ["weighted", "unanimous", "threshold"], "default": "weighted"},
            "nodes": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["fact"]
    }
}
```

**Add handler**:
```python
def verify_fact(fact: dict, strategy: str, nodes: list[str] | None) -> dict:
    # Import verification pool, run simulation (server is sync)
    # Return VerificationResult dict
```

**Acceptance criteria**:
- [ ] MCP client can call `fleet_verify` tool
- [ ] Returns JSON with verdict, confidence, votes

---

## Step 1.7: Skill Documentation

**File**: `shared/doctrine/skills/verification-pool.md`

**Contents**:
- Research citations (4 papers)
- Architecture diagram: Dispatch → Vote → Consensus
- CLI usage examples
- MCP tool reference

**Acceptance criteria**:
- [ ] Document explains WHY each design choice was made
- [ ] Citations linked to paper titles

---

## Step 1.8: Test & Commit

**Test commands**:
```bash
cd /Users/shivaramgoud/picocloth-work
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/verification_pool.py
python3 -m py_compile picocloth-cli/src/picocloth_cli/commands/extract.py
python3 -m py_compile mcp-fleet-server/server.py
python3 -c "from picocloth_cli.tools.verification_pool import FleetVerificationPool; print('OK')"
```

**Commit message**:
```
feat(verification): Fleet Verification Pool v1.0

- Heterogeneous multi-agent verification with learned consensus
- Credibility tracker with exponential decay (30-day half-life)
- Three strategies: weighted (A-HMAD), unanimous, threshold
- Deterministic simulation mode for offline use
- Fleet dispatch mode via MCP spawn_task
- CLI: extract verify --strategy weighted|unanimous|threshold --simulate
- MCP: fleet_verify tool registered

Research: Six Sigma Agent (2026), A-HMAD (Springer 2025),
MAV (Feb 2025), Adversary-Resistant Multi-Agent (Apr 2025)
```
