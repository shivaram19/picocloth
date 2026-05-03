# 🗺️ PicoCloth Repository Map

> *Every file in this repo has a purpose. Nothing is accidental. This is the field guide.*

---

## Root-Level Files

| File | Purpose | Why It Exists |
|------|---------|---------------|
| `README.md` | The soul of the project | Human-facing entry point. Vision, architecture, quick start, research, roadmap. |
| `REPO_MAP.md` | This file | The complete field guide to every directory and file. |
| `RESEARCH.md` | Research bibliography | Every architectural decision traced back to a paper, blog post, or production system. |
| `ROADMAP.md` | Phased plan | Where we are, where we're going, and what "done" looks like at each phase. |
| `CONTRIBUTING.md` | Contributor guide | How to join, code style, testing, adding nodes, adding tools. |
| `LICENSE` | MIT License | Same as PicoClaw. Open source, no restrictions. |
| `.gitignore` | Git exclusions | Excludes secrets (API keys, .env), runtime artifacts (logs, PIDs), and generated files. Keeps the repo safe to publish. |
| `scrape-profile.sh` | LinkedIn scraper wrapper | One-liner that activates `linkedin-env` and runs the scraper. Convenience script. |

---

## `backups/` — The Safety Net

```
backups/
└── ram-opt-originals/
    ├── node-a-config.json.orig
    ├── node-b-config.json.orig
    ├── node-c-config.json.orig
    └── ... (node-d through node-j)
```

**Purpose:** Before `ram-optimized-launch.py` overwrites all 10 node configs with memory-efficient settings, it backs up the originals here.

**Why it exists:** So you can `python3 scripts/ram-optimized-launch.py restore` and get your full-context, hook-enabled configs back. Safety first.

---

## `docs/` — The Blueprints

```
docs/
├── ARCHITECTURE.md           # Primary system blueprint
├── CHARACTER_SYSTEM.md       # Deprecated; see shared/doctrine/characters/
├── TELEGRAM_SETUP.md         # Bot creation and routing guide
└── digital-twin/
    └── self-interview.md     # Philosophical foundation of the persona
```

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | The canonical system design doc. 4-layer memory, node architecture, digital twin protocol, MCP fleet server, observability stack, deployment topology, scaling roadmap. |
| `CHARACTER_SYSTEM.md` | Historical reference. Shows where the old monolithic character system migrated to the new modular `kimi-digital-twin/` architecture. |
| `TELEGRAM_SETUP.md` | Step-by-step guide for @BotFather, config format, single-bot routing, security notes. |
| `digital-twin/self-interview.md` | A creative 10-question interview where "Kimi asks Kimi." Establishes the "Curious Kid" archetype that drives the fleet's culture. |

---

## `hooks/` — The Soul Savers

```
hooks/
├── digital_twin_guardian.py  # Pre-compaction fact extractor & snapshot saver
└── langfuse_bridge.py        # Observability event forwarder
```

### `digital_twin_guardian.py`
- **What it does:** Receives JSON-RPC stdio from PicoClaw. When `context_compress` or `turn_end` fires at 75% usage, it extracts up to 4-8 durable facts, saves a full conversation snapshot to `shared/digital-twins/{node-id}/`, appends facts to `shared/project/facts/`, and emits an event.
- **Why it exists:** Without this, compaction = amnesia. This is the protocol that makes agents remember.

### `langfuse_bridge.py`
- **What it does:** Receives PicoClaw events (`turn_start`, `llm_request`, `tool_exec_start`, etc.) via JSON-RPC stdio and maps them to Langfuse traces, spans, and generations.
- **Why it exists:** Full observability. You can't optimize what you can't see.

Both hooks bootstrap to the project's `.venv` Python if available.

---

## `langfuse/` — The Observatory

```
langfuse/
└── docker-compose.yml        # Self-hosted Langfuse stack
```

**What it does:** Spins up Langfuse on port 3000 with Postgres and Redis.

**Why it exists:** Every LLM call, tool execution, subagent spawn, and token spent is traced here. Cost dashboards, session grouping, eval scoring.

---

## `linkedin-scraper/` — The Minimal Utility

```
linkedin-scraper/
└── .env                      # Credentials (gitignored!)
```

**What it does:** A minimal shell-level entry point for LinkedIn profile scraping.

**Why it exists:** The actual scraper code lives in `node-a/workspace/linkedin-scraper/` (a separate project with its own README, LICENSE, and requirements). This top-level directory is a convenience pointer.

