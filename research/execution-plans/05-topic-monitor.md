# Execution Plan: Gap 9 (Original) — Monitoring / Webhook Infrastructure

## Gap Analysis
From the original 10 gaps: "No monitoring / webhook infrastructure for continuous tracking."

The parallel-agent-skills framework has no way to:
- Watch a topic over time
- Detect when new facts emerge
- Alert when contradictions appear
- Trigger extraction pipelines on a schedule

## Research Backing
- Event-driven architecture (EDA) patterns: webhook servers trigger actions on state changes
- Change detection: diff-based monitoring is the minimal viable approach for "$10 hardware"
- Cron-based polling: simplest scheduling for constrained environments
- Information Foraging (Pirolli & Card): sustained foraging requires periodic return to patches

## Cost Constraint
"Zero new infrastructure; must run on $10 hardware"
→ No webhook server. No Redis. No persistent queue.
→ Solution: Local JSONL state + diff + optional cron.

## File
`picocloth-cli/src/picocloth_cli/tools/topic_monitor.py`

---

## Step 5.1: Design `TopicMonitor` Data Model

```python
@dataclass
class WatchConfig:
    watch_id: str
    topic: str
    query: str
    interval_hours: int  # Polling interval
    last_run: str
    last_facts: list[str]  # fact_ids from previous run
    alert_on: list[str]  # ["new_facts", "contradictions", "confidence_drop"]
    created_at: str
    active: bool

@dataclass
class WatchDiff:
    watch_id: str
    run_at: str
    new_facts: list[dict]
    updated_facts: list[dict]
    contradictions_found: list[dict]
    confidence_changes: list[dict]
    summary: str
```

**Storage**:
- Watches: `shared/memory/watched-topics.jsonl`
- Diffs: `shared/memory/watch-diffs/<watch_id>/`

**Acceptance criteria**:
- [ ] WatchConfig serializes to JSONL
- [ ] Each watch gets a unique ID
- [ ] Diffs stored per-run for historical analysis

---

## Step 5.2: Write `TopicMonitor` Core

**Class structure**:
```python
class TopicMonitor:
    def __init__(self, watches_path: Path | None = None, diffs_dir: Path | None = None):
        self.watches_path = watches_path or Path("shared/memory/watched-topics.jsonl")
        self.diff_dir = diffs_dir or Path("shared/memory/watch-diffs")
        self.watches: dict[str, WatchConfig] = {}
        self._load()
    
    def add_watch(self, topic: str, query: str, interval_hours: int = 24, alert_on=None) -> str:
        # Create new watch, save, return watch_id
        pass
    
    def remove_watch(self, watch_id: str) -> bool:
        pass
    
    def list_watches(self) -> list[WatchConfig]:
        pass
    
    def run_watch(self, watch_id: str) -> WatchDiff | None:
        # 1. Load previous facts
        # 2. Run search + extract
        # 3. Diff against previous
        # 4. Store diff
        # 5. Update watch last_run
        pass
    
    def run_all_due(self) -> list[WatchDiff]:
        # Check each watch: is it due?
        # Run due watches, collect diffs
        pass
    
    def _diff_facts(self, old: list[dict], new: list[dict]) -> WatchDiff:
        # Find added, updated, contradicted facts
        pass
    
    def _save(self) -> None:
        pass
```

**Diff algorithm**:
```python
def _diff_facts(self, old: list[dict], new: list[dict]) -> WatchDiff:
    old_map = {f["fact_id"]: f for f in old}
    new_map = {f["fact_id"]: f for f in new}
    
    new_facts = [new_map[fid] for fid in new_map if fid not in old_map]
    updated = []
    contradictions = []
    confidence_changes = []
    
    for fid, new_f in new_map.items():
        if fid in old_map:
            old_f = old_map[fid]
            # Confidence change
            old_conf = old_f.get("confidence", 0)
            new_conf = new_f.get("confidence", 0)
            if abs(new_conf - old_conf) > 0.1:
                confidence_changes.append({
                    "fact_id": fid,
                    "old_confidence": old_conf,
                    "new_confidence": new_conf,
                    "claim": new_f.get("triple", {}).get("claim", ""),
                })
            # Contradiction check
            if new_f.get("contradicts") and not old_f.get("contradicts"):
                contradictions.append(new_f)
    
    return WatchDiff(...)
```

**Acceptance criteria**:
- [ ] `add_watch()` creates persistent watch config
- [ ] `run_watch()` produces meaningful diff
- [ ] `run_all_due()` respects interval_hours
- [ ] `python3 -m py_compile topic_monitor.py` passes

---

## Step 5.3: Add `watch` CLI Command

**File**: `picocloth-cli/src/picocloth_cli/commands/search.py`

