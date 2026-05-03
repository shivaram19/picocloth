# 🪶 PicoCloth-CLI

A research-backed CLI for orchestrating the **PicoCloth fleet** of intent-driven agents.

> *"10 curious kids working together, never forgetting what they learned."*

---

## What is PicoCloth-CLI?

**PicoCloth-CLI** is the command-line interface for interacting with the [PicoCloth](https://github.com/picocloth/picocloth) distributed fleet architecture. It is a **consumer of the fleet** — you can use it against a local fleet, a remote fleet, or both.

- 🎛️ **Fleet Management** — launch, monitor, and control 10 specialized nodes
- 💬 **Interactive Chat** — natural language REPL with streaming output
- 🧠 **Intent Engine** — hybrid rule-based + LLM intent classification
- 🤖 **Agent Spawning** — dynamic runtime agent creation with memory slicing
- 🧬 **Digital Twins** — search and extract from pre-compaction snapshots
- 🧠 **Shared Memory** — CRUD access to the 4-layer memory architecture
- 📊 **Live TUI Dashboard** — real-time fleet monitoring with Textual

Every architectural decision is justified by peer-reviewed research or production patterns from 2024-2026.

---

## Installation

### From PyPI (Recommended)

```bash
pip install picocloth-cli
```

This installs the `picocloth` command globally.

### From Source

```bash
cd picocloth/picocloth-cli
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Show fleet status
picocloth fleet status

# Launch the fleet
picocloth fleet launch

# Interactive chat
picocloth chat interactive

# Spawn a task
picocloth task spawn node-b "Build a REST API"

# Search digital twins
picocloth twin search "postgres"

# Monitor live dashboard
picocloth fleet monitor
```

---

## Commands

### Fleet
```bash
picocloth fleet status          # Rich table of all nodes
picocloth fleet launch          # Launch 10-node RAM-optimized fleet
picocloth fleet stop            # Stop all nodes
picocloth fleet logs <node>     # Show node logs
picocloth fleet tasks           # Show task queue
picocloth fleet broadcast       # Message all nodes
picocloth fleet monitor         # Live Textual TUI dashboard
```

### Chat
```bash
picocloth chat interactive      # REPL with Rich markdown
picocloth chat --node node-b    # Chat with specific node
```

### Task
```bash
picocloth task spawn <node> <task>   # Delegate task
picocloth task status               # Show queue
picocloth task complete <id>        # Mark done
picocloth task cancel <id>          # Cancel pending
```

### Agent
```bash
picocloth agent spawn <node> <goal>  # Spawn agent
picocloth agent list                 # List agents
picocloth agent show <id>            # Agent details
picocloth agent kill <id>            # Terminate agent
picocloth agent tree                 # Agent hierarchy
```

### Memory
```bash
picocloth memory read <layer> <category> <key>    # Read value
picocloth memory write <layer> <category> <key>   # Write value
picocloth memory list-layers                      # Show architecture
```

### Twin
```bash
picocloth twin search <query>       # Search archives
picocloth twin show <path>          # Display snapshot
picocloth twin stats                # Archive statistics
```

### Config
```bash
picocloth config get                # Show all config
picocloth config get fleet.transport # Get specific key
picocloth config set <key> <value>  # Set config
picocloth config reload             # Reload from disk
```

---

## Architecture

```
picocloth-cli/
├── src/picocloth_cli/
│   ├── core/           # Config, constants, exceptions, logging
│   ├── fleet/          # MCP client, state, launcher, monitor
│   ├── intent/         # Classifier, complexity, resolution engine
│   ├── agent/          # Spawn packages, memory slices, registry
│   ├── memory/         # Doctrine, project, state, run, compaction
│   ├── twin/           # Search, extract, snapshot
│   ├── chat/           # REPL, streaming, history
│   ├── commands/       # Typer command implementations
│   └── utils/          # File I/O, HTTP, citations
├── tests/              # pytest suite
├── docs/               # Architecture, citations, intent engine
└── scripts/            # install.sh
```

### Relationship to the Fleet

```
┌─────────────────┐         ┌─────────────────┐
│   You (human)   │────────►│  PicoCloth CLI  │
└─────────────────┘         └────────┬────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
    ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
    │  Node-A     │◄────────►│  Node-B     │◄────────►│  Node-C..J  │
    │  (MCP)      │  shared/ │  (MCP)      │  shared/ │  (shared    │
    └─────────────┘  memory  └─────────────┘  memory  │   memory)   │
                                                      └─────────────┘
```

The CLI connects to nodes via HTTP gateway ports and reads/writes the same `shared/` filesystem that the fleet uses. It is a first-class citizen of the architecture, not an afterthought.

---

## Design Patterns

- **Citation-first engineering:** Every decision references research
- **Lock-file coordination:** `fcntl` advisory locks for shared memory concurrency
- **Atomic writes:** Write to temp file, then `os.rename()` — never corrupt state
- **Intent→Complexity→Route pipeline:** Classify intent, evaluate complexity, then decide direct execution or dynamic spawn

---

## Research Citations

Every design decision is backed by research:

| Decision | Citation |
|----------|----------|
| Typer CLI framework | [Typer docs](https://typer.tiangolo.com); OpenHands V1 SDK (arXiv:2511.03690v1) |
| Rich + Textual UI | [Rich](https://github.com/Textualize/rich); [Textual](https://github.com/Textualize/textual) |
| MCP fleet communication | [MCP Protocol](https://modelcontextprotocol.io); agent-fleet repo |
| Intent-driven spawning | [AgentSpawn](https://arxiv.org/html/2602.07072v1) — 34% completion improvement |
| File-based memory | Claude Code architecture (arXiv:2604.14228v1) |
| Graduated compaction | Context Engineering Toolkit (arXiv:2604.08290v1) |
| Lock-file coordination | Claude Code Agent Teams (Anthropic, Feb 2026) |

See [docs/CITATIONS.md](docs/CITATIONS.md) for the full bibliography.

---

## Development

```bash
# Install in dev mode
cd picocloth-cli
pip install -e ".[dev]"

# Run tests
pytest -v

# Lint
ruff check src/ tests/
mypy src/

# Format
ruff format src/ tests/
```

---

## Publishing

This package is published to PyPI automatically via GitHub Actions when you push a tag:

```bash
# Bump version in src/picocloth_cli/__init__.py and pyproject.toml
git add .
git commit -m "release: bump CLI to v0.2.0"
git tag cli-v0.2.0
git push origin cli-v0.2.0
```

The `.github/workflows/publish-cli.yml` workflow will build, test, lint, and publish.

**Required:** Add `PYPI_API_TOKEN` as a GitHub repository secret.

---

## License

MIT — Same as PicoCloth. See [LICENSE](../LICENSE).
