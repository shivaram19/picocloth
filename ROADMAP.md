# 🗺️ PicoCloth Roadmap

> *"We know where we are. We know where we're going. Here is the map between."*

---

## Phase 1: Foundation ✅ COMPLETE

**Goal:** Prove that multiple PicoClaw nodes can share memory and communicate.

### What Works Today

| Component | Status | Evidence |
|-----------|--------|----------|
| 4-layer shared memory | ✅ | `shared/` hierarchy with doctrine, project, state, run, digital-twins, compaction-archive |
| Digital Twin Protocol | ✅ | `hooks/digital_twin_guardian.py` extracts facts and saves snapshots at 75% context usage |
| MCP Fleet Server | ✅ | `mcp-fleet-server/server.py` exposes 6 fleet-wide tools over stdio |
| Fleet orchestrator | ✅ | `scripts/ram-optimized-launch.py` launches 10 nodes with RAM-optimized configs |
| Health monitoring | ✅ | `scripts/orchestrator-10node.sh` polls all 10 gateway ports and updates `fleet-state.json` |
| Langfuse integration | ✅ | `hooks/langfuse_bridge.py` traces all LLM calls and tool executions |
| Python CLI | ✅ | `picocloth-cli/` — Typer-based CLI with fleet management, chat, task spawning, memory CRUD, twin search |
| Telegram integration | ✅ | `docs/TELEGRAM_SETUP.md` — bot creation, config format, routing patterns |
| Outreach engine | ✅ | `shared/project/outreach/` — full LinkedIn outreach product built on the fleet |
| VDC document intelligence | ✅ | `shared/project/documents/` + `shared/doctrine/skills/vdc-document-intelligence.md` |

### Phase 1 Nodes
- **Node-A** (Curiosity Brain, port 18790) — Research, web search, subagent spawning
- **Node-B** (Executor, port 18791) — Code, build, test, deploy

### Phase 1 Scale
- **Machines:** 1
- **Nodes:** 2 active (10 configured)
- **Context window:** 32K (RAM-optimized)
- **Max tokens:** 2K
- **Tool iterations:** 3

---

## Phase 2: Scale 🔄 IN PROGRESS

**Goal:** Expand to 5 active nodes, add load balancing, and enable Telegram production use.

### Deliverables

| Feature | Status | Owner | Notes |
|---------|--------|-------|-------|
| **Node-C: Memory Guardian** | 🔄 | Fleet | Dedicated to long-term memory management. Offloads memory tasks from A and B. |
| **Node-D: Safety Auditor** | 🔄 | Fleet | Reviews shell commands, spawn requests, doctrine writes. Approval gate. |
| **Node-E: Document Parser** | 🔄 | Fleet | PDF, CAD, spec extraction. Structured data output. |
| **Load balancer / router** | 📝 | Node-I | Route incoming tasks to the optimal node based on intent classification. |
| **GAN-like adversarial training** | 📝 | Research | Curiosity node proposes; safety node critiques. Iterative improvement loop. |
| **Custom classifier for model routing** | 📝 | ML | Train a lightweight classifier to choose `grok-4.20-reasoning` vs `grok-4.1-fast` per-task. |
| **Telegram production deployment** | 🔄 | Ops | Single-bot routing, `/spawn`, `/tasks`, `/memory` commands. |
| **Vector DB integration** | 📝 | Memory | Semantic search across digital twins and project facts. |

### Phase 2 Scale
- **Machines:** 1-2
- **Nodes:** 5 active
- **Context window:** 64K (gradual increase as RAM allows)
- **Max tokens:** 4K
- **Tool iterations:** 5

### Phase 2 Definition of Done
- [ ] All 5 nodes stay online for 7 days without manual restart
- [ ] Task delegation from Node-A to Node-C/D/E succeeds >95% of the time
- [ ] Telegram bot handles 100 messages/day without lag
- [ ] Vector DB enables semantic twin search with <500ms latency
- [ ] Safety Auditor catches 100% of flagged shell commands

---

## Phase 3: Intelligence

**Goal:** Full 10-node mesh with self-improving behavior and automatic skill generation.

### Deliverables

