# Phase Transition Plan: Gap Fill Execution

> One phase at a time. No phase starts until the previous phase is validated.
> After each phase: INTROSPECT (what just happened) → TALLY (checklist) → RETROSPECT (what worked, what didn't) → DECIDE (proceed or fix).

---

## Phase 0: State Tally (STARTING POSITION)

**Before any integration work begins.**

### Checklist
- [ ] 5 new tool files exist and compile
- [ ] All 5 classes instantiate without errors
- [ ] All 5 classes pass basic smoke tests
- [ ] Existing CLI (`extract`, `search`) still works
- [ ] Existing MCP server still starts
- [ ] Git working tree is clean

### Validation Command
```bash
cd /Users/shivaramgoud/picocloth-work
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/*.py
python3 -c "from picocloth_cli.main import app; print('CLI imports OK')"
python3 -m py_compile mcp-fleet-server/server.py
git status --short
```

### Tally Board
| Component | Exists | Compiles | Instantiates | Smoke Test |
|-----------|--------|----------|--------------|------------|
| verification_pool.py | ✅ | ✅ | ✅ | ✅ |
| citation_validator.py | ✅ | ✅ | ✅ | ✅ |
| retrospective_optimizer.py | ✅ | ✅ | ✅ | ✅ |
| indie_discovery.py | ✅ | ✅ | ✅ | ✅ |
| topic_monitor.py | ✅ | ✅ | ✅ | ✅ |
| ExtractEngine (existing) | ✅ | ✅ | — | — |
| SearchStrategyEngine (existing) | ✅ | ✅ | — | — |
| CLI commands (existing) | ✅ | ✅ | — | — |
| MCP server (existing) | ✅ | ✅ | — | — |

### Gate Decision
**ONLY proceed to Phase A if ALL checks pass.**
If any fail: STOP. Fix before proceeding.

---

## Phase A: ExtractEngine Integration

**Goal**: Wire `CitationValidator` and `FleetVerificationPool` into `ExtractEngine.run()`.

### Input State
- Phase 0 tally complete
- `ExtractEngine` has `run(inputs, topic)` signature
- `ExtractedFact` has `verified_by: dict` field

### Work
1. Add `validate_citations: bool = False` param to `run()`
2. Add `verify: bool = False` param to `run()`
3. After cross-reference, before deduplication:
   - If `validate_citations`: run `CitationValidator.validate_batch()`
   - Attach reports to `fact.verified_by["citation_validation"]`
   - Adjust confidence by citation health score
4. After deduplication/merge:
   - If `verify`: run `FleetVerificationPool.verify_batch()`
   - Attach results to `fact.verified_by["fleet_verification"]`
   - Adjust confidence by verification verdict
5. Add `to_bibliography(path, style)` method to `ExtractEngine`

### Output State
- `ExtractEngine.run(validate_citations=True)` produces facts with citation reports
- `ExtractEngine.run(verify=True)` produces facts with verification results
- Confidence scores reflect both citation health and fleet verification
- `to_bibliography()` generates deduplicated bibliographies

### Validation Commands
```bash
# Compile modified file
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/extract.py

# Import test
python3 -c "
from picocloth_cli.tools.extract import ExtractEngine
engine = ExtractEngine()
# Test with validation
facts, report = engine.run([
    {'href': 'https://example.com', 'title': 'Test', 'body': '50% of projects fail.'}
], topic='test', validate_citations=True)
print(f'Facts: {len(facts)}, Citation reports: {sum(1 for f in facts if f.verified_by.get(\"citation_validation\"))}')
"

# Test bibliography
python3 -c "
from picocloth_cli.tools.extract import ExtractEngine
engine = ExtractEngine()
engine.run([{'href': 'https://a.com', 'title': 'A', 'body': 'test'}], topic='t')
engine.to_bibliography('/tmp/test-bib.md', style='markdown')
print(open('/tmp/test-bib.md').read()[:200])
"
```

### Retrospective Questions (answer before proceeding)
1. Did the modified `extract.py` tool compile on first try?
2. Did `validate_citations=True` attach reports to all facts?
3. Did `verify=True` attach verification results?
4. Are confidence adjustments conservative (not over-adjusting)?
5. Did `to_bibliography()` deduplicate sources correctly?

### Gate Decision
**ONLY proceed to Phase B if ALL validation commands pass.**

---

## Phase B: CLI Extract Commands

**Goal**: Update `picocloth extract` subcommands to expose validation and verification.

### Input State
- Phase A complete and validated
- `ExtractEngine.run()` accepts `validate_citations` and `verify` params

### Work
1. **Modify `from_file` command**:
   - Add `--validate-citations` flag
   - Add `--verify` flag
   - Add `--bibliography` / `-b` path option
   - Pass flags to `engine.run()`
   - If `--bibliography`, call `engine.to_bibliography()`

2. **Modify `search` command**:
   - Add same 3 flags as `from_file`
   - Pass flags to `engine.run()`

3. **Rewrite `verify` command**:
   - Load fact from memory by ID
   - Create `FleetVerificationPool`
   - Call `pool.verify_fact()` with `--strategy`
   - Display Rich vote table
   - Store result back to memory

4. **Add `validate-citations` command**:
   - Load facts from JSONL file
   - Run `CitationValidator`
   - Display Rich health score table
   - Optionally `--fix` and write back

### Output State
- `picocloth extract search "topic" --validate-citations` works
- `picocloth extract search "topic" --verify` works
- `picocloth extract verify <fact_id> --strategy weighted` works
- `picocloth extract validate-citations facts.jsonl` works
- `picocloth extract from-file results.json --bibliography bib.md` works

### Validation Commands
```bash
# Compile
python3 -m py_compile picocloth-cli/src/picocloth_cli/commands/extract.py

# Import test
python3 -c "from picocloth_cli.commands import extract as extract_cmd; print('extract commands import OK')"

# CLI help test
python3 -m picocloth_cli extract --help
python3 -m picocloth_cli extract verify --help
python3 -m picocloth_cli extract validate-citations --help
```

### Retrospective Questions
1. Did all 4 commands show in `--help`?
2. Did Typer argument parsing work correctly?
3. Did Rich table display code compile?
4. Are the new flags discoverable and well-documented?
5. Did any existing command break?

### Gate Decision
**ONLY proceed to Phase C if CLI help shows all commands and no errors.**

---

## Phase C: CLI Search Commands

**Goal**: Update `picocloth search` subcommands to expose discovery, optimization, and monitoring.

### Input State
- Phase B complete and validated
- `IndieWebDiscoveryEngine`, `RetrospectiveOptimizer`, `TopicMonitor` all instantiate

### Work
1. **Add `discover` command**:
   - Create `IndieWebDiscoveryEngine`
   - Call `discover(topic, limit, include_hn)`
   - Display Rich table of sources
   - If `--extract`, run `ExtractEngine` on discovered URLs

2. **Add `optimize` command**:
   - Create `RetrospectiveOptimizer`
   - Call `suggest_reformulation(topic)`
   - Display Rich table of suggestions
   - If `--execute`, run searches

3. **Add `watch` command**:
   - Create `TopicMonitor`
   - `add_watch` / `list` / `run-now` / `remove` modes
   - Display Rich diff output

4. **Add `watch-daemon` command**:
   - Run `TopicMonitor.run_all_due()` in loop
   - `--once` for single pass
   - Display alerts for changes

5. **Implement `_execute_plan()`**:
   - Replace placeholder with actual DDGS execution
   - Limit to 3 queries × 5 results = 15 max (cost control)
   - Auto-record yield after execution

### Output State
- `picocloth search discover "distributed systems"` shows sources
- `picocloth search optimize "AI market"` shows suggestions
- `picocloth search watch "AI regulation"` creates watch
- `picocloth search watch-daemon --once` runs due watches
- `picocloth search clever "topic" --execute` actually searches and extracts

### Validation Commands
```bash
# Compile
python3 -m py_compile picocloth-cli/src/picocloth_cli/commands/search.py

# Import test
python3 -c "from picocloth_cli.commands import search as search_cmd; print('search commands import OK')"

# CLI help test
python3 -m picocloth_cli search --help
python3 -m picocloth_cli search discover --help
python3 -m picocloth_cli search optimize --help
python3 -m picocloth_cli search watch --help
python3 -m picocloth_cli search watch-daemon --help
```

### Retrospective Questions
1. Did all 5 new commands show in `--help`?
2. Did `_execute_plan()` stop being a placeholder?
3. Does yield auto-record after `--execute`?
4. Did any existing search command break?
5. Are command descriptions clear and consistent?

### Gate Decision
**ONLY proceed to Phase D if CLI help shows all commands and no errors.**

---

## Phase D: MCP Fleet Server

**Goal**: Register 4 new tools on the MCP fleet server.

### Input State
- Phase C complete and validated
- MCP server starts and existing tools work

### Work
1. Add `fleet_verify` to `TOOLS` dict
2. Add `fleet_validate_citations` to `TOOLS` dict
3. Add `fleet_discover` to `TOOLS` dict
4. Add `fleet_optimize` to `TOOLS` dict
5. Add 4 lightweight handler functions
6. Wire into `handle_tool_call()`

**Design rule**: Handlers must be minimal and self-contained. No imports of CLI tools (server is zero-dependency). Inline logic only.

### Output State
- `fleet_verify` returns simulated verification result
- `fleet_validate_citations` returns basic error reports
- `fleet_discover` returns registry sources
- `fleet_optimize` returns generic suggestions
- Existing 7 tools still work

### Validation Commands
```bash
# Compile
python3 -m py_compile mcp-fleet-server/server.py

# Start server and test (quick handshake)
python3 -c "
import subprocess, json, sys, time
proc = subprocess.Popen([sys.executable, 'mcp-fleet-server/server.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
# initialize
proc.stdin.write(json.dumps({'jsonrpc':'2.0','id':'1','method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'1.0'}}}) + '\n')
proc.stdin.flush()
resp = proc.stdout.readline()
print('Init:', 'result' in resp)
# tools/list
proc.stdin.write(json.dumps({'jsonrpc':'2.0','id':'2','method':'tools/list'}) + '\n')
proc.stdin.flush()
resp = proc.stdout.readline()
data = json.loads(resp)
tools = [t['name'] for t in data.get('result', {}).get('tools', [])]
print('Tools:', tools)
print('fleet_verify' in tools, 'fleet_discover' in tools)
proc.terminate()
"
```

### Retrospective Questions
1. Did the server start without errors?
2. Are all 11 tools (7 old + 4 new) listed?
3. Did any existing tool handler break?
4. Are new handlers truly zero-dependency?
5. Does server still respond to `initialize` correctly?

### Gate Decision
**ONLY proceed to Phase E if MCP server starts and lists all 11 tools.**

---

## Phase E: Skill Documentation

**Goal**: Write 5 skill docs in `shared/doctrine/skills/`.

### Input State
- Phase D complete and validated
- All code is finalized (no more API changes expected)

### Work
Write one doc per gap:
1. `verification-pool.md` — Gap 5
2. `citation-validator.md` — Gap 9
3. `retrospective-optimizer.md` — Gap 11
4. `indie-discovery.md` — Gap 13
5. `topic-monitor.md` — Gap 9 (original)

Each doc: research citations, architecture, CLI usage, MCP reference, WHY explanations.

### Output State
- 5 markdown files exist in `shared/doctrine/skills/`
- Each file has ≥2 research citations
- Each file has CLI usage examples

### Validation Commands
```bash
ls shared/doctrine/skills/*.md | wc -l
# Should output 5 (plus existing 2 = 7 total)
```

### Retrospective Questions
1. Do all docs exist?
2. Are citations accurate and specific?
3. Is there a doc for every filled gap?
4. Would a new developer understand how to use each feature?

### Gate Decision
**ONLY proceed to Phase F if all 5 docs exist and are non-empty.**

---

## Phase F: Final Test & Commit

**Goal**: End-to-end validation and git commit.

### Input State
- All prior phases complete
- All code written, all docs written

### Work
1. Compile every modified file
2. Run import test for entire CLI
3. Run CLI `--help` for all command groups
4. Run `git add -A`
5. Write commit message
6. `git commit`
7. Verify commit with `git log -1 --stat`

### Output State
- Working tree clean
- One commit with all changes
- Commit message references all gaps and research

### Validation Commands
```bash
# Final compilation sweep
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/*.py
python3 -m py_compile picocloth-cli/src/picocloth_cli/commands/*.py
python3 -m py_compile mcp-fleet-server/server.py

# Full import test
python3 -c "from picocloth_cli.main import app; print('Full CLI OK')"

# CLI help sweep
python3 -m picocloth_cli --help
python3 -m picocloth_cli extract --help
python3 -m picocloth_cli search --help

# Git status
git status
```

### Final Retrospective Questions
1. Did every file compile?
2. Did the full CLI import successfully?
3. Did all `--help` commands work?
4. Is the commit message comprehensive?
5. Are there any untracked files that should be in `.gitignore`?

### Gate Decision
**DONE when commit is clean and working tree is empty.**

---

## Running Tally Board (Update After Each Phase)

| Phase | Status | Files Changed | Lines Added | Compile OK | Test OK | Retro Done |
|-------|--------|--------------|-------------|------------|---------|------------|
| 0: State Tally | 🔲 | — | — | — | — | — |
| A: ExtractEngine | 🔲 | 1 | ~30 | — | — | — |
| B: CLI Extract | 🔲 | 1 | ~80 | — | — | — |
| C: CLI Search | 🔲 | 1 | ~120 | — | — | — |
| D: MCP Server | 🔲 | 1 | ~60 | — | — | — |
| E: Skill Docs | 🔲 | 5 | ~200 | — | — | — |
| F: Test & Commit | 🔲 | — | — | — | — | — |

**Total estimated lines to write**: ~490 lines across 8 files.
**Total estimated time**: 20-30 minutes if no blockers.
