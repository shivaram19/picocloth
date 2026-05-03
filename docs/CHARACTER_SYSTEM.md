# Character System

> **DEPRECATED — SUPERCEDED BY MODULAR SYSTEM**
>
> This monolithic character document has been replaced by the modular digital twin architecture.
>
> **→ Navigate to `shared/doctrine/characters/kimi-digital-twin/meta/README.md` for the zero-latency hub.**

---

## Where Things Moved

| Old Content | New Location |
|-------------|-------------|
| 6 archetypes (Explorer, Craftsman, etc.) | [`combinatorics/archetype-recipes.md`](../shared/doctrine/characters/kimi-digital-twin/combinatorics/archetype-recipes.md) |
| Phase 1/2/3 migration | [`meta/CHANGELOG.md`](../shared/doctrine/characters/kimi-digital-twin/meta/CHANGELOG.md) |
| Archetype behavioral traits | [`combinatorics/trait-vector.md`](../shared/doctrine/characters/kimi-digital-twin/combinatorics/trait-vector.md) |
| Voice profiles | [`voice/`](../shared/doctrine/characters/kimi-digital-twin/voice/) |
| Relationship graphs | [`identity/relationship-model.md`](../shared/doctrine/characters/kimi-digital-twin/identity/relationship-model.md) |

## Why The Change?

The old system had all characters in one file. The new system:
- **Separates** identity/voice/skills/process/combinatorics/meta into 6 typed modules
- **Formalizes** interfaces using M=(C,S,I,O,τ,γ) tuple notation
- **Enables** composition — mix archetypes like ingredients
- **Provides** machine-readable frontmatter for automated persona assembly
- **Supports** Big Five 30-facet trait vectors for high-resolution personality control

Built using research from: Clawdbot pattern, Digital Twin formal architecture (Bolender et al. 2021), Big Five facet-level prompting (CECIIS 2025), PEP Methodology (Amin et al. 2026), MIMIC-Py (FSE Companion '26).

---

*This file preserved for historical reference. All active development is in the modular system.*
