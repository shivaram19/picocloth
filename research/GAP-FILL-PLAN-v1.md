# Gap Fill Plan v1.0 — parallel-agent-skills vs PicoCloth

> Every gap filled is backed by research before implementation.
> THINK FIRST → RESEARCH → PLAN → EXECUTE.

## Gap Status Matrix

| # | Gap | parallel-agent-skills | PicoCloth Status | Research | Action |
|---|-----|----------------------|------------------|----------|--------|
| 1 | Structured fact extraction | Raw snippets only | ✅ THEE v1.0 | FActScore, VeriScore, Neural OIE | DONE |
| 2 | Confidence scoring | None | ✅ Source tier + type bonus | VERITAS-NLI, Mem0 | DONE |
| 3 | Cross-reference | None | ✅ CrossReferenceEngine | SAFE, Nature 2026 | DONE |
| 4 | Temporal validity | None | ✅ valid_from/until/superseded | Mem0 temporal | DONE |
| 5 | **Multi-agent verification** | Single-agent pipeline | 🔄 Basic MCP verify | **Six Sigma Agent, A-HMAD, MAV** | **FILL NOW** |
| 6 | Memory architecture | Ephemeral | ✅ Mem0-style ADD/UPDATE/DELETE/NOOP | Mem0 paper | DONE |
| 7 | Query optimization | Generic search | ✅ SearchStrategyEngine | Pirolli & Card, Bioptic Agent | DONE |
| 8 | Platform intelligence | No targeting | ✅ Platform registry with yield tiers | Academic search lit | DONE |
| 9 | **Citation association quality** | Inline links, no structure | 🔄 Basic Source dataclass | **LiveResearchBench, Deerflow+** | **FILL NOW** |
| 10 | Fleet-native MCP | Commercial SaaS only | ✅ Zero-dep stdio JSON-RPC | MCP protocol spec | DONE |
| 11 | **Yield tracking / retrospective optimization** | No learning | 🔄 Basic YieldTracker | **ConvSearch-R1, Retroformer, Nogueira & Cho** | **FILL NOW** |
| 12 | Source diversification | Single engine | ✅ Multiple strategies | Information Foraging | DONE |
| 13 | **Indie web / expert blog discovery** | SEO-dominated | ❌ Not implemented | **Marginalia, Schultheiß et al.** | **FILL NOW** |
| 14 | Terminology expansion | None | ✅ Query plan builder | Academic search lit | DONE |
| 15 | Query template library | Ad-hoc | ✅ Template patterns | Bioptic Agent | DONE |

---

## Gap 5: Multi-Agent Verification

### Research Backing

**Six Sigma Agent (Jan 2026, arXiv:2601.22290)**
- "Atomic task decomposition enabling effective voting"
- "Dynamic scaling when initial votes are contested"
- ICE framework (Omar et al., 2025) improved GPQA-diamond from 46.9% to 68.2% — 45% relative gain
- Probabilistic Consensus: precision from 73.1% → 93.9% with 2 models, 95.6% with 3

**A-HMAD (Springer 2025, s44443-025-00353-3)**
- Heterogeneous agent ensemble: "Verifier" + "Solver" roles
- Learned consensus module: 78% vs 68% majority vote in disagreements — 31% relative error reduction
- GSM8K: 90.2% vs 84.0% standard debate, vs 77.0% single CoT
- Biography facts: incorrect facts per bio cut by 45%

**Multi-Agent Verification / MAV (Feb 2025)**
- "Novel dimension for scaling test-time compute: increasing verifiers rather than model size"
- Aspect Verifiers with binary True/False approvals
- BoN-MAV stronger scaling than self-consistency and reward model verification

**Adversary-Resistant Multi-Agent (Apr 2025, arXiv:2505.24239)**
- Credibility scoring per agent based on historical accuracy
- Self-refinement before voting: agents track own errors, measure variance, trigger self-reflection

### Design

