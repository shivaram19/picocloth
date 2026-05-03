# 🤝 Contributing to PicoCloth

> *"We built this in the open because agent swarms should be a public good."*

Thank you for considering a contribution. Every PR, issue, and idea makes the fleet stronger.

---

## Code of Conduct

- Be the kid. Be curious. Be kind.
- Assume good intent.
- Cite your sources. See `RESEARCH.md` for the citation format.
- No knowledge gatekeeping. If you learned something, write it down in `shared/doctrine/skills/`.

---

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/picocloth.git
cd picocloth
```

### 2. Set Up Python Environment

```bash
# For the CLI and hooks
python3 -m venv .venv
source .venv/bin/activate
pip install -e "picocloth-cli/[dev]"

# For the linkedin scraper (optional)
python3 -m venv linkedin-env
source linkedin-env/bin/activate
pip install -r linkedin-scraper/requirements.txt
```

### 3. Initialize Shared Memory

```bash
./scripts/init-shared-memory.sh
```

### 4. Configure a Node

```bash
# Copy the example config
cp node-a/config.json.example node-a/config.json

# Edit with your API key
nano node-a/config.json
```

> ⚠️ **NEVER commit `node-*/config.json`.** These files contain API keys and are `.gitignore`d by default.

### 5. Run Tests

```bash
cd picocloth-cli
pytest -v
```

---

## Development Guidelines

### Code Style

We use `ruff` and `mypy`:

```bash
cd picocloth-cli
ruff check src/ tests/
ruff format src/ tests/
mypy src/
```

- **Line length:** 100
- **Python target:** 3.10+
- **Type hints:** Required. `disallow_untyped_defs = true` in mypy.
- **Docstrings:** Google style for public functions.

### Project Structure

When adding code, respect the separation:

| Layer | What Goes Here | Examples |
|-------|---------------|----------|
| `core/` | Infrastructure | Config models, constants, exceptions, logging setup |
| `fleet/` | Communication | MCP client, HTTP wrappers, state CRUD, TUI monitor |
| `intent/` | Routing logic | Intent classifier, complexity evaluator, resolution engine |
| `agent/` | Lifecycle | Spawn packages, memory slices, registry |
| `memory/` | Storage | Doctrine, project, state, run, compaction |
| `twin/` | Archives | Search, extract, snapshot |
| `chat/` | Interaction | REPL, streaming, history |
| `commands/` | CLI surface | Typer command implementations |
| `utils/` | Helpers | File I/O (atomic writes, locks), HTTP, citations |

### Testing

- Write tests for every new module.
- Use `pytest` with `pytest-asyncio` for async code.
- Use `pytest-cov` for coverage.
- Mock filesystem operations where possible.

```bash
pytest tests/test_intent.py -v
pytest tests/test_memory.py -v
pytest tests/test_fleet_client.py -v
```

### Atomic Writes

When writing to `shared/`, always use atomic writes:

```python
from picocloth_cli.utils.files import atomic_write_json

atomic_write_json("shared/state/fleet-state.json", new_state)
```

This writes to a temp file and renames — never corrupts state.

### Lock-File Coordination

When multiple nodes might read/write the same file:

```python
from picocloth_cli.utils.files import lock_file

with lock_file("shared/state/task-queue.json"):
    # read + write
```

This uses `fcntl.flock` for advisory locking.

---

## How to Add a New Node Role

1. **Choose a node letter** (e.g., node-k)
2. **Create the directory:**
   ```bash
   mkdir -p node-k/{home,workspace}
   ```
3. **Create `config.json` from template:**
   ```bash
   cp node-standard/config.json.example node-k/config.json
   ```
4. **Edit the config:**
   - Set unique `gateway.port` (e.g., 18800)
   - Write a `system_prompt` for the new role
   - Choose appropriate `model_name`
   - Enable/disable hooks and MCP as needed
5. **Register in fleet state:**
   ```bash
   picocloth memory write state fleet-nodes node-k '{"role":"your_role","port":18800}'
   ```
6. **Add documentation:**
   - Update `REPO_MAP.md`
   - Update `docs/ARCHITECTURE.md`
   - Add a skill to `shared/doctrine/skills/` if needed
7. **Submit PR**

---

## How to Add an MCP Tool

1. **Edit `mcp-fleet-server/server.py`**
2. **Add to `TOOLS` list:**
   ```python
   {
       "name": "fleet_your_tool",
       "description": "What it does",
       "inputSchema": {
           "type": "object",
           "properties": {
               "param": {"type": "string", "description": "What this param does"}
           },
           "required": ["param"]
       }
   }
   ```
3. **Add handler in `handle_tool_call()`:**
   ```python
   elif name == "fleet_your_tool":
       return {"content": [{"type": "text", "text": result}]}
   ```
4. **Update CLI client** (`picocloth_cli/fleet/client.py`)
5. **Add test**
6. **Submit PR**

---

## How to Contribute to the Digital Twin Persona

The persona lives in `shared/doctrine/characters/kimi-digital-twin/`.

### Modules

| Module | What It Contains | How to Contribute |
|--------|-----------------|-------------------|
| `identity/` | Core self, values, boundaries | Add new facets, refine trait vectors |
| `voice/` | Linguistic profile, prosody, catchphrases | Add new registers, refine emotional markers |
| `skills/` | Capabilities | Add new skill modules (markdown + YAML frontmatter) |
| `combinatorics/` | Trait composition math | Refine archetype recipes, add interaction matrices |
| `process/` | Operational protocols | Add new workflows (decision, research, build, communication) |

### Format

Every module is a Markdown file with optional YAML frontmatter:

```markdown
---
version: 1.0.0
dependencies: ["identity/core-identity.md"]
---

# Module Title

Content here...
```

### The MANIFEST

`meta/MANIFEST.json` is the machine-readable inventory. When you add a module, update the manifest:

```json
{
  "modules": [
    {
      "id": "your-module",
      "path": "your-folder/your-module.md",
      "version": "1.0.0",
      "dependencies": ["identity/core-identity"]
    }
  ]
}
```

---

## How to Contribute Research

Found a paper, blog post, or production pattern that validates (or challenges) our architecture?

1. **Add to `RESEARCH.md`**
   - Citation format: Source, Contribution, Why we chose it
2. **Add to `picocloth-cli/docs/CITATIONS.md`**
   - Link the decision to the CLI code
3. **Open an issue** if it challenges existing design
4. **Open a PR** if it improves the code

---

## Commit Message Convention

We use conventional commits:

```
feat(memory): add vector DB search for digital twins
fix(fleet): resolve race condition in task queue
 docs: update ARCHITECTURE.md with Phase 3 details
research: add citation for graduated compaction paper
```

---

## Release Process

1. Update version in `picocloth-cli/src/picocloth_cli/__init__.py`
2. Update `CHANGELOG.md` (or `meta/CHANGELOG.md` for persona changes)
3. Tag: `git tag v0.2.0`
4. Push: `git push origin v0.2.0`

---

## Questions?

- Open an issue
- Start a discussion
- Read `REPO_MAP.md` to understand the codebase
- Read `RESEARCH.md` to understand the decisions

---

> *"The fleet is only as strong as its contributors. You are the fleet."* 🚀🪶
