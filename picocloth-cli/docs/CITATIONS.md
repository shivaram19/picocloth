# Bibliography

Complete research bibliography for PicoCloth-CLI architectural decisions.

---

## Core Agent Architecture

### Anthropic — "Building Effective Agents" (Dec 2024)
- **URL:** https://www.anthropic.com/research/building-effective-agents
- **Contribution:** Five composable workflow patterns (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer). Agents vs. workflows distinction. Simplicity principle.
- **Used in:** Intent taxonomy, orchestrator-workers pattern, routing design

### "The Design Space of Today's and Future AI Agent Systems" (2026)
- **Source:** arXiv:2604.14228v1
- **URL:** https://arxiv.org/html/2604.14228v1
- **Contribution:** Claude Code architecture analysis via source code. AsyncGenerator queryLoop. Sidechain transcript design. File-lock coordination. Five-layer graduated compaction taxonomy.
- **Used in:** Streaming design, memory architecture, compaction pipeline, file coordination

### "Context Engineering for AI Agents: Memory vs. Compaction vs. Tool Clearing"
- **URL:** https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools
- **Contribution:** Three primitives: compaction, tool-result clearing, memory. Context engineering ≠ memory engineering.
- **Used in:** Compaction pipeline, observation masking

### "A Context Engineering Toolkit for AI Coding Assistants" (2026)
- **Source:** arXiv:2604.08290v1
- **URL:** https://arxiv.org/html/2604.08290v1
- **Contribution:** Context rot research. Per-file relevance scoring. Graduated compaction pipeline. Zone-based pruning.
- **Used in:** Compaction pipeline, zone-based pruning

---

## Multi-Agent Systems & Spawning

### "AgentSpawn: Adaptive Multi-Agent Collaboration Through Dynamic Spawning" (Feb 2026)
- **Source:** arXiv:2602.07072v1
- **URL:** https://arxiv.org/html/2602.07072v1
- **Contribution:** Runtime agent spawning (not static workflows). Memory slicing algorithm (42% overhead reduction). Spawn package spec. 34% completion improvement over static baselines.
- **Used in:** Agent spawner, spawn packages, memory slicing, complexity metrics

### "Task-Adaptive Multi-Agent Orchestration in the Era of LLM Performance Convergence" (2024)
- **Source:** arXiv:2602.16873
- **URL:** https://arxiv.org/html/2602.16873
- **Contribution:** Orchestration structure as primary performance lever. Dynamic topology based on task characteristics.
- **Used in:** Intent resolution engine, dynamic routing

### "ToolSelf: Unifying Task Execution and Self-Reconfiguration" (2026)
- **Source:** arXiv:2602.07883v1
- **URL:** https://arxiv.org/html/2602.07883v1
- **Contribution:** Tool-driven intrinsic adaptation. Agents reconfigure schemas at runtime.
- **Used in:** Adaptive spawning design

---

## Communication & Protocols

### Model Context Protocol Specification
- **URL:** https://modelcontextprotocol.io
- **Contribution:** Standardized agent-tool interface. Stdio + HTTP transports. Enterprise default-on.
- **Used in:** MCP fleet client, tool definitions

### "Enhancing MCP with Context-Aware Server Collaboration" (2026)
- **Source:** arXiv:2601.11595v2
- **URL:** https://arxiv.org/html/2601.11595v2
- **Contribution:** Context-aware MCP server collaboration reduces repeated inference. Prevents context loss between steps.
- **Used in:** Fleet client design

### "agent-fleet: Orchestrate Multiple AI CLIs as a Team" (2026)
- **URL:** https://github.com/Luxuzhou/agent-fleet
- **Contribution:** MCP-native fleet orchestration. Role-based tool routing. Poll-based task queue. Streamable HTTP transport.
- **Used in:** Fleet commands, task queue, HTTP client

---

## Memory & Knowledge Base

### Graph Digital — "Katelyn Skills OS — 4-Layer Memory Architecture"
- **URL:** https://graph.digital/guides/ai-agents/memory
- **Contribution:** Doctrine/Project/State/Run separation. Immutable constitution. Append-only facts. Real-time operational truth.
- **Used in:** 4-layer memory architecture, shared directory design

### Microsoft Agent Framework 1.0
- **URL:** https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/
- **Contribution:** Production multi-agent SDK. Pluggable memory. Checkpointing/hydration. A2A + MCP support.
- **Used in:** Agent registry, memory architecture

### "Secure Multi-LLM Agentic AI and Agentification for Edge" (2025)
- **Source:** arXiv:2508.19870v1
- **URL:** https://arxiv.org/html/2508.19870v1
- **Contribution:** Multi-LLM topologies. Shared memory categories. MetaGPT message pool pattern.
- **Used in:** Fleet architecture, shared memory design

---

## CLI & UI

### Typer — Build Great CLIs
- **URL:** https://typer.tiangolo.com
- **Contribution:** Type-hinted CLI framework. Auto-generated help. Rapid development.
- **Used in:** All command modules

### Rich — Python Library for Rich Text
- **URL:** https://github.com/Textualize/rich
- **Contribution:** Tables, progress bars, markdown rendering, syntax highlighting, tracebacks.
- **Used in:** Fleet status, task queue, log display

### Textual — Python Framework for Terminal UIs
- **URL:** https://github.com/Textualize/textual
- **Contribution:** DOM-based widget system. Reactive updates. CSS-like TCSS. Async-native.
- **Used in:** Fleet monitor TUI dashboard

### OpenHands Software Agent SDK (2025)
- **Source:** arXiv:2511.03690v1
- **URL:** https://arxiv.org/html/2511.03690v1
- **Contribution:** Modular SDK design (sdk/tool/workspace/application). Opt-in sandboxing.
- **Used in:** Package structure, modular design

---

## Evaluation & Benchmarking

### "Benchmarking Agents on Hard, Real-World Tasks in Command Line Interfaces" (2024)
- **Source:** arXiv:2601.11868v1
- **URL:** https://arxiv.org/html/2601.11868v1
- **Contribution:** Terminal-Bench 2.0. CLI agents as dominant deployment path.
- **Used in:** CLI-first design justification

### "Terminal AI Agents: The 2025 Landscape"
- **URL:** https://wal.sh/research/2025-terminal-ai-agents/
- **Contribution:** Survey of terminal-based coding agents. MCP as enterprise default.
- **Used in:** CLI architecture justification

---

## Open Questions / Future Research

1. **Vector semantic search** for memory slicing (sentence-transformers integration)
2. **LLM-based intent classification** as primary path (currently rule-based)
3. **Online complexity threshold tuning** based on task success rates
4. **Cross-node agent migration** for load balancing
5. **Automatic skill generation** to doctrine/ based on successful agent runs
