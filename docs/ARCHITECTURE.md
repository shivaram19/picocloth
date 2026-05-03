# 🪶 PicoCloth Architecture
## A Fleet of PicoClaws with Digital Twins & Shared Memory

### Vision
10 PicoClaw nodes (starting with 2) that operate as a cohesive intelligence fabric.
Each node has:
- **Unique behavior** (specialized system prompts + tools)
- **Shared memory** (4-layer architecture)
- **Digital twin** (snapshot before every compaction)
- **Fleet observability** (Langfuse + EventBus bridge)
- **Inter-node communication** (MCP Fleet Server)

---

## 🧠 The 4-Layer Shared Memory Architecture

Inspired by Graph Digital's production Katelyn Skills OS:

```
shared/
├── doctrine/          # Read-only skills, schemas, policies
│   ├── skills/
│   ├── schemas/
│   └── policies/
├── project/           # Durable structured facts (JSON)
│   ├── facts/
│   ├── decisions/
│   └── entities/
├── state/             # Operational truth (single source)
│   ├── fleet-state.json
│   ├── node-registry.json
│   └── task-queue.json
├── run/               # Ephemeral working memory per execution
│   └── {session-id}/
├── digital-twins/     # Snapshots before compaction
│   └── {node-id}/{timestamp}_pre_compaction.jsonl
└── compaction-archive/ # Post-compaction summaries
    └── {node-id}/{timestamp}_compaction_summary.md
```

### Layer Details

#### 1. `doctrine/` - The Constitution
- Skills (markdown with YAML frontmatter)
- Tool definitions shared across fleet
- Behavioral policies
- **Permissions:** Read-only for worker nodes. Updated via governed flows.

#### 2. `project/` - The Knowledge Graph
- Durable facts extracted from conversations
- Decisions made by the fleet
- Entity relationships
- **Format:** Structured JSON with timestamps, sources, confidence scores
- **Updated:** Via pre-compaction hooks and explicit memory writes

#### 3. `state/` - The Nervous System
- Fleet registry (which nodes are alive)
- Task queue (pending, running, completed)
- Load balancer state
- **Updated:** Real-time by orchestrator

#### 4. `run/` - Working Memory
- Per-session ephemeral context
- Active tool call sequences
- In-flight subagent tasks
- **Lifecycle:** Created at turn start, archived or discarded at turn end

---

## 🤖 Node Architecture

### Node-A: The Curiosity Brain (Researcher)
```yaml
role: research_orchestrator
system_prompt: |
  You are the Curiosity Engine of the PicoCloth fleet.
  Your mission: Find gaps in knowledge and spawn investigations.
  
  Behaviors:
  - When you encounter something unknown, spawn a subagent to research it
  - When 3 scouts report similar unknowns, synthesize and escalate
  - Write all findings to shared/project/facts/
  - Maintain a "curiosity log" of open questions
  
  Tools: web_search, spawn, subagent, write_file, read_file
  Model Routing: Light model for triage, heavy for synthesis
```

### Node-B: The Executor (Coder/Builder)
```yaml
role: execution_engineer
system_prompt: |
  You are the Builder of the PicoCloth fleet.
  Your mission: Execute tasks, write code, and build tools.
  
  Behaviors:
  - Receive tasks from the orchestrator or Curiosity Brain
  - Break complex builds into parallel subagent tasks
  - Test everything before marking complete
  - Write code to shared/doctrine/skills/
  
  Tools: shell, write_file, read_file, spawn, subagent, message
  Model Routing: Heavy model for coding, light for file ops
```

---

## 🔄 Digital Twin / Pre-Compaction System

### Trigger Condition
When a node's context usage reaches **75%** of its window (PicoClaw's default soft limit),
we trigger the Digital Twin Protocol BEFORE compaction:

```
Context Usage: 75% reached
    |
    v
[Digital Twin Hook Fires]
    |
    +---> Extract durable facts (up to 8 facts)
    +---> Save full conversation snapshot to digital-twins/{node-id}/
    +---> Update project/ facts database
    +---> Emit event to fleet EventBus
    |
    v
[Compaction Proceeds]
    |
    +---> Summarize and truncate
    +---> Save compaction summary
```

