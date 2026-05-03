# AGENTS.md — PicoCloth-CLI

## Agent-Facing Documentation

This file is for AI agents (like you!) working on the PicoCloth-CLI codebase.

---

## Project Structure

```
picocloth-cli/
├── pyproject.toml              # PEP 621 packaging
├── src/picocloth_cli/          # Main package
│   ├── main.py                 # Typer app root, subcommand registration
│   ├── core/                   # Infrastructure (no business logic)
│   ├── fleet/                  # Fleet communication (MCP, HTTP, state)
│   ├── intent/                 # Intent classification + complexity
│   ├── agent/                  # Spawn packages, memory slicing, registry
│   ├── memory/                 # 4-layer memory CRUD + compaction
│   ├── twin/                   # Digital twin search/extract/snapshot
│   ├── chat/                   # REPL, streaming, history
│   ├── commands/               # Typer command implementations
│   └── utils/                  # Shared utilities
├── tests/                      # pytest suite
└── docs/                       # Human + agent documentation
```

---

## Key Design Patterns

### 1. Citation-First Engineering
Every module must cite research in its docstring. Add citations to `utils/citations.py`.

### 2. Lock-File Coordination
All shared memory access uses `utils/files.py:lock_file()`. Never read/write shared files without locking.

### 3. Atomic Writes
All file writes use `atomic_write_json()` or `atomic_write_text()` to prevent corruption.

### 4. Intent → Complexity → Route Pipeline
```
User Input → classify_intent() → evaluate_complexity() → IntentEngine.resolve()
```

### 5. Spawn Packages
Agents are spawned with `agent/package.py:SpawnPackage`. Always include memory slices.

---

## Adding a New Command

1. Create a new file in `src/picocloth_cli/commands/`
2. Define `app = typer.Typer()` and subcommands
3. Register in `src/picocloth_cli/main.py` via `app.add_typer()`
4. Add tests in `tests/`
5. Update this file and README.md

---

## Testing

```bash
pytest                           # Run all tests
pytest tests/test_intent.py      # Run specific module
pytest -v --tb=short             # Verbose, short tracebacks
```

---

## Logging

Use `get_logger(__name__)` from `core/logging.py`. Structured JSON logs go to `~/.picocloth/logs/`.

---

## Configuration

User config lives at `~/.picocloth/config.yaml`. Pydantic models in `core/config.py`.

---

## Common Tasks

### Add a new intent type
1. Add to `intent/classifier.py:IntentType`
2. Add rule patterns to `RULE_PATTERNS`
3. Add node mapping to `intent/engine.py:_select_node_for_intent()`
4. Add execution path to `IntentEngine._execute_direct()`

### Add a new memory layer operation
1. Add function to appropriate `memory/*.py` file
2. Use `lock_file()` for writes
3. Export from `memory/__init__.py`

### Add a new citation
1. Register in `utils/citations.py:CitationRegistry.register()`
2. Reference by key in module docstrings

---

## Dependencies

Core: `typer`, `rich`, `textual`, `pydantic`, `httpx`, `pyyaml`, `structlog`
Dev: `pytest`, `pytest-asyncio`, `ruff`, `mypy`

No external databases — all state is file-based.