| Feature | Description |
|---------|-------------|
| **Self-improving curiosity loop** | Node-A automatically identifies knowledge gaps, spawns research subagents, and writes new skills to `shared/doctrine/skills/` |
| **Automatic skill generation** | When 3+ nodes encounter the same unknown, auto-generate a skill markdown file with YAML frontmatter |
| **Cross-node SubTurn delegation** | A single user message can trigger a cascade: Router → Curiosity → Executor → Safety, with full traceability |
| **Sleep/wake scheduling** | Nodes auto-sleep during low-load periods and wake on incoming tasks. Cost optimization. |
| **Node-F: Contradiction Detector** | Cross-reference multiple documents and flag conflicting data automatically |
| **Node-G: RFI Drafter** | Generate construction industry RFIs from document analysis |
| **Node-H: Knowledge Graph Builder** | Maintain live entity-relationship graphs from extracted facts |
| **Node-J: Metrics Collector** | Real-time cost tracking, token usage, latency histograms, success rates |

### Phase 3 Scale
- **Machines:** 2-3
- **Nodes:** 10 active
- **Context window:** 128K
- **Max tokens:** 8K
- **Tool iterations:** 10

### Phase 3 Definition of Done
- [ ] Fleet generates ≥1 new skill per week without human intervention
- [ ] SubTurn delegation completes end-to-end in <30 seconds
- [ ] Sleep/wake scheduling reduces costs by ≥30%
- [ ] Knowledge graph contains >1000 entities with >95% accuracy
- [ ] 30-day uptime with zero manual restarts

---

## Phase 4: Autonomy

**Goal:** Distributed across multiple machines with self-healing and emergent behavior.

### Deliverables

| Feature | Description |
|---------|-------------|
| **Distributed fleet** | Nodes run across 5+ machines, communicating over network-based MCP transport |
| **Self-healing node replacement** | If a node dies, the fleet automatically spawns a replacement and restores its memory from digital twins |
| **Emergent collective behavior** | Nodes develop coordination patterns not explicitly programmed (e.g., spontaneous load balancing) |
| **Human-in-the-loop governance** | Web dashboard for approving doctrine changes, reviewing safety flags, and steering fleet priorities |
| **Custom model fine-tuning** | Train small fine-tuned models for specific node roles (e.g., a "contradiction detection" LoRA) |
| **Node-K through Node-Z** | Scale beyond 10 nodes. Specialized nodes for domains: legal, medical, finance, creative |

### Phase 4 Scale
- **Machines:** 5+
- **Nodes:** 25+
- **Context window:** 2M (full model capability)
- **Max tokens:** 32K
- **Tool iterations:** 15

### Phase 4 Definition of Done
- [ ] Fleet self-heals from 2 simultaneous node failures in <60 seconds
- [ ] New node onboarding takes <5 minutes (copy config, start, auto-register)
- [ ] Emergent behavior documented and reproducible
- [ ] Web dashboard used by >10 humans for governance
- [ ] 99.9% uptime over 90 days

---

## Research & Development Tracks

These span across all phases:

| Track | Current | Target | Phase |
|-------|---------|--------|-------|
| **Semantic Memory** | Full-text grep | Vector DB + hybrid search | 2 |
| **Digital Twin Extraction** | Rule-based (regex) | LLM-based extraction with confidence scores | 2 |
| **Cost Optimization** | Manual monitoring | Auto sleep/wake + model routing | 3 |
| **Persona Evolution** | Static markdown modules | Self-updating trait vectors based on interaction history | 3 |
| **Multi-Modal** | Text only | Image + PDF ingestion for Node-E | 3 |
| **Edge Deployment** | Laptop/server | $10 RISC-V hardware per node | 4 |

---

## Milestone Timeline

| Date | Milestone |
|------|-----------|
| 2026-Q2 | Phase 1 complete — 2-node stable fleet, CLI v1.0, documentation complete |
| 2026-Q3 | Phase 2 — 5 nodes, Telegram production, vector DB semantic search |
| 2026-Q4 | Phase 3 — 10-node mesh, auto skill generation, sleep/wake scheduling |
| 2027-Q1 | Phase 4 — Distributed fleet, self-healing, emergent behavior research |

---

## How to Contribute to the Roadmap

1. **Pick a phase** that excites you
2. **Open an issue** describing your approach
3. **Reference research** (see `RESEARCH.md`)
4. **Submit a PR** against the relevant component

We especially need help with:
- **Phase 2:** Vector DB integration (Chroma, Qdrant, or pgvector)
- **Phase 2:** Custom classifier training pipeline
- **Phase 3:** Automatic skill generation logic
- **Phase 3:** Sleep/wake scheduling algorithm
- **Phase 4:** Network-based MCP transport

---

> *"The best time to plant a tree was 20 years ago. The second best time is now."*
>
> *The best time to build a fleet was yesterday. The second best time is today.* 🚀
