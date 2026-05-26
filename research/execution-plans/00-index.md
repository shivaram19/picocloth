# Gap Fill Execution Plans — Index

## Context
Systematic gap filling between PicoCloth and parallel-agent-skills. Every gap filled is backed by research (academia/industry) before implementation.

## Gap Status

| # | Gap | Status | Execution Plan | Research |
|---|-----|--------|---------------|----------|
| 1 | Structured fact extraction | ✅ Done | — | FActScore, VeriScore |
| 2 | Confidence scoring | ✅ Done | — | VERITAS-NLI, Mem0 |
| 3 | Cross-reference | ✅ Done | — | SAFE, Nature 2026 |
| 4 | Temporal validity | ✅ Done | — | Mem0 temporal |
| 5 | Multi-agent verification | 🔄 Ready | [01-verification-pool.md](01-verification-pool.md) | Six Sigma Agent, A-HMAD, MAV |
| 6 | Memory architecture | ✅ Done | — | Mem0 |
| 7 | Query optimization | 🔄 Ready | [03-retrospective-optimizer.md](03-retrospective-optimizer.md) | ConvSearch-R1, Nogueira & Cho |
| 8 | Platform intelligence | ✅ Done | — | Academic search lit |
| 9 | Citation association | 🔄 Ready | [02-citation-validator.md](02-citation-validator.md) | LiveResearchBench, Deerflow+ |
| 10 | Fleet-native MCP | ✅ Done | — | MCP protocol spec |
| 11 | Monitoring / webhooks | 🔄 Ready | [05-topic-monitor.md](05-topic-monitor.md) | EDA patterns, Pirolli & Card |
| 12 | Indie web discovery | 🔄 Ready | [04-indie-discovery.md](04-indie-discovery.md) | Schultheiß et al., Marginalia |

## Execution Order

1. **Core tools** (parallelizable):
   - `verification_pool.py` — Step 1.1-1.2
   - `citation_validator.py` — Step 2.1
   - `retrospective_optimizer.py` — Step 3.1-3.2
   - `indie_discovery.py` — Step 4.1-4.3
   - `topic_monitor.py` — Step 5.1-5.2

2. **Integration** (sequential):
   - `extract.py` tool — Step 6.1
   - `extract.py` commands — Step 6.2
   - `search.py` commands — Step 6.3
   - MCP fleet server — Step 6.4

3. **Documentation** (parallelizable):
   - 5 skill docs — Step 6.5

4. **Testing & commit**:
   - Compile test — Step 6.6
   - Smoke test — Step 6.6
   - Git commit — Step 6.7

## Files to Create

```
picocloth-cli/src/picocloth_cli/tools/
  ├── verification_pool.py      (exists, needs fixes)
  ├── citation_validator.py     (exists, needs fixes)
  ├── retrospective_optimizer.py (new)
  ├── indie_discovery.py         (new)
  └── topic_monitor.py           (new)

picocloth-cli/src/picocloth_cli/commands/
  ├── extract.py                 (modify)
  └── search.py                  (modify)

mcp-fleet-server/
  └── server.py                  (modify)

shared/doctrine/skills/
  ├── verification-pool.md       (new)
  ├── citation-validator.md      (new)
  ├── retrospective-optimizer.md (new)
  ├── indie-discovery.md         (new)
  └── topic-monitor.md           (new)

shared/doctrine/
  └── indie-web-registry.json    (new)
```

## Cost Constraints Check

| Constraint | Status |
|-----------|--------|
| Zero new infrastructure | ✅ All local Python + JSONL |
| Minimize LLM calls | ✅ Verification simulates by default; LLM only in Deep Lane |
| Must run on $10 hardware | ✅ No new services; daemon is optional foreground loop |
| Zero new SaaS dependencies | ✅ Only OpenAI API (already configured) |

## Research Citations per Gap

- **Gap 5**: Six Sigma Agent (arXiv:2601.22290), A-HMAD (Springer s44443-025-00353-3), MAV (Feb 2025), Adversary-Resistant Multi-Agent (arXiv:2505.24239)
- **Gap 9**: LiveResearchBench (arXiv:2510.14240), Deerflow+ (Appendix D), DEFT Taxonomy (Zhang et al. Dec 2025)
- **Gap 11**: ConvSearch-R1 (arXiv:2505.15776), Nogueira & Cho (EMNLP 2017), Retroformer/TRICE, Pirolli & Card (1999)
- **Gap 13**: Schultheiß et al. (2022), Marginalia Search, IndieWeb community, SearXNG
- **Gap 9 (orig)**: Event-driven architecture patterns, Information Foraging Theory
