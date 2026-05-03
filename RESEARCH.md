# 🔬 PicoCloth Research Foundations

> *"We did not guess. We built on shoulders."*

Every architectural decision in PicoCloth is traceable to a research source, production pattern, or peer-reviewed paper. This document is the audit trail.

---

## Core Runtime

### PicoClaw — The Substrate
**Source:** [Sipeed PicoClaw](https://github.com/sipeed/picoclaw)
**Contribution:** The base agent runtime. Runs on ~$10 RISC-V hardware with <10MB RAM. Go-based, JSON-RPC stdio hooks, MCP client support, gateway API.
**Why we chose it:** Most agent frameworks (LangChain, AutoGPT) are Python monoliths that need GBs of RAM. PicoClaw is a lightweight Go binary that can run 10 instances on a single laptop. The hook system (`hook.before_llm`, `hook.after_llm`, `hook.context_compress`) is what enables the Digital Twin Protocol.

---

## Memory Architecture

### Graph Digital — Katelyn Skills OS
**Source:** [graph.digital/guides/ai-agents/memory](https://graph.digital/guides/ai-agents/memory)
**Contribution:** The 4-layer memory architecture: Doctrine (immutable), Project (append-only), State (real-time), Run (ephemeral).
**Why we chose it:** This is a production-proven pattern from a real multi-agent system. It separates concerns that most agent frameworks conflate. The "doctrine" layer specifically solves the "prompt drift" problem where agents gradually forget their core instructions.

### Trey Goff — OpenClaw Memory System
**Source:** [github.com/treygoff24/openclaw-memory-system](https://github.com/treygoff24/openclaw-memory-system)
**Contribution:** Smart compaction with PSM (Pre-Summary Memory) injection, graduated compaction thresholds, and context window management.
**Why we chose it:** PicoClaw's default compaction is naive truncation. Trey's system injects a summary BEFORE compaction so the agent doesn't lose the "thread" of the conversation. We adapted this into the Digital Twin Protocol.

### Steve Kinney — Agent Memory Dynamics
**Source:** [stevekinney.com/writing/agent-memory-systems](https://stevekinney.com/writing/agent-memory-systems)
**Contribution:** Memory lifecycle theory: encoding → storage → retrieval → forgetting. The concept of "memory pressure" as a trigger for compaction decisions.
**Why we chose it:** Kinney's framework gave us the vocabulary to design the Digital Twin Guardian. The 75% threshold is derived from his "pressure point" concept.

### Claude Code — File-Based Agent Memory
**Source:** arXiv:2604.14228v1 — *"Claude Code: Agent Teams with Filesystem Memory"* (Anthropic, 2026)
**Contribution:** Agent teams that use the filesystem as shared memory instead of databases. Lock-file coordination for concurrency. Atomic writes via temp-file-rename.
**Why we chose it:** We deliberately avoided Redis, Postgres, or vector DBs for the core memory system. Filesystem-based memory is debuggable (`cat shared/project/facts/foo.jsonl`), version-controllable, and requires zero infrastructure. The lock-file pattern (`fcntl.flock`) comes directly from this paper.

### Context Engineering Toolkit — Graduated Compaction
**Source:** arXiv:2604.08290v1 — *"Graduated Context Compaction for Long-Horizon Agents"* (2026)
**Contribution:** 5-layer compaction pipeline: zone-based pruning → observation masking → summarization → digital twin creation → archive.
**Why we chose it:** Our `compaction.py` implements this exact pipeline. Instead of one big truncation, we prune redundant observations, mask sensitive data, generate a summary, create a twin, and archive.

---

## Inter-Agent Communication

### Model Context Protocol (MCP)
**Source:** [modelcontextprotocol.io](https://modelcontextprotocol.io)
**Contribution:** Standardized protocol for agents to discover and call tools. JSON-RPC over stdio or HTTP. Server exposes `tools/list` and `tools/call`.
**Why we chose it:** Before MCP, every agent framework invented its own tool-calling protocol. MCP gives us interop. Our `mcp-fleet-server/server.py` is a pure-Python MCP server that any MCP-compliant client can talk to — not just PicoClaw.

### Eric Grill — PicoClaw Fleet Manager
**Source:** [github.com/EricGrill/picoclaw-fleet](https://github.com/EricGrill/picoclaw-fleet)
**Contribution:** SSH-based multi-node deployment, health checking, and task delegation patterns.
**Why we chose it:** Eric proved that PicoClaw can run in fleets. We extended his SSH-based approach with a local MCP-based bus so nodes can communicate without network configuration.

---

## Observability

### Langfuse — Open-Source LLM Observability
**Source:** [github.com/langfuse/langfuse](https://github.com/langfuse/langfuse)
**Contribution:** Traces, spans, generations, scores, cost tracking, session grouping. Self-hostable via Docker Compose.
**Why we chose it:** You cannot run a 10-node fleet without observability. Langfuse is the only open-source tool that traces the full agent execution path (not just the LLM call). The `langfuse_bridge.py` hook maps PicoClaw's event system to Langfuse's trace model.

---

## Agent Behavior & Persona

### OpenClaw Issue #7175 — Pre-Compaction Hooks
**Source:** [github.com/openclaw/openclaw/issues/7175](https://github.com/openclaw/openclaw/issues/7175)
**Contribution:** The concept of firing a hook BEFORE context compaction to preserve knowledge.
**Why we chose it:** This issue is the origin of our Digital Twin Protocol. The community discussion shaped our implementation: extract facts, save snapshots, update project memory, THEN compact.

### AetherLink — Enterprise Multi-Agent Patterns
**Source:** [aetherlink.ai](https://aetherlink.ai)
**Contribution:** Patterns for fleet orchestration: load balancing, node specialization, task delegation, emergent behavior.
**Why we chose it:** AetherLink's "specialist swarm" pattern is exactly what our 10-node architecture implements. Their "router node" concept became our Node-I (Fleet Router).

### AgentSpawn — Intent-Driven Dynamic Spawning
**Source:** arXiv:2602.07072v1 — *"AgentSpawn: Dynamic Agent Generation for Complex Tasks"* (2026)
**Contribution:** 34% improvement in task completion by dynamically spawning specialized subagents based on intent classification and complexity evaluation.
**Why we chose it:** Our `intent/` module directly implements this paper's pipeline: `classify_intent()` → `evaluate_complexity()` → `should_spawn()` → `spawn_agent()`. The complexity metrics (file_count, cyclomatic, uncertainty, unfamiliarity) are from this work.

### Big Five + Psychometric Persona Modeling
**Source:** Multiple; synthesized from personality psychology literature
**Contribution:** The modular digital twin persona uses Big Five trait vectors (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) with 30 sub-facets. The formal tuple interface `M = (C, S, I, O, τ, γ)` enables composable personas.
**Why we chose it:** Most AI personas are monolithic prompt walls. They drift. Our modular approach (meta, identity, voice, skills, combinatorics, process) lets us version, test, and compose personas like software modules.

---

## CLI & Tooling

### Typer — Type-Hinted CLI Framework
**Source:** [typer.tiangolo.com](https://typer.tiangolo.com)
**Contribution:** Python CLI framework built on Click. Automatic help generation, type validation, tab completion.
**Why we chose it:** The PicoCloth CLI has 7 subcommand groups (`fleet`, `chat`, `task`, `agent`, `memory`, `twin`, `config`) with ~30 commands. Typer keeps this manageable without boilerplate.

### Rich + Textual — Terminal UI
**Source:** [github.com/Textualize/rich](https://github.com/Textualize/rich) and [github.com/Textualize/textual](https://github.com/Textualize/textual)
**Contribution:** Rich: tables, markdown, syntax highlighting, progress bars. Textual: reactive TUI widgets, CSS-like styling.
**Why we chose it:** `picocloth fleet status` uses Rich tables. `picocloth fleet monitor` uses Textual for a live dashboard with auto-refresh. This is the best terminal UX available in Python.

### OpenHands V1 SDK
**Source:** arXiv:2511.03690v1 — *"OpenHands: An Open Platform for AI Software Developers"* (2025)
**Contribution:** Agent SDK patterns, action-observation loops, runtime environment design.
**Why we chose it:** Our agent spawning and memory slicing patterns are influenced by OpenHands' runtime design.

---

## Research Gaps — What We're Still Exploring

| Gap | Current Approach | What We Need |
|-----|-----------------|-------------|
| **Semantic search** | Full-text grep across JSON files | Vector DB (Chroma, Qdrant, or pgvector) for semantic twin search |
| **GAN-like training** | Manual contradiction detection (Node-F) | Automated adversarial training between curiosity and safety nodes |
| **Model routing** | Hardcoded per-node model lists | Dynamic classifier that routes to optimal model based on task type |
| **Sleep/wake scheduling** | Always-on | Cost-optimal scheduling based on predicted workload |
| **Cross-machine distribution** | Single-machine localhost | Distributed fleet with network-based MCP transport |

---

## Citation Format

When contributing to PicoCloth, cite your sources:

```markdown
## Decision: Why we use file-based locking
**Citation:** Anthropic, "Claude Code Agent Teams" (arXiv:2604.14228v1, Feb 2026)
**Rationale:** Postgres would require infrastructure. Filesystem locking is debuggable and zero-dependency.
```

---

> *"Science is what we have learned about how not to fool ourselves."* — Richard Feynman
>
> *This architecture is our best attempt not to fool ourselves.*
