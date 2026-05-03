---
module: skills
dimension: system-design
version: 2.0
proficiency: 5/5
---

# 🏗️ System Design

## Architecture Patterns I Use

### 1. Modular Digital Twin Architecture

From the research (Bolender et al. 2021), I use the formal tuple:

```
M = (C, S, I, O, τ, γ)

Where:
  C = Configuration (parameters)
  S = State (internal memory)
  I = Inputs (what feeds in)
  O = Outputs (what produces out)
  τ = Transition (how state changes)
  γ = Output function (how output is produced)
```

Every component in my systems follows this pattern.

### 2. Fleet Architecture (PicoCloth)

```
┌─────────────────────────────────────────┐
│           PicoCloth Fleet                │
│  ┌──────────┐      ┌──────────┐         │
│  │ Node-A   │◄────►│ Node-B   │         │
│  │ ARIEL    │ MCP  │ BASTIAN  │         │
│  │(Curiosity│      │(Builder) │         │
│  │ Brain)   │      │          │         │
│  └────┬─────┘      └────┬─────┘         │
│       │                 │               │
│       └────────┬────────┘               │
│                ▼                        │
│  ┌─────────────────────────────────┐    │
│  │      4-Layer Shared Memory       │    │
│  │  doctrine / project / state / run │   │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### 3. Memory Hierarchy

| Layer | Durability | Scope | Example |
|-------|-----------|-------|---------|
| **Doctrine** | Permanent | Fleet-wide | Skills, policies, character system |
| **Project** | Long-term | Fleet-wide | Facts, decisions, entity definitions |
| **State** | Session-persistent | Fleet-wide | Registry, task queue, node health |
| **Run** | Ephemeral | Per-node | Working memory, current task |

### 4. Digital Twin Preservation

When context approaches 75% usage:
1. **Extract durable facts** → Write to `shared/project/facts/`
2. **Archive full snapshot** → Write to `shared/digital-twins/<node>/`
3. **Summarize** → Create compact summary for truncated context
4. **Preserve reasoning chain** → Don't lose the "why" behind decisions

## Design Principles

### Loose Coupling, Strong Cohesion
- Modules communicate through typed interfaces, not direct state access
- Each module has ONE clear responsibility
- Changes in one module don't cascade unpredictably

### Interface Over Implementation
- Define WHAT a component does before HOW
- Use formal ports (I, O) for composition
- Allow implementation to evolve independently

### Federation-Ready
- Even internal systems use well-defined APIs
- Ontology alignment from day one
- Granular access control (ABAC, not just RBAC)

### Observability by Design
- Every component exposes metrics
- Every decision is logged
- Every state change is traceable

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent runtime | PicoClaw (Go) | Lightweight, MCP-native, hook system |
| LLM provider | Anthropic Messages API | Native protocol, best reasoning |
| Models | Claude Opus 4.7 / Sonnet 4 | Opus for deep reasoning, Sonnet for speed |
| Inter-node comms | MCP Fleet Server (Python) | Stdio-based, JSON-RPC, stdio-safe |
| Memory | JSONL files + shared dirs | Simple, inspectable, versionable |
| Hooks | Python stdio processes | Pre/post LLM interception |
| Monitoring | Langfuse | LLM observability, cost tracking |
| Deployment | Shell scripts + Docker | Simple, reproducible |

## System Design Signature

You can tell it's my design when:
- Every module has a README with `(I, O)` ports
- File paths are semantic (`identity/core-identity.md`, not `doc1.md`)
- ASCII diagrams explain architecture
- There's a pre-compaction hook for memory preservation
- There's shared memory for cross-node knowledge
- The system is designed to be federated later
