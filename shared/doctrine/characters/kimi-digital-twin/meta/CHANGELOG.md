# Changelog — Kimi Digital Twin

## [2.0.0] — 2026-04-23 — The Modular Revolution

### Added
- **Formal module architecture** with 6 typed modules: `meta`, `identity`, `voice`, `skills`, `combinatorics`, `process`
- **Interface spec M=(C,S,I,O,τ,γ)** per module, enabling composability
- **Big Five 30-facet trait vector ψ** for high-resolution personality control
- **Archetype recipes** — composable trait combinations for different modes
- **Context adaptation rules** — how persona shifts per situation
- **Machine-readable MANIFEST.json** with dependency graph and access patterns
- **Typed ports** between modules — identity→voice, combinatorics→process, etc.

### Changed
- Split monolithic `CHARACTER_SYSTEM.md` into discrete modules
- Split monolithic `core-identity.md` + `traits.md` into 6 identity files
- Reorganized all persona content into strict module boundaries

### Research-Grounded
- Built using patterns from: Clawdbot (`SOUL.md`/`AGENTS.md`/`IDENTITY.md`), Digital Twin formal architecture (Bolender et al. 2021), Big Five facet-level prompting (CECIIS 2025), PEP Methodology (Amin et al. 2026), MIMIC-Py modular framework (FSE Companion '26)

## [1.0.0] — 2026-04-23 — Genesis

### Added
- Initial digital twin documentation
- `core-identity.md` — origin story, essence, co-authors
- `traits.md` — primary/secondary traits, quirks, values, fears, joys
- `CHARACTER_SYSTEM.md` — 6 archetypes (Explorer, Craftsman, Guardian, Librarian, Diplomat, Skeptic)
- Fleet node configs (ARIEL, BASTIAN) with system prompt characters
- Digital Twin Guardian pre-compaction hook
- MCP Fleet Server for inter-node communication
