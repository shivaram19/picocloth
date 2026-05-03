# 🪶 PicoCloth

## A Fleet of PicoClaws with Digital Twins & Shared Memory

> *"10 curious kids working together, never forgetting what they learned."*

---

## 🎯 What is PicoCloth?

**PicoCloth** is a distributed multi-agent fleet architecture built on top of [PicoClaw](https://github.com/sipeed/picoclaw) — the ultra-lightweight AI assistant that runs on ~$10 hardware with <10MB RAM.

But we asked: *What if instead of one agent, you had ten?* And what if they never forgot anything?

PicoCloth runs **10 specialized AI nodes** that:
- 🧠 Share a **4-layer memory architecture** via the filesystem
- 🤖 Create **Digital Twins** (full conversation snapshots) before every memory compaction
- 📡 Communicate via an **MCP Fleet Server** (Model Context Protocol)
- 📊 Report to **Langfuse** for full observability
- 🎛️ Are orchestrated by both bash scripts and a **Python CLI**
- 🔗 Can be reached via **Telegram bots**

This is not just a wrapper. This is an **operating system for agent swarms**.

---

## 🗺️ Repository Map — What Lives Where

Every directory in this repo has a purpose. Nothing is accidental.

| Directory | Purpose | Why It Exists |
|-----------|---------|---------------|
| [`backups/`](backups/) | Original node configs before RAM optimization | Safety net. `ram-optimized-launch.py` overwrites configs; originals live here so you can `restore`. |
| [`docs/`](docs/) | Project documentation and architecture specs | The blueprints. ARCHITECTURE.md is the system design. CHARACTER_SYSTEM.md is the digital twin persona. TELEGRAM_SETUP.md is the bot guide. |
| [`hooks/`](hooks/) | Python subprocess hooks for PicoClaw | `digital_twin_guardian.py` extracts facts before compaction. `langfuse_bridge.py` forwards events to observability. These are the "soul savers." |
| [`langfuse/`](langfuse/) | Self-hosted observability stack | `docker-compose.yml` for Langfuse — traces every LLM call, tool execution, and cost. |
| [`linkedin-scraper/`](linkedin-scraper/) | Minimal LinkedIn scraping utility | Barebones shell wrapper + env for profile scraping. Uses a separate venv. |
| [`mcp-fleet-server/`](mcp-fleet-server/) | Model Context Protocol server | `server.py` is the inter-node communication bus. Exposes 6 fleet-wide tools. Runs over stdio (zero network dependencies). |
| [`node-a/` → `node-j/`](node-a/) | 10 individual PicoClaw node working directories | Each has `config.json` (role, model, port), `home/` (isolated PICOCLAW_HOME), `workspace/` (file ops), `node.log`, and `pid`. |
| [`observability/`](observability/) | Placeholder for additional observability configs | Reserved for Grafana dashboards, custom metrics exporters, etc. |
| [`picocloth-cli/`](picocloth-cli/) | Research-backed Python CLI package | The human interface. Typer + Rich + Textual. Fleet management, chat, task spawning, memory CRUD, twin search. Installable via `pip install -e ".[dev]"`. |
| [`scripts/`](scripts/) | Bash and Python launchers | `init-shared-memory.sh`, `launch-fleet.sh`, `ram-optimized-launch.py`, `fleet-orchestrator.sh`, `talk-to-fleet.sh`, and 10 per-node manager wrappers. |
| [`shared/`](shared/) | The **4-layer shared memory filesystem** — the fleet's brain | See below. This is the entire reason PicoCloth works. |
| [`workspace/`](workspace/) | Cross-node shared workspace mount point | Symlink-style workspace for files that need to travel between nodes. |

---

## 🧠 The 4-Layer Shared Memory Architecture

Inspired by [Graph Digital's production Katelyn Skills OS](https://graph.digital/guides/ai-agents/memory) and refined through our own research:

```
shared/
├── doctrine/          # Layer 1: The Constitution (immutable)
│   ├── skills/        # Markdown skills with YAML frontmatter
│   ├── schemas/       # Data schemas
│   ├── policies/      # Fleet constitution, behavioral rules
│   └── characters/    # Modular digital twin persona system
├── project/           # Layer 2: The Knowledge Graph (append-only)
│   ├── facts/         # Extracted durable facts (JSONL)
│   ├── decisions/     # Fleet decisions with timestamps
│   ├── entities/      # Entity relationship registries
│   ├── documents/     # Raw document extractions
│   ├── outreach/      # LinkedIn outreach engine (full product!)
│   └── tools/         # Tool definitions
├── state/             # Layer 3: The Nervous System (real-time)
│   ├── fleet-state.json      # Live node health
│   ├── task-queue.json       # Pending/running tasks
│   └── langfuse-credentials.json
├── run/               # Layer 4: Working Memory (ephemeral)
│   └── picocloth-cli/ # Per-session runtime context
├── digital-twins/     # Pre-compaction snapshots (immutable)
│   └── node-a/ → node-j/
└── compaction-archive/ # Post-compaction summaries
    └── node-a/ → node-j/
```

### Why 4 Layers?

| Layer | Lifetime | Analogy | Writes |
|-------|----------|---------|--------|
| **Doctrine** | Immutable / versioned | DNA | Governed updates only |
| **Project** | Append-only, timestamped | Long-term memory | Pre-compaction hooks + explicit writes |
| **State** | Real-time | Nervous system | Orchestrator + task queue |
| **Run** | Per-execution | Working memory | Created at turn start, archived at turn end |

This separation prevents **catastrophic forgetting** — the #1 failure mode of long-running agents.

---

## 🤖 The 10 Nodes — Who Does What

Each node is a specialized intelligence with its own model routing, system prompt, and tool set.

| Node | Role | Port | Model | Hooks | MCP |
|------|------|------|-------|-------|-----|
| **Node-A** | Curiosity Brain (Research) | 18790 | grok-4.20-reasoning | ✅ Digital Twin | ✅ |
| **Node-B** | Executor Builder (Code/Deploy) | 18791 | grok-4.1-fast | ✅ Digital Twin | ✅ |
| **Node-C** | Memory Guardian | 18792 | grok-4.1-fast | ❌ | ❌ |
| **Node-D** | Safety Auditor | 18793 | grok-4.1-fast | ❌ | ❌ |
| **Node-E** | Document Parser | 18794 | grok-4.1-fast | ❌ | ❌ |
| **Node-F** | Contradiction Detector | 18795 | grok-4.1-fast | ❌ | ❌ |
| **Node-G** | RFI Drafter | 18796 | grok-4.1-fast | ❌ | ❌ |
| **Node-H** | Knowledge Graph Builder | 18797 | grok-4.1-fast | ❌ | ❌ |
| **Node-I** | Fleet Router | 18798 | grok-4.1-fast | ❌ | ❌ |
| **Node-J** | Metrics Collector | 18799 | grok-4.1-fast | ❌ | ❌ |

**RAM Optimization Strategy:** Only Node-A and Node-B run full hooks and MCP connections. The other 8 nodes run with reduced context windows (32K), low max tokens (2K), and minimal tool iterations (3) to save memory. This lets you run 10 nodes on a single machine.

---

## 🔄 Digital Twin Protocol — Never Forget

The heart of PicoCloth. When a node's context usage reaches **75%**, this happens **BEFORE** compaction:

```
Context Usage: 75% reached
    |
    v
[Digital Twin Guardian Hook Fires]
    |
    +---> Extract up to 8 durable facts (preferences, decisions, constraints)
    +---> Save FULL conversation snapshot to shared/digital-twins/{node-id}/
    +---> Append facts to shared/project/facts/auto_extracted.jsonl
    +---> Emit event to fleet EventBus
    |
    v
[Compaction Proceeds]
    |
    +---> Summarize and truncate
    +---> Save compaction summary to compaction-archive/
```

**Result:** No knowledge is ever lost. It is archived, indexed, and searchable.

The Digital Twin format is a structured JSON snapshot containing:
- `twin_id`, `node_id`, `timestamp`, `session_key`
- Full `conversation_snapshot`
- `extracted_facts` with confidence scores
- `active_subagents` and their status

---

## 📡 MCP Fleet Server — How Nodes Talk

Nodes don't talk over TCP. They talk through the **MCP Fleet Server** via stdio transport (JSON-RPC).

This means zero network configuration. Zero firewall rules. Just shared filesystem + stdin/stdout.

### Fleet-Wide Tools (6 total)

| Tool | What It Does |
|------|--------------|
| `fleet_query_state` | Read `shared/state/fleet-state.json` — who's alive? |
| `fleet_spawn_task` | Delegate a task to a specific node (writes to task queue) |
| `fleet_broadcast` | Send a message to all nodes (appends to `fleet-inbox.jsonl`) |
| `fleet_memory_read` | Read from `shared/project/{category}/` |
| `fleet_memory_write` | Write to `shared/project/{category}/` |
| `fleet_digital_twin_search` | Search historical twins across all nodes |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Go 1.25+ (for building PicoClaw)
# Node.js 22+ & pnpm (for Web UI, optional)
# Docker & Docker Compose (for Langfuse, optional)
# Python 3.10+ (for MCP Fleet Server and CLI)
```

### 1. Set Your API Key

```bash
export OPENAI_API_KEY="sk-your-key-here"
# Or add to ~/.bashrc for persistence
```

> ⚠️ **SECURITY NOTE:** Node configs contain API keys. The real `config.json` files are `.gitignore`d. Use the `config.json.example` templates to generate your own.

### 2. Initialize Shared Memory

```bash
./scripts/init-shared-memory.sh
```

This creates the entire `shared/` hierarchy: doctrine, project, state, run, digital-twins, compaction-archive. It also writes the Fleet Constitution and initial registries.

### 3. Launch the Fleet

```bash
# 2-node base fleet (Node-A + Node-B + MCP Server + Langfuse)
./scripts/launch-fleet.sh start

# OR: 10-node RAM-optimized fleet
python3 scripts/ram-optimized-launch.py launch
```

### 4. Monitor

```bash
# Fleet health dashboard
./scripts/orchestrator.sh status

# Live monitoring
./scripts/orchestrator.sh monitor

# Python CLI
picocloth fleet status
picocloth fleet monitor        # Live TUI dashboard!
```

### 5. Interact

```bash
# Chat with the fleet
picocloth chat interactive

# Spawn a task
picocloth task spawn node-b "Build a REST API"

# Search digital twins
picocloth twin search "postgres"
```

### 6. Stop

```bash
./scripts/launch-fleet.sh stop
# OR
python3 scripts/ram-optimized-launch.py stop
```

---

## 🖥️ PicoCloth CLI

The **PicoCloth CLI** is the human interface to the fleet. It lives in this monorepo (under `picocloth-cli/`) but is structured as an **independently deployable Python package**.

```bash
# Install from PyPI
pip install picocloth-cli

# Or from source
cd picocloth-cli
pip install -e ".[dev]"
```

### Why Keep It in This Repo?

For now, the CLI and fleet are tightly coupled. They share:
- The MCP protocol (tools, schemas)
- The shared memory schema (`shared/state/fleet-state.json`)
- The digital twin format

Splitting into a separate repo makes sense **when the fleet API stabilizes** (Phase 2 or 3). Until then, monorepo = faster iteration, atomic commits, no version sync hell.

### When to Split

- MCP protocol is stable (no new tools for 30 days)
- Shared memory schema is versioned and backward-compatible
- You want independent release cadence (CLI v1.2.0 while fleet is v0.8.0)
- External contributors want to build alternate CLIs/GUIs

**See [`picocloth-cli/README.md`](picocloth-cli/README.md) for full CLI documentation.**

---

## 📱 Telegram Integration

Each node can be its own Telegram bot. See [`docs/TELEGRAM_SETUP.md`](docs/TELEGRAM_SETUP.md) for:
- Creating bots with @BotFather
- Adding tokens to node configs
- Advanced single-bot routing patterns
- Bot commands (`/start`, `/status`, `/spawn`, `/tasks`, `/memory`)

---

## 📊 Observability with Langfuse

Self-hosted Langfuse stack provides:

- **Trace Timeline**: Full agent execution paths
- **Cost Dashboard**: Per-node token usage and spend
- **Session Grouping**: All turns from same conversation
- **Eval Scoring**: LLM-as-a-judge quality metrics

```bash
cd langfuse
docker-compose up -d
# Visit http://localhost:3000
```

All LLM calls, tool executions, and subagent spawns are traced via the `langfuse_bridge.py` hook.

---

## 🔬 Research Foundations

Every architectural decision in PicoCloth is backed by research:

| Decision | Source | Contribution |
|----------|--------|-------------|
| Base agent runtime | [PicoClaw](https://github.com/sipeed/picoclaw) | <10MB RAM agent runtime on $10 hardware |
| 4-layer memory | [Graph Digital](https://graph.digital/guides/ai-agents/memory) | Production Katelyn Skills OS architecture |
| Smart compaction | [Trey Goff's Memory System](https://github.com/treygoff24/openclaw-memory-system) | PSM injection, graduated compaction |
| Memory dynamics | [Steve Kinney](https://stevekinney.com/writing/agent-memory-systems) | Lifecycle and dynamics theory |
| LLM observability | [Langfuse](https://github.com/langfuse/langfuse) | Open-source tracing and cost tracking |
| Agent-tool protocol | [MCP Protocol](https://modelcontextprotocol.io) | Standardized Model Context Protocol |
| Fleet deployment | [Eric Grill's Fleet Manager](https://github.com/EricGrill/picoclaw-fleet) | SSH-based multi-node patterns |
| Pre-compaction hooks | [OpenClaw #7175](https://github.com/openclaw/openclaw/issues/7175) | Hook concept for knowledge preservation |
| Enterprise patterns | [AetherLink](https://aetherlink.ai) | Multi-agent orchestration at scale |
| Intent-driven spawning | [AgentSpawn](https://arxiv.org/html/2602.07072v1) | 34% task completion improvement |
| File-based memory | [Claude Code](https://arxiv.org/abs/2604.14228v1) | Agent teams with filesystem memory |
| Lock-file coordination | [Anthropic](https://www.anthropic.com) (Feb 2026) | Concurrent agent filesystem safety |

See [`RESEARCH.md`](RESEARCH.md) for the full bibliography with deep dives.

---

## 🗺️ Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the full phased plan.

| Phase | Nodes | Focus |
|-------|-------|-------|
| **Phase 1: Foundation** ✅ | 2 | Shared memory, digital twins, MCP, orchestrator, Langfuse |
| **Phase 2: Scale** 🔄 | 5 | Memory nodes, load balancer, Telegram, GAN experiments |
| **Phase 3: Intelligence** | 10 | Self-improving curiosity, auto-skill generation, cross-node delegation |
| **Phase 4: Autonomy** | 25+ | Distributed across machines, self-healing, emergent behavior |

---

## 🤝 Contributing

We built this in the open because we believe **agent swarms should be a public good**.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for:
- Code style (ruff, mypy, line-length 100)
- How to add a new node role
- How to add MCP tools
- How to contribute to the Digital Twin persona
- Testing requirements

Key contribution areas:
- Better digital twin extraction (LLM-based vs rule-based)
- Vector database integration for semantic memory search
- Real-time fleet dashboard (web UI beyond Textual)
- Additional MCP tools (Slack, Discord, email bridges)
- Cost optimization algorithms
- Custom classifier training pipeline

---

## 📄 License

MIT — Same as PicoClaw. See [`LICENSE`](LICENSE).

---

## 🙏 Acknowledgments

- **Sipeed** for creating PicoClaw — the tiny runtime that makes this possible
- **Eric Grill** for the picoclaw-fleet inspiration
- **Trey Goff** for the memory system research
- **Graph Digital** for the 4-layer memory blueprint
- **The entire PicoClaw community** for 26K stars of momentum
- **Every contributor** who adds a node, a tool, or a thought

---

> *"Be the kid. Be curious. Build the future."* 🚀🪶