Build `FleetVerificationPool`:
1. **Heterogeneous dispatch**: Route facts to consultants by type
   - `consultant-academic` → research facts
   - `consultant-solutions` → business/technical facts
   - `consultant-growth` → market/competitive facts
   - `consultant-trainer` → educational/tutorial facts
   - `curious-kimi` → general/cross-domain facts
2. **Weighted voting**: Each consultant votes with confidence + justification
3. **Learned consensus**: Weight consultants by historical accuracy on fact types
4. **Credibility decay**: Older verification votes decay; recent ones weighted higher
5. **Disagreement resolution**: When votes split, trigger deep verification with all agents

### Implementation

- File: `picocloth-cli/src/picocloth_cli/tools/verification_pool.py`
- CLI: Extend `picocloth extract verify` with `--strategy=weighted|unanimous|threshold`
- Integration: Add `verify_with_fleet()` to `ExtractEngine`

---

## Gap 9: Citation Association Quality

### Research Backing

**LiveResearchBench (Salesforce AI Research, 2026, arXiv:2510.14240)**
- "Models struggle most with citation correctness and formatting, rather than surface fluency"
- Key failure modes observed across ALL 17 evaluated systems:
  1. Mismatched in-text citations and references
  2. Missing or incomplete URLs
  3. Inconsistent citation formats
  4. Uncited references appearing in bibliography
  5. Broken or incomplete table formatting
  6. Out-of-order reference numbering
- E3 errors (unsupported claims — claim not verifiable from cited link) dominate in wide search
- Open Deep Research averages 91.9 unsupported claims per market analysis report
- Multi-agent systems lead in Citation Association (Deerflow+: 77.0, Open Deep Research: 76.9)
- Single-agent deep research lags (OpenAI o3: 25.6, o4-mini: 27.2)

**Deerflow+ Stabilization (Appendix D)**
- Added inline-citation support + validation pass
- Enforces one-to-one mapping between in-text citations and reference entries
- Checks numbering continuity and duplicates
- Result: "higher information retention, stronger evidence structuring with inline citations"

**DEFT Taxonomy (Zhang et al., Dec 2025)**
- Retrieval failures: 33.10% of all failures
- Generation failures: 38.76% (including Strategic Content Fabrication at 18.95%)
- Low-authority citation is a specific retrieval failure mode

### Design

Build `CitationValidator`:
1. **URL health check**: Verify each source URL is reachable (HEAD request, 200/301/302 OK)
2. **Inline citation mapping**: Every claim must have ≥1 source; every source must support ≥1 claim
3. **Format consistency**: Enforce single citation format (APA-ish inline + URL)
4. **Duplicate detection**: Deduplicate URLs by canonical form
5. **Unsupported claim flagging**: When a claim has no matching source content, flag as E3
6. **Reference numbering**: Auto-assign and validate sequential reference numbers

### Implementation

- File: `picocloth-cli/src/picocloth_cli/tools/citation_validator.py`
- Extend `Source` dataclass with `reference_number`, `accessed_at`, `status_code`
- Extend `ExtractedFact` with `citation_errors` list
- CLI: Add `picocloth extract validate-citations` command
- Integration: Run validator after `ExtractEngine.run()` when `--validate-citations` flag

---

## Gap 11: Yield Tracking & Retrospective Optimization

### Research Backing

**ConvSearch-R1 (Zhu et al., May 2025, arXiv:2505.15776)**
- "Self-driven framework eliminating external rewrite supervision"
- Two-stage: Self-Driven Policy Warm-Up + Retrieval-Guided RL
- Rank-incentive reward shaping overcomes metric sparsity
- 10%+ improvement on TopiOCQA with 3B parameter model
- Key insight: optimize reformulation directly through retrieval signals

