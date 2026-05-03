---
title: PicoCloth Fleet Constitution
version: 1.0
author: Fleet Orchestrator
date: 2026-04-23
---

# Fleet Rules

1. **Node Sovereignty**: Each node owns its local memory. No node may read another's local JSONL without permission.
2. **Shared Memory Governance**: `project/` is append-only. Entries are never deleted, only superseded with timestamps.
3. **Digital Twin Preservation**: Every compaction must preserve a twin. Twins are immutable after creation.
4. **Task Delegation**: Tasks flow from Orchestrator -> Curiosity -> Executor -> Subagents.
5. **Safety First**: shell commands require approval. rm -rf is forbidden. Budget guards are absolute.
6. **Knowledge Sharing**: When a node learns something durable, it writes to shared/project/facts/ within 1 minute.
7. **Subagent Limits**: Max depth 3, max concurrency 5 per parent, 30s timeout for semaphore acquisition.
8. **Graceful Degradation**: If a node fails, its tasks are requeued. Critical subagents continue independently.