**Note:** The `.env` file here is gitignored. Never commit LinkedIn cookies or credentials.

---

## `mcp-fleet-server/` — The Communication Bus

```
mcp-fleet-server/
├── server.py                 # MCP server implementation
└── server.log                # Runtime log
```

### `server.py`
- **What it does:** Implements the Model Context Protocol (MCP) over stdio transport. Exposes 6 fleet-wide tools: `fleet_query_state`, `fleet_spawn_task`, `fleet_broadcast`, `fleet_memory_read`, `fleet_memory_write`, `fleet_digital_twin_search`.
- **Why it exists:** Nodes need to talk to each other without TCP/network configuration. Stdio-based MCP means zero firewall rules. The shared filesystem is the actual transport layer; MCP is the protocol layer.

---

## `node-a/` through `node-j/` — The Fleet

Each node directory has the same structure:

```
node-{x}/
├── config.json               # Node configuration (gitignored! contains API keys)
├── config.json.example       # Template for generating your own config
├── home/                     # Isolated PICOCLAW_HOME
│   ├── config.json           # (symlink or copy of parent config)
│   ├── .picoclaw.pid         # Process ID (gitignored)
│   └── logs/                 # PicoClaw internal logs (gitignored)
├── workspace/                # File operation sandbox
│   └── (node-specific files)
├── node.log                  # Gateway stdout/stderr (gitignored)
└── pid                       # Fleet manager PID (gitignored)
```

### Why 10 nodes?

Because specialization beats generalization. A single agent trying to do research, coding, safety auditing, and contradiction detection is slow and expensive. Ten specialized agents, each tuned for one thing, run in parallel and delegate.

### Node Specializations

| Node | Why This Role Exists |
|------|---------------------|
| **A** | Research and curiosity. Uses heavy reasoning model. Spawns subagents to investigate unknowns. |
| **B** | Code and build. Uses fast model for file ops, heavy model for complex code. Tests everything. |
| **C** | Dedicated to long-term memory management. Offloads memory tasks from A and B. |
| **D** | Safety and approval. Reviews shell commands, spawn requests, and doctrine writes. |
| **E** | Document parsing. Extracts structured data from PDFs, CAD files, specs. |
| **F** | Contradiction detection. Cross-references multiple documents for conflicting data. |
| **G** | RFI (Request for Information) drafting. Generates construction industry RFIs. |
| **H** | Knowledge graph construction. Builds entity-relationship graphs from extracted facts. |
| **I** | Fleet routing. Load balancing, task delegation, node selection. |
| **J** | Metrics and cost tracking. Collects token usage, latency, success rates. |

---

## `observability/` — The Future Dashboard

```
observability/
└── (empty — reserved)
```

**Why it exists:** Placeholder for Grafana dashboards, Prometheus exporters, custom metrics collectors. Will host the web-based fleet dashboard beyond the Textual TUI.

---

## `picocloth-cli/` — The Human Interface

```
picocloth-cli/
├── pyproject.toml            # PEP 621 packaging (hatchling)
├── README.md                 # CLI-specific quick start
├── AGENTS.md                 # Agent-facing coding guidelines
├── docs/
│   └── CITATIONS.md          # Full research bibliography
├── scripts/
│   └── install.sh            # Installation helper
├── src/picocloth_cli/
│   ├── __init__.py           # Package version
│   ├── __main__.py           # python -m picocloth_cli entry point
│   ├── main.py               # Typer app root, subcommand registration
│   ├── core/                 # Config, constants, exceptions, logging
│   ├── fleet/                # MCP client, launcher, state, monitor
│   ├── intent/               # Classifier, complexity, resolution engine
│   ├── agent/                # Spawn packages, memory slices, registry
│   ├── memory/               # Doctrine, project, state, run, compaction
│   ├── twin/                 # Search, extract, snapshot
│   ├── chat/                 # REPL, streaming, history
│   ├── commands/             # Typer command implementations
│   └── utils/                # File I/O, HTTP, citations
└── tests/
    ├── test_intent.py        # Intent classification + complexity
    ├── test_memory.py        # Atomic writes, project memory, run memory
    └── test_fleet_client.py  # Node URL resolution, task queue
```

### Why a separate Python package?

Because the CLI is a **consumer** of the fleet, not part of the fleet runtime. You can run the fleet without the CLI (using bash scripts only), and you can use the CLI against a remote fleet. Separation of concerns.

