# Skill: Topic Monitor v1.0

## Research

- **Event-driven architecture (EDA)**: State change triggers actions. In information monitoring, changes in facts should trigger alerts or downstream processing.

- **Change detection**: Diff-based monitoring is the minimal viable approach for constrained environments. No Redis, no queue server, no webhook infrastructure needed.

- **Pirolli & Card (1999)**: Information Foraging Theory — sustained foraging requires periodic return to patches. Information decays; re-checking is essential for maintaining accuracy.

## Architecture

```
WatchConfig → Scheduled Check → Search + Extract → Diff against Previous
→ Alert if Changes → Store Diff → Update Watch State
```

**Diff algorithm**:
- **New facts**: fact_id not seen in previous run
- **Updated facts**: fact_id exists but hash changed
- **Confidence changes**: tracked per fact over time

**Storage**:
- Watches: `shared/memory/watched-topics.jsonl`
- Diffs: `shared/memory/watch-diffs/<watch_id>-<timestamp>.json`

**Scheduling**: Foreground daemon with configurable interval. Optional cron for production servers.

## CLI Usage

```bash
# Add a watch
picocloth search watch "AI regulation"

# List all watches
picocloth search watch --list

# Run check immediately
picocloth search watch "AI regulation" --run-now

# Remove a watch
picocloth search watch "AI regulation" --remove

# Run daemon (checks all due watches)
picocloth search watch-daemon --once

# Continuous monitoring
picocloth search watch-daemon --interval 300
```

## Why This Design

We chose **JSONL persistence** over a database because it requires zero infrastructure. A SQLite database would also work, but JSONL is consistent with the rest of the PicoCloth memory architecture.

We chose a **foreground daemon** over a background service because:
1. It works on "$10 hardware" without systemd or cron
2. It's transparent — the user sees every check
3. It can be wrapped in cron or systemd by the user if needed

We chose **hash-based diffing** over LLM-based comparison because:
1. It's deterministic and fast
2. It doesn't require LLM calls (cost constraint)
3. It catches factual changes, not just rewordings