**Nogueira & Cho (2017, EMNLP — Task-Oriented Query Reformulation with RL)**
- RL-based query reformulation: actions = selecting terms, reward = document recall
- 5-20% relative improvement in recall over strong baselines
- RL-RNN-SEQ produces 3× shorter queries with comparable performance
- "Only a small subset of terms are useful for reformulation"

**Retroformer / TRICE / SimpleTIR (2024-2025)**
- "Agents learn from retrospective execution feedback"
- Credit assignment across long tool-use chains
- "Reflection as explicit action inside RL loop"

**Pirolli & Card (1999)**
- Information Foraging Theory: users optimize information gain per unit cost
- "Information scent" guides patch selection
- Applied to search: query reformulation should maximize yield per query

### Design

Build `RetrospectiveOptimizer`:
1. **Yield database**: SQLite or JSONL tracking every search → facts → confidence chain
2. **Reward function**: `R = facts_extracted × avg_confidence / query_count`
3. **Pattern scoring**: Track yield per query template, platform, terminology set
4. **Auto-reformulation**: When yield drops below threshold, suggest reformulated queries
5. **Query template optimization**: Learn which template patterns produce highest yield per topic type
6. **Decay old data**: Exponential decay on historical yields (recent searches weighted higher)

### Implementation

- File: `picocloth-cli/src/picocloth_cli/tools/retrospective_optimizer.py`
- Extend `SearchStrategyEngine` with `record_yield()` and `suggest_reformulation()`
- CLI: Add `picocloth search optimize` command
- Integration: Auto-record yield after every `extract search` run

---

## Gap 13: Indie Web / Expert Blog Discovery

### Research Backing

**Schultheiß et al. (2022) — SEO vs Content Quality**
- "Non-optimized, but high-quality content may be outranked by optimized content"
- SEO-optimized content dominates commercial search results
- Expert blogs, personal websites, and self-hosted content are systematically under-ranked

**Marginalia Search (Viktor Lofgren)**
- Independent DIY search engine prioritizing "grass fed, free range HTML"
- Filters tracking, no data sharing, no long-term IP retention
- "Minority report that keeps [corporate searches] honest"
- Explore mode for random discovery of high-quality independent sites

**Creative Article: "Searching the indieweb" (Dec 2025)**
- "Corporate web is doomed, but the indieweb is thriving"
- Need for "accessible tools to surface content from real people"
- Multiple alternative search engines exist specifically for indieweb discovery

**SearXNG**
- Metasearch engine aggregating from multiple sources
- No tracking, no profiling
- Can be self-hosted

### Design

Build `IndieWebDiscoveryEngine`:
1. **Expert blog registry**: Curated list of high-quality expert blogs by domain
2. **Newsletter directories**: Substack, Buttondown, Revue, Ghost self-hosted
3. **Self-hosted content**: GitHub Pages, Neocities, Bear Blog, Write.as
4. **Academic indies**: Personal academic pages, lab blogs, course notes
5. **Discovery sources**: Marginalia API, HN Algolia, Lobsters, IndieWebRing
6. **Quality heuristics**: Plain HTML, no tracking scripts, old domain age, RSS feed present, no ads

### Implementation

- File: `picocloth-cli/src/picocloth_cli/tools/indie_discovery.py`
- CLI: Add `picocloth search discover` command
- Integration: Add `indie` mode to `SearchStrategyEngine`
- Registry: JSON file with categorized expert sources

---

## Execution Order

1. `verification_pool.py` — Fleet multi-agent verification
2. `citation_validator.py` — Citation quality enforcement
3. `retrospective_optimizer.py` — Yield learning + query optimization
4. `indie_discovery.py` — Expert blog + indie web discovery
5. CLI integration in `extract.py` and `search.py`
6. MCP fleet server tool registration
7. Research docs + commit

---

## Cost Constraints

- Zero new infrastructure (runs on existing VMs)
- Minimize LLM calls (verification uses rule-based where possible)
- All tools are local Python, no external SaaS dependencies beyond OpenAI API (already configured)
- SQLite for yield database (no new database server)
