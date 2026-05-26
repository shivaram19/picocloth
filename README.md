# 🎩 PicoCloth Consultant Twin Fleet

A 5-node AI consultant swarm — each node is a digital twin of a world-class AI consultant, sharing memory via a 4-layer shared state architecture. Built on [PicoCloth](https://github.com/shivaramgoud/picocloth) framework.

## The Fleet

| Node | Port | Role | System Prompt |
|------|------|------|---------------|
| **consultant-academic** | 18797 | Research & Knowledge synthesis | PhD-level researcher who cross-validates everything |
| **consultant-growth** | 18801 | Growth & Strategy | Scaled seed→Series C; asks "vanity or value?" |
| **consultant-solutions** | 18802 | AI Solutions Engineering | Designs production AI systems that scale 10x |
| **consultant-trainer** | 18803 | Training & Education | Makes you curious about the ocean, not just fishing |
| **curious-kimi** | 18804 | Question Engine | The conscience of the fleet — never settles, always asks why |

## Quick Start

```bash
# 1. Clone & enter
$EDITOR$ git clone <repo-url> picocloth-work && cd picocloth-work

# 2. Set up secrets (one-time)
$EDITOR$ ./scripts/setup-keyvault-for-picocloth.sh

# 3. Launch the fleet
$EDITOR$ ./scripts/launch-consultants.sh --keyvault

# 4. Check status
$EDITOR$ ./scripts/fleet-status.sh

# 5. Stop
$EDITOR$ ./scripts/stop-fleet.sh
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CONSULTANT TWINS                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Academic │ │ Growth   │ │ Solutions│ │ Trainer  │       │
│  │  :18797  │ │  :18801  │ │  :18802  │ │  :18803  │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
│       └─────────────┴────────────┴────────────┘             │
│                        │                                    │
│              ┌─────────┴─────────┐                         │
│              │   Curious Kimi    │  ← Question Engine      │
│              │     :18804        │    (Fleet Conscience)   │
│              └─────────┬─────────┘                         │
└────────────────────────┼────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌─────▼────┐   ┌────▼────┐
    │ Shared  │    │  Shared  │   │  Fleet  │
    │ Memory  │    │  Project │   │  State  │
    │ (Facts) │    │ (Docs)   │   │ (Health)│
    └─────────┘    └──────────┘   └─────────┘
         │               │               │
    ┌────▼───────────────▼───────────────▼────┐
    │         Azure Key Vault (shivaram-ai-kv) │
    │         ─── OpenAI API key ───           │
    └──────────────────────────────────────────┘
```

## Shared State Layers

| Layer | Path | Purpose |
|-------|------|---------|
| **L1 Shared Memory** | `shared/memory/` | Cross-node facts, research, competitive intel |
| **L2 Shared Project** | `shared/project/` | Client deliverables, documents, generated images |
| **L3 Shared Doctrine** | `shared/doctrine/` | Skills, characters, protocols — the "source code" of consultants |
| **L4 Fleet State** | `shared/state/` | Health, routing, session history |

## Tools Available to Every Consultant

- **Real-time web search** — DuckDuckGo + Serper for competitive intelligence
- **Image generation** — DALL-E 3 for diagrams, frameworks, concept visuals
- **MCP fleet server** — Cross-node memory sharing and broadcast

## Directory Structure

```
picocloth-work/
├── nodes/                    # Per-node configs + workspaces
│   ├── consultant-academic/
│   ├── consultant-growth/
│   ├── consultant-solutions/
│   ├── consultant-trainer/
│   └── curious-kimi/
├── shared/
│   ├── memory/              # L1: Facts, research, intel
│   ├── project/             # L2: Client work, images, docs
│   ├── doctrine/            # L3: Skills, characters, protocols
│   │   ├── skills/
│   │   └── characters/
│   └── state/               # L4: Fleet health, routing
├── scripts/
│   ├── launch-consultants.sh
│   ├── stop-fleet.sh
│   ├── fleet-status.sh
│   └── setup-keyvault-for-picocloth.sh
└── hooks/
    └── digital_twin_guardian.py   # Memory extraction hook
```

## Security

- **No API keys in code** — OpenAI key lives in Azure Key Vault (`shivaram-ai-kv`)
- **Managed Identity** — VMs fetch secrets at runtime via IMDS token
- **RBAC** — VMs have `Key Vault Secrets User`, humans have `Secrets Officer`
- **Local fallback** — Dev machines use `az login` + Azure CLI

## Cost Optimization

The fleet is designed to run on Azure VMs with:
- **Sleep/wake scripts** — Deallocate VMs when not in use
- **Model routing** — gpt-4o-mini for simple tasks, gpt-4o for complex
- **Shared state** — Prevents redundant API calls across nodes

## Roadmap

- [ ] Phase 1: 5 consultant nodes ✅
- [ ] Phase 2: Auto-scaling based on query load
- [ ] Phase 3: Client portal for consulting sessions
- [ ] Phase 4: Fine-tuned models per consultant specialty

---

Built with 🧠 by [Shivaram Goud](https://github.com/shivaramgoud) | Part of the PicoCloth ecosystem
