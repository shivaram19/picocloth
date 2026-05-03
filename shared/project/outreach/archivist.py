#!/usr/bin/env python3
"""
📚 The Archivist — Librarian + Skeptic

Mission: Remember everything. Organize it. Question it.

The Archivist is the BACKBONE of the Outreach Engine. Nothing happens
without being recorded. Every fact gets a timestamp, a confidence score,
a source citation, and a skeptic's eye.

Shared Memory Layout (PicoCloth 4-Layer Architecture):
  project/       → Durable facts, entities, decisions
  state/         → Operational truth (queue, sent log, stats)
  run/           → Ephemeral working memory per execution
  doctrine/      → Archetypes, skills, policies (read-only)

Author: PicoCloth Fleet
Date: 2026-04-23
Purpose: Durable memory for outreach operations
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
PROJECT_DIR = BASE.parent  # shared/project/
OUTREACH_DIR = BASE

FACTS_FILE = OUTREACH_DIR / "logs" / "outreach-facts.jsonl"
ENTITIES_FILE = PROJECT_DIR / "entities" / "prospects.json"
DECISIONS_FILE = PROJECT_DIR / "decisions" / "outreach-decisions.json"
SENT_LOG = OUTREACH_DIR / "state" / "sent.jsonl"
QUEUE_FILE = OUTREACH_DIR / "state" / "queue.json"
STATS_FILE = OUTREACH_DIR / "state" / "stats.json"

# Ensure directories exist
for d in [FACTS_FILE.parent, ENTITIES_FILE.parent, DECISIONS_FILE.parent,
          SENT_LOG.parent, QUEUE_FILE.parent]:
    d.mkdir(parents=True, exist_ok=True)


# ── Data Classes (Typed Interfaces) ──────────────────────────────────────────

@dataclass
class Fact:
    """A durable fact extracted from research or execution."""
    type: str           # "prospect_fact", "company_fact", "market_fact"
    entity: str         # Who/what is this about?
    content: str        # The fact itself
    confidence: float   # 0.0-1.0
    source: str         # "web_search", "profile_scrape", "inference"
    extracted_at: str
    archetype: str      # Which archetype discovered this?

@dataclass
class ProspectEntity:
    """A prospect in the entity registry."""
    id: str
    name: str
    company: str
    role: str
    profile_url: str
    industry: str
    status: str         # "discovered", "researched", "messaged", "sent", "connected", "failed"
    enriched: bool
    message: str
    last_contact: Optional[str]
    confidence: float
    tags: List[str]

@dataclass
class Decision:
    """A decision made by the fleet."""
    decision_id: str
    timestamp: str
    archetype: str      # Who made this decision?
    context: str        # What was the situation?
    choice: str         # What was decided?
    rationale: str      # Why?
    expected_outcome: str

@dataclass
class SentRecord:
    """A log entry for a sent connection request."""
    timestamp: str
    target_id: str
    name: str
    company: str
    action: str         # "connect_sent", "follow_up", "message_sent"
    status: str         # "success", "failed", "pending"
    screenshot: Optional[str]
    error: Optional[str]
    archetype: str      # The Courier who sent it


# ── The Archivist ────────────────────────────────────────────────────────────

class Archivist:
    """
    The Archivist maintains the shared memory of the Outreach Engine.

    Design Principles (from the Craftsman):
      - Modularity first: Each method handles one concern
      - Typed interfaces: dataclasses define the contract
      - Fail safely: append-only writes, never overwrite without backup
      - Observability: Every write is logged
    """

    def __init__(self):
        self.session_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        print(f"📚 [Archivist] Session {self.session_id} initialized.")
        print(f"    Facts:    {FACTS_FILE}")
        print(f"    Entities: {ENTITIES_FILE}")
        print(f"    Decisions: {DECISIONS_FILE}")
        print(f"    Sent Log: {SENT_LOG}")

    # ── Facts ────────────────────────────────────────────────────────────────

    def write_fact(self, fact: Fact) -> None:
        """Append a fact to the durable facts database."""
        with open(FACTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(fact), ensure_ascii=False) + "\n")
        print(f"📚 [Archivist] Fact recorded: [{fact.type}] {fact.entity} — confidence {fact.confidence:.2f}")

    def read_facts(self, entity: Optional[str] = None, fact_type: Optional[str] = None) -> List[Fact]:
        """Query facts. The Skeptic demands evidence."""
        facts = []
        if not FACTS_FILE.exists():
            return facts
        with open(FACTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if entity and d.get("entity") != entity:
                        continue
                    if fact_type and d.get("type") != fact_type:
                        continue
                    facts.append(Fact(**d))
                except json.JSONDecodeError:
                    continue  # The Skeptic ignores malformed data
        return facts

    def get_fact_confidence(self, entity: str) -> float:
        """Calculate aggregate confidence for an entity's facts."""
        facts = self.read_facts(entity=entity)
        if not facts:
            return 0.0
        return sum(f.confidence for f in facts) / len(facts)

    # ── Entities ─────────────────────────────────────────────────────────────

    def _load_entities(self) -> Dict[str, Any]:
        if ENTITIES_FILE.exists():
            with open(ENTITIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"prospects": [], "version": 1, "last_updated": None}

    def _save_entities(self, data: Dict[str, Any]) -> None:
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(ENTITIES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def upsert_prospect(self, prospect: ProspectEntity) -> None:
        """Add or update a prospect in the entity registry."""
        data = self._load_entities()
        prospects = data.get("prospects", [])

        # Skeptic check: flag if company changed
        existing = next((p for p in prospects if p["id"] == prospect.id), None)
        if existing and existing.get("company") != prospect.company:
            print(f"⚠️  [Archivist-Skeptic] Company change detected for {prospect.id}:")
            print(f"     Was: {existing.get('company')} → Now: {prospect.company}")

        # Update or append
        new_entry = asdict(prospect)
        if existing:
            prospects = [p for p in prospects if p["id"] != prospect.id]
        prospects.append(new_entry)

        data["prospects"] = prospects
        self._save_entities(data)
        print(f"📚 [Archivist] Prospect '{prospect.name}' upserted. Status: {prospect.status}")

    def get_prospect(self, prospect_id: str) -> Optional[ProspectEntity]:
        data = self._load_entities()
        for p in data.get("prospects", []):
            if p["id"] == prospect_id:
                return ProspectEntity(**p)
        return None

    def get_prospects_by_status(self, status: str) -> List[ProspectEntity]:
        data = self._load_entities()
        return [ProspectEntity(**p) for p in data.get("prospects", []) if p.get("status") == status]

    # ── Decisions ────────────────────────────────────────────────────────────

    def record_decision(self, decision: Decision) -> None:
        """Record a fleet decision for auditability."""
        decisions = []
        if DECISIONS_FILE.exists():
            with open(DECISIONS_FILE, "r", encoding="utf-8") as f:
                decisions = json.load(f)
        decisions.append(asdict(decision))
        with open(DECISIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(decisions, f, indent=2, ensure_ascii=False)
        print(f"📚 [Archivist] Decision recorded by {decision.archetype}: {decision.choice}")

    # ── Sent Log ─────────────────────────────────────────────────────────────

    def log_sent(self, record: SentRecord) -> None:
        """Append a sent record. Append-only = audit trail."""
        with open(SENT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        emoji = "✅" if record.status == "success" else "❌"
        print(f"{emoji} [Archivist] Sent log: {record.name} ({record.company}) — {record.status}")

    def get_sent_count_today(self) -> int:
        """Count successful sends today. The Guardian uses this for rate limiting."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        count = 0
        if not SENT_LOG.exists():
            return 0
        with open(SENT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    ts = d.get("timestamp", "")
                    if ts.startswith(today) and d.get("status") == "success":
                        count += 1
                except json.JSONDecodeError:
                    continue
        return count

    # ── Queue ────────────────────────────────────────────────────────────────

    def load_queue(self) -> List[Dict[str, Any]]:
        if QUEUE_FILE.exists():
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_queue(self, queue: List[Dict[str, Any]]) -> None:
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)

    # ── Stats ────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        if STATS_FILE.exists():
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "total_targets": 0,
            "researched": 0,
            "messaged": 0,
            "sent": 0,
            "connected": 0,
            "failed": 0,
            "last_run": None
        }

    def update_stats(self, **kwargs) -> None:
        stats = self.get_stats()
        stats.update(kwargs)
        stats["last_run"] = datetime.now(timezone.utc).isoformat()
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

    def print_summary(self) -> None:
        """The Librarian loves a good summary."""
        stats = self.get_stats()
        print("\n" + "=" * 60)
        print("📊 [Archivist] Fleet Memory Summary")
        print("=" * 60)
        print(f"  Total targets:     {stats.get('total_targets', 0)}")
        print(f"  Researched:        {stats.get('researched', 0)}")
        print(f"  Messages drafted:  {stats.get('messaged', 0)}")
        print(f"  Requests sent:     {stats.get('sent', 0)}")
        print(f"  Connected:         {stats.get('connected', 0)}")
        print(f"  Failed:            {stats.get('failed', 0)}")
        print(f"  Sent today:        {self.get_sent_count_today()}")
        print("=" * 60)


if __name__ == "__main__":
    # Test the Archivist
    arch = Archivist()

    # Write a test fact
    arch.write_fact(Fact(
        type="company_fact",
        entity="Powerkh",
        content="Boutique VDC firm with 20+ staff, expanding to UK market",
        confidence=0.92,
        source="web_search",
        extracted_at=datetime.now(timezone.utc).isoformat(),
        archetype="Scout"
    ))

    # Upsert a prospect
    arch.upsert_prospect(ProspectEntity(
        id="kostya-rapina",
        name="Kostya Rapina",
        company="Powerkh",
        role="CEO",
        profile_url="https://linkedin.com/in/kostya-rapina",
        industry="VDC Construction",
        status="discovered",
        enriched=False,
        message="",
        last_contact=None,
        confidence=0.85,
        tags=["vdc", "ceo", "uk-expansion"]
    ))

    arch.print_summary()
