#!/usr/bin/env bash
# PicoCloth Shared Memory Initialization
# Creates the 4-layer memory architecture for the fleet

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="${SCRIPT_DIR}/../shared"

echo "🪶 PicoCloth Shared Memory Initialization"
echo "=========================================="

# Layer 1: Doctrine (Read-only constitution)
mkdir -p "${SHARED_DIR}/doctrine/skills"
mkdir -p "${SHARED_DIR}/doctrine/schemas"
mkdir -p "${SHARED_DIR}/doctrine/policies"

cat > "${SHARED_DIR}/doctrine/policies/fleet-constitution.md" << 'EOF'
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
EOF

cat > "${SHARED_DIR}/doctrine/skills/web-research-template.md" << 'EOF'
---
title: Web Research Skill
trigger: research_task
author: PicoCloth
---

# Web Research Protocol

1. Search broadly (3-5 queries)
2. Read top 3 results deeply
3. Extract key facts with confidence scores
4. Cite sources
5. Write findings to shared/project/facts/{topic}.jsonl
6. Report completion to fleet state
EOF

# Layer 2: Project (Durable facts)
mkdir -p "${SHARED_DIR}/project/facts"
mkdir -p "${SHARED_DIR}/project/decisions"
mkdir -p "${SHARED_DIR}/project/entities"

cat > "${SHARED_DIR}/project/entities/fleet-nodes.json" << 'EOF'
{
  "schema_version": "1.0",
  "entity_type": "fleet_node",
  "nodes": [
    {
      "id": "node-a",
      "name": "Curiosity Brain",
      "role": "research_orchestrator",
      "capabilities": ["web_search", "spawn", "synthesize"],
      "model_preference": "light_for_triage_heavy_for_synthesis",
      "status": "registered"
    },
    {
      "id": "node-b",
      "name": "Executor Builder",
      "role": "execution_engineer",
      "capabilities": ["shell", "write_file", "test", "deploy"],
      "model_preference": "heavy_for_code_light_for_ops",
      "status": "registered"
    }
  ],
  "created_at": "2026-04-23T10:00:00Z"
}
EOF

# Layer 3: State (Operational truth)
mkdir -p "${SHARED_DIR}/state"

cat > "${SHARED_DIR}/state/fleet-state.json" << 'EOF'
{
  "version": "1.0",
  "last_updated": "2026-04-23T10:00:00Z",
  "orchestrator": "master",
  "nodes": {
    "node-a": {
      "status": "initializing",
      "role": "curiosity-brain",
      "last_heartbeat": null,
      "active_turns": 0,
      "active_subagents": 0,
      "daily_tokens_used": 0,
      "daily_cost_usd": 0.0
    },
    "node-b": {
      "status": "initializing",
      "role": "executor-builder",
      "last_heartbeat": null,
      "active_turns": 0,
      "active_subagents": 0,
      "daily_tokens_used": 0,
      "daily_cost_usd": 0.0
    }
  },
  "metrics": {
    "total_tasks_completed": 0,
    "total_digital_twins_created": 0,
    "total_compactions": 0
  }
}
EOF

cat > "${SHARED_DIR}/state/task-queue.json" << 'EOF'
[]
EOF

# Layer 4: Run (Ephemeral - empty initially)
mkdir -p "${SHARED_DIR}/run"

# Digital Twins Archive
mkdir -p "${SHARED_DIR}/digital-twins/node-a"
mkdir -p "${SHARED_DIR}/digital-twins/node-b"

# Compaction Archive
mkdir -p "${SHARED_DIR}/compaction-archive/node-a"
mkdir -p "${SHARED_DIR}/compaction-archive/node-b"

echo "✅ Shared memory initialized at: ${SHARED_DIR}"
echo ""
echo "Structure:"
tree -L 3 "${SHARED_DIR}" 2>/dev/null || find "${SHARED_DIR}" -maxdepth 3 -print | sed 's|^'"${SHARED_DIR}"'/||' | sed 's|^|  |'
