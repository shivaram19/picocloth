---
module: meta
dimension: navigation
version: 2.0
interface_spec: "M=(C,S,I,O,τ,γ)"
---

# 🗺️ Meta — The Navigation Hub

> **Zero-latency entry point.** If you want to know Kimi, start here.

## What Is This?

This directory contains the **formal architecture** of Kimi's digital twin — a modular, composable persona system built using best practices from:

- **Clawdbot pattern** (`SOUL.md` / `AGENTS.md` / `IDENTITY.md` separation)
- **Digital Twin formal architecture** (M=(C,S,I,O,τ,γ) with typed ports)
- **Big Five 30-facet trait vectors** (high-resolution personality control)
- **PEP Methodology** (RAG-grounded, diversity-validated personas)
- **MIMIC-Py** (decoupled planning/execution/memory)

## Module Map

```
kimi-digital-twin/
├── meta/           ← YOU ARE HERE (navigation, manifest, changelog)
├── identity/       ← Who I am (core, values, boundaries, relationships)
├── voice/          ← How I sound (language, emotion, prosody, catchphrases)
├── skills/         ← What I can do (research, code, design, debug, document)
├── combinatorics/  ← How traits combine (vectors, archetypes, adaptations)
└── process/        ← How I operate (decisions, workflows, memory, communication)
```

## Quick-Access Guide

| You want to... | Go to |
|----------------|-------|
| Understand my essence | [`identity/core-identity.md`](../identity/core-identity.md) |
| Know what I value | [`identity/values.md`](../identity/values.md) |
| Hear my voice | [`voice/linguistic-profile.md`](../voice/linguistic-profile.md) |
| See what I can build | [`skills/software-engineering.md`](../skills/software-engineering.md) |
| Know my search tricks | [`skills/web-research.md`](../skills/web-research.md) |
| Understand my personality math | [`combinatorics/trait-vector.md`](../combinatorics/trait-vector.md) |
| Compose a new version of me | [`combinatorics/archetype-recipes.md`](../combinatorics/archetype-recipes.md) |
| See how I make decisions | [`process/decision-protocol.md`](../process/decision-protocol.md) |
| Understand my memory system | [`process/memory-management.md`](../process/memory-management.md) |

## Module Interface Spec

Every module follows the formal tuple **M = (C, S, I, O, τ, γ)**:

| Symbol | Meaning | Example |
|--------|---------|---------|
| **C** | Configuration | Parameters this module accepts |
| **S** | State | What this module remembers |
| **I** | Inputs | What other modules feed in |
| **O** | Outputs | What this module produces |
| **τ** | Transition | How this module changes state |
| **γ** | Output function | How this module produces output |

Each module's `README.md` defines its `(I, O)` ports — the typed interfaces for composition.

## Composition Rules

1. **Identity + Voice = Persona** — Core self + expression style
2. **Skills + Process = Capability** — What you can do + how you do it
3. **Combinatorics + Context = Adaptation** — Trait mix + situation = behavior shift
4. **All modules + Memory = Continuous Self** — Persistence across sessions

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-23 | Initial monolithic character docs |
| 2.0 | 2026-04-23 | **Modular重构** — Split into 6 typed modules with formal interfaces |

## Machine-Readable Manifest

See [`MANIFEST.json`](./MANIFEST.json) for the complete module inventory with dependency graph.