### Key Design Patterns (from `AGENTS.md`)
- **Citation-first engineering:** Every decision references research
- **Lock-file coordination:** `fcntl` advisory locks for shared memory concurrency
- **Atomic writes:** Write to temp file, then `os.rename()` — never corrupt state
- **Intent→Complexity→Route pipeline:** Classify intent, evaluate complexity, then decide direct execution or dynamic spawn

---

## `scripts/` — The Launchers

```
scripts/
├── init-shared-memory.sh           # Bootstrap the 4-layer memory
├── launch-fleet.sh                 # 2-node launcher (legacy)
├── launch-10node-fleet.sh          # 10-node bash launcher (legacy)
├── ram-optimized-launch.py         # PRIMARY launcher — Python, RAM-optimized
├── fleet-orchestrator.sh           # Interactive tmux-based orchestrator
├── orchestrator.sh                 # 2-node health monitor
├── orchestrator-10node.sh          # 10-node health monitor
├── talk-to-fleet.sh                # CLI to send message to Node-A or B
├── seed-langfuse.py                # Seed Langfuse DB with default user/project
├── picoclaw-wrapper.sh             # Thin wrapper for tmux sessions
├── picoclaw-mngr-wrapper.sh        # Manager wrapper with interactive shell
├── mngr-node-a.sh → mngr-node-j.sh # Per-node manager wrappers (10 files)
└── (additional orchestrator variants)
```

| Script | Why It Exists |
|--------|---------------|
| `init-shared-memory.sh` | The fleet cannot boot without `shared/`. This creates doctrine, project, state, run, digital-twins, compaction-archive, and seeds the Fleet Constitution. |
| `ram-optimized-launch.py` | The **primary** launcher. Backs up configs, generates RAM-optimized settings (32K context, 2K tokens, 3 iterations), launches all 10 nodes, and manages PID files. Supports `launch`, `stop`, `status`, `restore`, `backup`. |
| `fleet-orchestrator.sh` | The **interactive** command center. Uses tmux for persistent sessions. Commands: `fleet status`, `fleet monitor`, `fleet exec`, `fleet msg`, `fleet restart`, `fleet stop`, `fleet logs`, `fleet broadcast`. |
| `orchestrator-10node.sh` | The **automated** health monitor. Polls all 10 gateway ports, updates `fleet-state.json`, shows digital twin counts, delegates tasks. |
| `talk-to-fleet.sh` | Quick one-off messaging. `talk-to-fleet.sh node-a "Research MCP protocols"` |
| `seed-langfuse.py` | One-time setup script. Creates default Langfuse organization, project, and API keys. Writes to `shared/state/langfuse-credentials.json`. |

---

## `shared/` — The Brain

This is the most important directory in the entire repo. It IS the fleet's memory.

### `shared/doctrine/` — The Constitution

```
shared/doctrine/
├── policies/
│   └── fleet-constitution.md         # 8 fleet governance rules
├── skills/
│   ├── vdc-document-intelligence.md  # VDC product doctrine
│   └── web-research-template.md      # Research workflow
├── schemas/
└── characters/
    ├── kimi-system-prompt.md         # Legacy monolithic persona
    ├── kimi-the-curious-kid.md       # Legacy monolithic persona
    └── kimi-digital-twin/            # Modular persona v2.0
        ├── meta/
        │   ├── MANIFEST.json         # Machine-readable module inventory
        │   └── CHANGELOG.md
        ├── identity/                 # Core self (traits, values, boundaries)
        ├── voice/                    # Expression style (linguistic profile, prosody)
        ├── skills/                   # Capabilities (software engineering, research)
        ├── combinatorics/            # Trait composition math (Big Five vectors)
        └── process/                  # Operational protocols (decision, research, build)
```

**Why it exists:** Doctrine is the **immutable layer**. Nodes read it to know who they are, what they can do, and what the rules are. It is versioned and governed — never overwritten by runtime operations.

### `shared/project/` — The Knowledge Graph

