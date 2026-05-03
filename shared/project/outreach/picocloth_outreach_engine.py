#!/usr/bin/env python3
"""
🪶 PicoCloth Outreach Engine

The main entrypoint for the fleet-powered LinkedIn outreach product.

This is NOT a script. It's a PRODUCT.

Architecture:
  ┌─────────────────────────────────────────┐
  │     PICOLOTH OUTREACH ENGINE            │
  │                                         │
  │  ┌─────────┐    ┌─────────┐            │
  │  │ Node-A  │───►│ Node-B  │            │
  │  │ (Scout) │    │(Courier)│            │
  │  └────┬────┘    └────┬────┘            │
  │       │              │                  │
  │       └──────┬───────┘                  │
  │              ▼                          │
  │      ┌─────────────┐                    │
  │      │ Orchestrator │                   │
  │      └──────┬──────┘                   │
  │             ▼                           │
  │      ┌─────────────┐                    │
  │      │  Archivist  │                    │
  │      │ (Librarian) │                    │
  │      └─────────────┘                    │
  │                                         │
  │  Shared Memory:                         │
  │    ├── doctrine/  (read-only archetypes)│
  │    ├── project/   (facts, entities)     │
  │    ├── state/     (queue, sent log)     │
  │    └── run/       (ephemeral sessions)  │
  └─────────────────────────────────────────┘

Usage:
    # Full autonomous pipeline
    python3 picocloth_outreach_engine.py --targets targets.csv --limit 5

    # Dry run (research + craft, no sending)
    python3 picocloth_outreach_engine.py --targets targets.csv --dry-run

    # With existing session
    python3 picocloth_outreach_engine.py --targets targets.csv --session linkedin_state.json

    # Visible browser (for debugging)
    python3 picocloth_outreach_engine.py --targets targets.csv --visible

Author: PicoCloth Fleet
Date: 2026-04-23
Purpose: End-to-end LinkedIn outreach automation
"""

import sys
from pathlib import Path

# Add this directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import main

if __name__ == "__main__":
    sys.exit(main())
