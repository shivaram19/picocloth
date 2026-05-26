# Skill: Fleet Verification Pool v1.0

## Research

- **Six Sigma Agent** (arXiv:2601.22290, Jan 2026): Consensus-driven decomposed execution. ICE framework improved GPQA-diamond from 46.9% to 68.2% — a 45% relative gain. Key insight: atomic task decomposition enables effective voting.

- **A-HMAD** (Springer s44443-025-00353-3, 2025): Heterogeneous debate with learned consensus. 78% correctness vs 68% majority vote in disagreements — 31% relative error reduction. GSM8K: 90.2% vs 84.0% standard debate.

- **MAV** (Feb 2025): "Increasing verifiers rather than model size" as a scaling dimension. Aspect Verifiers with binary True/False approvals.

- **Adversary-Resistant Multi-Agent** (arXiv:2505.24239, Apr 2025): Credibility scoring per agent based on historical accuracy. Self-refinement before voting.

## Architecture

```
Fact → Heterogeneous Dispatch → Per-Agent Verification → Weighted Voting
→ Learned Consensus → VerificationResult
```

**Heterogeneous dispatch**: Facts are routed to consultants by type:
- `consultant-academic` → research/scientific facts
- `consultant-solutions` → business/technical facts
- `consultant-growth` → market/competitive facts
- `consultant-trainer` → educational facts
- `curious-kimi` → general/cross-domain facts

**Learned consensus** (A-HMAD): Not simple majority. Each agent's vote is weighted by:
1. Base role weight (academic = 1.2, generalist = 0.9)
2. Historical accuracy on that fact type (30-day exponential decay)
3. Agent's own confidence in its vote

**Credibility decay**: Older verification votes decay with a 30-day half-life. Recent accuracy matters more.

## CLI Usage

```bash
# Verify a fact with weighted consensus (default)
picocloth extract verify <fact-id>

# Use unanimous consensus (all must agree)
picocloth extract verify <fact-id> --strategy unanimous

# Use threshold consensus (simple majority)
picocloth extract verify <fact-id> --strategy threshold

# Local simulation without fleet
picocloth extract verify <fact-id> --simulate

# Verify during extraction
picocloth extract search "topic" --verify
picocloth extract from-file results.json --verify
```

## MCP Tool

- **Tool**: `fleet_verify`
- **Parameters**: `fact` (object), `strategy` (string), `nodes` (array)
- **Returns**: `{fact_id, verdict, confidence, votes, consensus_method}`

## Why This Design

We chose **heterogeneous dispatch** over uniform voting because A-HMAD showed that domain-aligned agents produce more reliable votes. A generalist voting on a medical claim is less reliable than an academic expert.

We chose **learned consensus** over majority vote because A-HMAD's experiments showed 78% vs 68% correctness in disagreements when using learned weights. The minority view is sometimes correct — the consensus module learns when to trust it.

We chose **deterministic simulation** as the default mode because real fleet verification requires running 5 consultant nodes with LLM access, which is expensive. The simulation provides immediate value while the fleet integration is opt-in.