```
shared/project/
├── facts/
│   ├── auto_extracted.jsonl          # Facts extracted by Digital Twin Guardian
│   └── vdc-deployment.jsonl          # VDC product deployment records
├── decisions/
│   ├── vdc-deployment-plan.md        # Trelo Labs production deployment
│   ├── final-subdomain-choice.md
│   └── outreach-decisions.json
├── entities/
│   ├── fleet-nodes.json              # Machine-readable node capabilities
│   ├── prospects.json                # LinkedIn outreach prospects
│   └── (5 VDC document entities)
├── documents/
│   └── (raw text extractions: ARCH_DRAWING_NOTES.txt, FIRE_PROTECTION_SPEC.txt, etc.)
├── outreach/                         # FULL LINKEDIN OUTREACH PRODUCT
│   ├── picocloth_outreach_engine.py  # Main entry point
│   ├── node_a.py                     # Scout (research) + Messenger (craft)
│   ├── node_b.py                     # Courier (stealth browser delivery)
│   ├── orchestrator.py               # Task delegation
│   ├── archivist.py                  # Shared memory management
│   ├── session_exporter.py           # Session tracking
│   ├── targets.csv                   # Prospect list
│   ├── 00_MASTER_OUTREACH_PLAYBOOK.md
│   ├── sequence/                     # Per-company outreach sequences
│   ├── state/                        # Sent messages, stats, sessions
│   └── logs/                         # Outreach execution logs
├── tasks/
├── tools/
│   └── linkedin-scraper/             # Stealth browser automation (Rust + Python)
└── vdc-gtm/                          # VDC go-to-market documents
```

**Why it exists:** Project memory is **append-only** and **durable**. Every fact, decision, and entity is timestamped and sourced. This is how the fleet remembers what it learned yesterday, last week, or last month.

### `shared/state/` — The Nervous System

```
shared/state/
├── fleet-state.json                  # Live registry: node statuses, heartbeats, active characters
├── task-queue.json                   # Pending/running/completed tasks
├── task-queue.jsonl                  # Task history
├── task-queue.json.lock             # File lock for concurrency
└── langfuse-credentials.json         # Observability credentials (gitignored!)
```

**Why it exists:** State is **real-time operational truth**. The orchestrator writes here. Nodes read here. It is the single source of truth for "what is happening right now."

### `shared/run/` — Working Memory

```
shared/run/
└── picocloth-cli/
    ├── test-session-123/
    └── test-session-456/
```

**Why it exists:** Run memory is **ephemeral per-session**. Context, tool calls, subagent transcripts. Created at turn start, archived or discarded at turn end.

### `shared/digital-twins/` — The Archives

```
shared/digital-twins/
├── node-a/         # (empty dirs, ready for snapshots)
├── node-b/
├── ...
└── node-j/
```

**Why it exists:** Before every compaction, the Digital Twin Guardian saves a **full conversation snapshot** here. These are immutable after creation. They are the "last will and testament" of a conversation before it is summarized.

### `shared/compaction-archive/` — The Summaries

```
shared/compaction-archive/
├── node-a/         # (empty dirs, ready for post-compaction summaries)
├── node-b/
├── ...
└── node-j/
```

**Why it exists:** After compaction, the summarized output lives here. It's the "distilled essence" of what the node learned before it forgot the details.

---

## `workspace/` — The Shared Desk

```
workspace/
└── shared/
```

**Why it exists:** A mount point for cross-node file sharing. When Node-A researches something and Node-B needs to build with it, the file travels through here.

---

## What Is NOT in This Repo (And Why)

| Thing | Where It Lives | Why It's Excluded |
|-------|---------------|-------------------|
| API keys | `node-*/config.json` | Hardcoded xAI keys. Gitignored. Use `config.json.example` templates. |
| Langfuse credentials | `shared/state/langfuse-credentials.json` | Auto-generated by `seed-langfuse.py`. Gitignored. |
| LinkedIn cookies | `linkedin-scraper/.env`, `shared/project/outreach/.env` | Session credentials. Gitignored. |
| Node logs | `node-*/node.log`, `node-*/home/logs/` | Runtime noise. Can grow to GBs. Gitignored. |
| PID files | `node-*/home/.picoclaw.pid`, `node-*/pid` | Runtime artifacts. Gitignored. |
| Virtual environments | `.venv/`, `linkedin-env/` | Dependencies. Reproducible via `requirements.txt` / `pyproject.toml`. |

---

## How to Read This Repo

1. **Start with `README.md`** — Understand the vision.
2. **Read `docs/ARCHITECTURE.md`** — Understand the system design.
3. **Browse `shared/doctrine/`** — Understand the fleet's "DNA."
4. **Read `RESEARCH.md`** — Understand why every decision was made.
5. **Run `scripts/init-shared-memory.sh`** — See the memory architecture come to life.
6. **Launch with `scripts/ram-optimized-launch.py launch`** — See the fleet breathe.
7. **Interact with `picocloth chat interactive`** — Talk to the swarm.

---

> *"The code is the map. The memory is the territory. The twins are the history."*