**New command**:
```python
@app.command()
def watch(
    topic: str = typer.Argument(..., help="Topic to monitor"),
    query: str = typer.Option(None, "--query", "-q", help="Search query (defaults to topic)"),
    interval: int = typer.Option(24, "--interval", "-i", help="Hours between checks"),
    alert: str = typer.Option("new_facts", "--alert", "-a", help="Comma-separated: new_facts,contradictions,confidence_drop"),
    remove: bool = typer.Option(False, "--remove", help="Remove existing watch"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all watches"),
    run_now: bool = typer.Option(False, "--run-now", help="Run check immediately"),
):
    """Monitor a topic for new facts, contradictions, or confidence changes."""
    monitor = TopicMonitor()
    
    if list_all:
        # Display Rich table of all watches
        pass
    elif remove:
        # Remove watch by topic
        pass
    elif run_now:
        # Run watch immediately and show diff
        pass
    else:
        # Add new watch
        watch_id = monitor.add_watch(topic, query or topic, interval, alert.split(","))
        console.print(f"[green]✓[/green] Watch added: {watch_id}")
```

**Rich display for diff**:
- Header: "🔍 Watch Diff: {topic}"
- New facts: Green table with confidence and source
- Updated facts: Yellow table with old→new confidence
- Contradictions: Red alert box
- Summary: "N new, M updated, K contradictions"

**Acceptance criteria**:
- [ ] `picocloth search watch "AI regulation"` creates a watch
- [ ] `picocloth search watch --list` shows all active watches
- [ ] `picocloth search watch --run-now` runs immediately
- [ ] `picocloth search watch --remove` removes a watch

---

## Step 5.4: Add `watch-run` Background Command

**Problem**: `watch` needs to run periodically. No cron on $10 hardware? Use a simple loop.

**New command**:
```python
@app.command()
def watch_daemon(
    once: bool = typer.Option(False, "--once", help="Run once and exit"),
    interval: int = typer.Option(60, "--interval", help="Seconds between checks"),
):
    """Run the topic monitor daemon. Checks all due watches."""
    monitor = TopicMonitor()
    while True:
        diffs = monitor.run_all_due()
        for diff in diffs:
            if diff.new_facts or diff.contradictions_found:
                console.print(f"[bold green]Alert:[/bold green] {diff.summary}")
        if once:
            break
        time.sleep(interval)
```

**Note**: This is a foreground daemon. For true background, user can use `nohup` or `&`.

**Acceptance criteria**:
- [ ] `--once` runs due watches and exits
- [ ] Without `--once`, loops indefinitely
- [ ] Graceful exit on Ctrl-C

---

## Step 5.5: Integration with ExtractEngine

**File**: `picocloth-cli/src/picocloth_cli/tools/extract.py`

**Add method to `ExtractEngine`**:
```python
def watch_and_extract(self, query: str, topic: str) -> tuple[list[ExtractedFact], WatchDiff]:
    """Run extraction and compute diff against previous run."""
    # This is a convenience method for TopicMonitor to use
    facts, report = self.run([...], topic=topic)  # needs search results
    return facts, report
```

Actually, `TopicMonitor` should handle the search itself. Better design:
- `TopicMonitor` imports `ExtractEngine` and `SearchStrategyEngine`
- It builds queries, searches, extracts, diffs

**Acceptance criteria**:
- [ ] `TopicMonitor` can perform full search→extract→diff pipeline
- [ ] No circular imports

---

## Step 5.6: Skill Documentation

**File**: `shared/doctrine/skills/topic-monitor.md`

**Contents**:
- Why continuous monitoring matters (information decay)
- Diff algorithm explanation
- Alert types: new_facts, contradictions, confidence_drop
- CLI usage: `watch`, `watch --run-now`, `watch-daemon`
- Cron setup example for production servers

**Acceptance criteria**:
- [ ] Document explains diff semantics
- [ ] Example cron job shown

---

## Step 5.7: Test & Commit

**Test commands**:
```bash
cd /Users/shivaramgoud/picocloth-work
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/topic_monitor.py
python3 -c "
from picocloth_cli.tools.topic_monitor import TopicMonitor, WatchConfig
m = TopicMonitor()
wid = m.add_watch('test topic', 'test query', interval_hours=1)
print('Watch ID:', wid)
print('Watches:', len(m.list_watches()))
m.remove_watch(wid)
print('After remove:', len(m.list_watches()))
"
```

**Commit message**:
```
feat(monitor): Topic Monitor v1.0

- Add/remove/list watches with JSONL persistence
- Diff algorithm: new facts, updates, contradictions, confidence changes
- Alert types: new_facts, contradictions, confidence_drop
- CLI: search watch --list --run-now --remove
- CLI: search watch-daemon --once --interval
- Zero infrastructure: local state, foreground daemon, optional cron

Research: Event-driven architecture patterns,
Information Foraging (Pirolli & Card 1999)
```