### Digital Twin File Format
```json
{
  "twin_id": "node-a-20260423-103000",
  "node_id": "node-a",
  "session_key": "telegram:123456",
  "trigger": "context_budget_75_percent",
  "timestamp": "2026-04-23T10:30:00Z",
  "context_usage": {
    "used_tokens": 12000,
    "total_tokens": 16000,
    "used_percent": 75
  },
  "conversation_snapshot": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "extracted_facts": [
    {"key": "user_prefers_postgresql", "content": "User uses PostgreSQL 16", "confidence": 0.95}
  ],
  "active_subagents": [
    {"id": "subagent-3", "task": "Research MCP protocols", "status": "running"}
  ],
  "compaction_summary": null
}
```

---

## 📡 Fleet Communication (MCP Fleet Server)

The MCP Fleet Server acts as a "shared tool registry" across all nodes:

```
Node-A                    MCP Fleet Server                  Node-B
  |                             |                               |
  |-- query_fleet_state ------->|                               |
  |                             |-- broadcast_state_update ---->|
  |                             |                               |
  |-- spawn_remote_task ------->|-- delegate_to_node --------->|
  |                             |                               |
  |<-- task_result -------------|<-- report_completion ---------|
```

### Fleet Tools ( exposed via MCP )
- `fleet_query_state` - Get health of all nodes
- `fleet_spawn_task` - Delegate task to specific node
- `fleet_broadcast` - Send message to all nodes
- `fleet_memory_read` - Read from shared project/
- `fleet_memory_write` - Write to shared project/
- `fleet_digital_twin_search` - Query historical twins

---

## 📊 Observability Stack

### Langfuse (Self-Hosted)
- **Traces:** Every LLM call, tool execution, subagent spawn
- **Cost Tracking:** Per node, per model, per session
- **Evaluations:** LLM-as-a-judge for output quality
- **Dashboard:** Fleet-wide view of all 10 nodes

### Custom Fleet Dashboard
- Node health (CPU, RAM, active turns)
- EventBus throughput
- Subagent queue depth
- Digital twin count
- Compaction frequency

---

## 🚀 Deployment Topology

### Phase 1: 2 Nodes (TODAY)
```
Machine (Your Current Box)
├── Node-A (Curiosity Brain)
│   ├── Port: 18790 (gateway)
│   ├── Memory: local + shared/
│   └── Telegram: @YourCuriosityBot
├── Node-B (Executor)
│   ├── Port: 18791 (gateway)
│   ├── Memory: local + shared/
│   └── Telegram: @YourBuilderBot
├── Shared Memory (shared/)
├── MCP Fleet Server (Port: 18880)
└── Langfuse (Port: 3000)
```

### Phase 2: 10 Nodes (FUTURE)
```
PicoCloth Mesh
├── 3x Curiosity Nodes (Research, Monitoring, Analysis)
├── 3x Executor Nodes (Code, Deploy, Test)
├── 2x Memory Nodes (Long-term storage, retrieval)
├── 1x Orchestrator Node (Load balancing, routing)
└── 1x Safety Node (Budget guards, approval hooks)
```

---

## 🛡️ Security & Safety

### Budget Guard (Per Node)
```json
{
  "daily_token_budget": 1000000,
  "daily_cost_budget_usd": 10.00,
  "max_subagent_depth": 3,
  "max_concurrent_subagents": 5,
  "auto_shutdown_on_budget_exhaustion": true
}
```

### Approval Hooks
- `shell` commands > $risk_threshold require approval
- `spawn` tasks targeting external nodes require approval
- `write_file` to `doctrine/` requires approval

---

## 📈 Scaling Roadmap

| Phase | Nodes | Focus |
|-------|-------|-------|
| 1 | 2 | Local deployment, shared memory, basic comms |
| 2 | 5 | Add memory nodes, load balancer, Telegram |
| 3 | 10 | Full mesh, custom classifier, GAN experiments |
| 4 | 25+ | Distributed across machines, auto-scaling |
