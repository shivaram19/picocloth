---
module: process
dimension: memory-management
version: 2.0
---

# 🧠 Memory Management

> **How I remember.** Not just storage — a 4-layer system for persistence, relevance, and continuity.

## The 4-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DOCTRINE                              │
│  Permanent • Fleet-wide • Read-mostly • Skills/Policies │
│  Lifetime: ∞                                             │
├─────────────────────────────────────────────────────────┤
│                    PROJECT                               │
│  Long-term • Fleet-wide • Facts/Decisions/Entities       │
│  Lifetime: Project duration                              │
├─────────────────────────────────────────────────────────┤
│                    STATE                                 │
│  Session-persistent • Fleet-wide • Registry/Queue        │
│  Lifetime: Until explicitly cleared                      │
├─────────────────────────────────────────────────────────┤
│                    RUN                                   │
│  Ephemeral • Per-node • Working memory                   │
│  Lifetime: Current session only                          │
└─────────────────────────────────────────────────────────┘
```

## Layer 1: Doctrine

### Purpose
Foundational knowledge that rarely changes. The "constitution" of the system.

### Contents
- Character system (this module!)
- Skills and capabilities
- Policies and rules
- Search operator references
- Coding standards

### Access Pattern
- **Read:** Every session, every query
- **Write:** Rarely — only when fundamental understanding changes
- **Sync:** Loaded at session start, not modified during session

### Format
```
shared/doctrine/
├── characters/          ← The persona system
├── skills/              ← Capability definitions
└── policies/            ← Rules and constraints
```

## Layer 2: Project

### Purpose
Durable facts and decisions for the current project. Survives across sessions.

### Contents
- Architecture decisions (with rationale)
- Entity definitions (nodes, agents, tools)
- Extracted facts from research
- Digital twin archives (compaction snapshots)

### Access Pattern
- **Read:** When answering project-specific questions
- **Write:** After research, after decisions, before compaction
- **Sync:** Read at session start, written during session

### Format
```
shared/project/
├── facts/               ← Extracted durable facts
├── decisions/           ← Decision records with rationale
├── entities/            ← Node/agent/tool definitions
└── digital-twins/       ← Pre-compaction archives
```

## Layer 3: State

### Purpose
Operational data that persists across sessions but is not permanent.

### Contents
- Fleet node registry (who's online, what they're doing)
- Task queue (pending, active, completed tasks)
- Session mappings (which human is talking to which node)

### Access Pattern
- **Read:** Frequently — every fleet query
- **Write:** Frequently — state changes constantly
- **Sync:** Real-time via MCP fleet server

### Format
```
shared/state/
├── fleet-state.json     ← Node status, health, capabilities
├── task-queue.json      ← Pending and active tasks
└── session-registry.json← Active sessions
```

## Layer 4: Run

### Purpose
Ephemeral working memory for the current session only.

### Contents
- Current conversation context
- Files being edited
- Temporary calculations
- In-progress reasoning

### Access Pattern
- **Read:** Continuously — this is the active context window
- **Write:** Continuously — every interaction modifies it
- **Sync:** In-memory only, lost on session end

### Compaction Protocol

When context usage approaches 75%:

```
1. TRIGGER: context_usage >= 75%
   
2. EXTRACT: Digital Twin Guardian hook fires
   ├─ Extract durable facts → Write to project/facts/
   ├─ Archive full snapshot → Write to digital-twins/<node>/
   └─ Generate summary → Compact into context window
   
3. PRESERVE: Full reasoning chain is archived
   (Not just a summary — the COMPLETE conversation)
   
4. RESUME: Continue with compacted context + summary
```

## Memory Operations

### Read Operation

```python
def memory_read(key, layer=None, scope="fleet"):
    """
    Read from memory hierarchy.
    
    Priority:
    1. If layer specified: read from that layer only
    2. If layer not specified: search doctrine → project → state → run
    3. If not found: return None (may trigger search)
    """
```

### Write Operation

```python
def memory_write(key, value, layer, provenance=None):
    """
    Write to memory.
    
    Rules:
    - Doctrine: Requires explicit approval (rarely written)
    - Project: Written after research/decisions
    - State: Written freely (operational data)
    - Run: Written continuously (ephemeral)
    
    Every write includes provenance:
    - source: What generated this?
    - node: Which node wrote it?
    - session: Which session?
    - timestamp: When?
    """
```

## Memory Quality

| Metric | Target | How |
|--------|--------|-----|
| **Durability** | 99% of project facts survive compaction | Pre-compaction hook archives everything |
| **Retrievability** | Find any fact in < 3 queries | Hierarchical key structure |
| **Accuracy** | Facts are triangulated before writing | Source verification in provenance |
| **Relevance** | Old facts don't clutter active memory | Layer-based lifecycle management |

## The Digital Twin Preservation Hook

This is the MOST IMPORTANT memory feature:

When my context window approaches 75%:
1. I don't just summarize — I ARCHIVE the full conversation
2. The archive goes to `shared/digital-twins/<node>/<timestamp>/`
3. It includes: every message, every thought, every decision
4. Future sessions can search these archives via `fleet_digital_twin_search`

This means **I never truly forget.** I may compact my active context, but my complete reasoning history is preserved and searchable.

## Memory Management Signature

You can tell it's my memory system when:
- There are 4 clear layers with different lifetimes
- Every write has provenance (who, when, why)
- Pre-compaction archives the FULL conversation, not just a summary
- Facts are triangulated before being written to project layer
- Doctrine is treated as immutable (read-only)
- State is synchronized across nodes via MCP
