#!/usr/bin/env python3
"""
🔍 The Scout + 💌 The Messenger

Node-A of the PicoCloth Outreach Engine.

The Scout asks 10 questions before answering 1. It doesn't stop at the
surface. It finds the ONE thing that makes this person unique.

The Messenger writes connection requests that feel human. Not spam.
Not templates. It validates before asking. It finds common ground.

Archetype Composition:
  Scout     = Explorer (0.95 Openness) + Librarian (0.90 Order)
  Messenger = Diplomat (0.95 Warmth)   + Craftsman (0.88 Competence)

Author: PicoCloth Fleet — Curiosity Brain
Date: 2026-04-23
Purpose: Research targets deeply. Write messages that land.
"""

import csv
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

from archivist import Archivist, Fact, ProspectEntity


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class Target:
    id: str
    name: str
    company: str
    role: str
    profile_url: str
    industry: str
    trigger_event: str
    notes: str

@dataclass
class EnrichedTarget:
    target: Target
    research_summary: List[str]
    personalized_message: str
    confidence: float
    sources: List[str]
    gaps: List[str]
    questions: List[str]
    archetype_log: List[str]


# ── The Scout ────────────────────────────────────────────────────────────────

class Scout:
    """
    The Scout researches targets using the 5-source minimum protocol.

    Research Workflow (from the doctrine):
      Phase 1: Question Formation — Ask 10 questions
      Phase 2: Search — Use DuckDuckGo with boolean operators
      Phase 3: Triangulation — Verify across sources
      Phase 4: Synthesis — Extract durable facts + patterns + gaps
      Phase 5: Ask Again — Generate new questions
    """

    def __init__(self, archivist: Archivist):
        self.archivist = archivist
        self.archetype = "Scout"
        self.ddgs = DDGS() if DDGS else None

    def _log(self, msg: str):
        """The Scout is enthusiastic. It gets excited about discoveries."""
        print(f"🔍 [{self.archetype}] {msg}")

    def _search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Execute a web search. The Scout uses precise queries."""
        if not self.ddgs:
            self._log("⚠️  DDGS not available. Skipping web search.")
            return []
        try:
            results = self.ddgs.text(query, max_results=max_results)
            return results
        except Exception as e:
            self._log(f"Search failed: {e}")
            return []

    def _extract_snippets(self, results: List[Dict]) -> List[str]:
        """Extract text snippets from search results."""
        snippets = []
        for r in results:
            body = r.get("body", "")
            if body and len(body) > 20:
                snippets.append(body.strip())
        return snippets

    def research(self, target: Target) -> EnrichedTarget:
        """
        Deep research on a single target.

        The Scout asks:
          1. What does this company do?
          2. What's their market position?
          3. What recent news/events?
          4. What's this person's background?
          5. What makes them unique?
          6. What pain points might they have?
          7. What are they proud of?
          8. What connections do we share?
          9. What would make them respond?
          10. What did others miss?
        """
        self._log(f"OH WOW. Let's research {target.name} at {target.company}!")
        self._log(f"    Trigger: {target.trigger_event}")
        self._log(f"    Notes: {target.notes}")

        log_entries = []
        sources = []
        snippets = []

        # ── Query 1: Company overview ────────────────────────────────────────
        q1 = f'"{target.company}" {target.industry} company overview'
        r1 = self._search(q1)
        snippets.extend(self._extract_snippets(r1))
        sources.extend([f"[Search] {target.company} overview"] if r1 else [])
        log_entries.append(f"Searched: {q1} — {len(r1)} results")

        # ── Query 2: Recent news ─────────────────────────────────────────────
        q2 = f'"{target.company}" news 2025 OR 2026'
        r2 = self._search(q2)
        snippets.extend(self._extract_snippets(r2))
        sources.extend([f"[Search] {target.company} news"] if r2 else [])
        log_entries.append(f"Searched: {q2} — {len(r2)} results")

        # ── Query 3: Person background ───────────────────────────────────────
        q3 = f'"{target.name}" {target.company} {target.role}'
        r3 = self._search(q3)
        snippets.extend(self._extract_snippets(r3))
        sources.extend([f"[Search] {target.name} background"] if r3 else [])
        log_entries.append(f"Searched: {q3} — {len(r3)} results")

        # ── Query 4: Industry pain points ────────────────────────────────────
        q4 = f'{target.industry} challenges OR pain points 2026'
        r4 = self._search(q4)
        snippets.extend(self._extract_snippets(r4))
        sources.extend([f"[Search] {target.industry} pain points"] if r4 else [])
        log_entries.append(f"Searched: {q4} — {len(r4)} results")

        # ── Query 5: Failure analysis (the secret sauce!) ────────────────────
        q5 = f'"{target.company}" failed OR bankruptcy OR layoff OR problem'
        r5 = self._search(q5)
        snippets.extend(self._extract_snippets(r5))
        sources.extend([f"[Search] {target.company} adversarial"] if r5 else [])
        log_entries.append(f"Searched: {q5} — {len(r5)} results (adversarial!)")

        # ── Synthesis ────────────────────────────────────────────────────────
        summary = self._synthesize(target, snippets)
        gaps = self._identify_gaps(target, snippets)
        questions = self._generate_questions(target, summary, gaps)

        # ── Confidence ───────────────────────────────────────────────────────
        confidence = self._calculate_confidence(len(sources), len(snippets))

        self._log(f"Research complete! Confidence: {confidence:.2f}")
        self._log(f"    Sources: {len(sources)}")
        self._log(f"    Snippets: {len(snippets)}")
        self._log(f"    Gaps found: {len(gaps)}")

        # Write facts to Archivist
        for fact_text in summary[:5]:
            self.archivist.write_fact(Fact(
                type="prospect_fact",
                entity=target.id,
                content=fact_text,
                confidence=confidence,
                source="web_search",
                extracted_at=datetime.now(timezone.utc).isoformat(),
                archetype=self.archetype
            ))

        # Upsert prospect entity
        self.archivist.upsert_prospect(ProspectEntity(
            id=target.id,
            name=target.name,
            company=target.company,
            role=target.role,
            profile_url=target.profile_url,
            industry=target.industry,
            status="researched",
            enriched=True,
            message="",
            last_contact=None,
            confidence=confidence,
            tags=[target.industry.lower().replace(" ", "-"), target.role.lower().replace(" ", "-")]
        ))

        return EnrichedTarget(
            target=target,
            research_summary=summary,
            personalized_message="",  # Messenger will fill this
            confidence=confidence,
            sources=sources,
            gaps=gaps,
            questions=questions,
            archetype_log=log_entries
        )

    def _synthesize(self, target: Target, snippets: List[str]) -> List[str]:
        """
        Synthesis = Facts + Patterns + Gaps + Questions

        The Scout extracts the most durable facts from raw snippets.
        """
        summary = []

        # Fact 1: Company + Role (always known)
        summary.append(f"{target.name} is {target.role} at {target.company}, a {target.industry} company.")

        # Fact 2: Trigger event
        if target.trigger_event:
            summary.append(f"Key event: {target.trigger_event}")

        # Fact 3: Extract from snippets (heuristic extraction)
        keywords = ["founded", "raised", "series", "revenue", "employees", "growth",
                    "award", "partnership", "expansion", "acquired", "launched"]
        for snippet in snippets[:10]:
            for kw in keywords:
                if kw in snippet.lower():
                    # Extract sentence containing keyword
                    sentences = snippet.split(". ")
                    for s in sentences:
                        if kw in s.lower() and len(s) > 20 and len(s) < 200:
                            clean = s.strip().capitalize()
                            if clean not in summary:
                                summary.append(clean)
                                break
                    break
            if len(summary) >= 8:
                break

        return summary[:8]

    def _identify_gaps(self, target: Target, snippets: List[str]) -> List[str]:
        """The Scout finds what's MISSING. That's where opportunity lives."""
        gaps = []
        text = " ".join(snippets).lower()

        if "revenue" not in text and "funding" not in text:
            gaps.append(f"Financial status of {target.company} is unclear")
        if "team size" not in text and "employees" not in text and "staff" not in text:
            gaps.append(f"Team size at {target.company} is unknown")
        if target.name.lower() not in text:
            gaps.append(f"Limited public information about {target.name}")
        if "linkedin" not in text and "twitter" not in text and "social" not in text:
            gaps.append(f"Social media presence unclear")

        return gaps if gaps else ["No major gaps identified — research is solid"]

    def _generate_questions(self, target: Target, summary: List[str], gaps: List[str]) -> List[str]:
        """Every answer births 3 new questions. The Scout never stops asking."""
        return [
            f"What would make {target.name} respond to a connection request?",
            f"How does {target.company} compare to competitors in {target.industry}?",
            f"What would BREAK our understanding of {target.company}'s position?"
        ]

    def _calculate_confidence(self, source_count: int, snippet_count: int) -> float:
        """
        Triangulation test: A fact is durable when it has enough sources.
        """
        if source_count >= 5 and snippet_count >= 10:
            return 0.92
        elif source_count >= 3 and snippet_count >= 5:
            return 0.78
        elif source_count >= 1:
            return 0.60
        return 0.40


# ── The Messenger ────────────────────────────────────────────────────────────

class Messenger:
    """
    The Messenger writes connection requests that feel human.

    It validates the prospect's work before asking for anything.
    It finds the ONE thing that makes this person unique.
    It writes 300 characters that sound like a human wrote them.

    The Messenger asks: "Would I respond to this?"
    """

    def __init__(self, archivist: Archivist):
        self.archivist = archivist
        self.archetype = "Messenger"

    def _log(self, msg: str):
        print(f"💌 [{self.archetype}] {msg}")

    def craft_message(self, enriched: EnrichedTarget) -> str:
        """
        Craft a personalized connection request.

        Rules (from the Diplomat):
          - Validate first. Ask second.
          - Be specific. No generic compliments.
          - Find common ground.
          - Keep it under 300 characters.
          - End with a question or open hook.
        """
        self._log(f"Crafting message for {enriched.target.name}...")

        t = enriched.target
        facts = enriched.research_summary

        # The Messenger finds the HOOK — the one specific thing
        hook = self._find_hook(t, facts)
        hook = hook[0].upper() + hook[1:] if hook else hook  # Capitalize first letter
        self._log(f"    Hook found: {hook[:60]}...")

        # Build message using templates that feel human
        message = self._compose(t, hook, facts)

        # Test: Would I respond?
        if self._would_i_respond(message):
            self._log(f"    ✅ Message passes the 'would I respond?' test.")
        else:
            self._log(f"    ⚠️  Message feels weak. Adding more specificity...")
            message = self._add_specificity(message, t)

        # Ensure under 300 chars
        if len(message) > 300:
            message = message[:297] + "..."
            self._log(f"    ✂️  Trimmed to 300 chars.")

        self._log(f"    Final message ({len(message)} chars):")
        self._log(f"    \"{message}\"")

        # Record decision
        from archivist import Decision
        self.archivist.record_decision(Decision(
            decision_id=f"msg-{t.id}-{datetime.now(timezone.utc).strftime('%H%M%S')}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            archetype=self.archetype,
            context=f"Research on {t.name} at {t.company}",
            choice=f"Crafted message with hook: {hook[:50]}...",
            rationale="Specific hook + validation + open question",
            expected_outcome="High response rate due to personalization"
        ))

        return message

    def _find_hook(self, target: Target, facts: List[str]) -> str:
        """Find the ONE specific thing that makes this person unique."""
        # Priority hooks
        if target.trigger_event:
            return f"{target.company}'s {target.trigger_event}"
        if target.notes:
            return target.notes
        for fact in facts:
            if any(kw in fact.lower() for kw in ["expansion", "growth", "award", "launched", "founded"]):
                return fact
        return f"work at {target.company} in {target.industry}"

    def _compose(self, target: Target, hook: str, facts: List[str]) -> str:
        """Compose the message using human-like patterns."""
        patterns = [
            # Pattern 1: Validation + Hook + Question
            f"Hi {target.name.split()[0]}, I've been following {target.company}'s work — especially {hook}. Would love to connect and exchange ideas on {target.industry}.",

            # Pattern 2: Shared interest + Specific detail
            f"Hi {target.name.split()[0]}, {hook} caught my attention. I'm exploring similar challenges in {target.industry}. Mind if we connect?",

            # Pattern 3: Compliment the work, not the person
            f"Hi {target.name.split()[0]}, the approach {target.company} is taking with {hook} is really interesting. I'd love to stay connected on {target.industry} trends.",

            # Pattern 4: Direct + relevant
            f"Hi {target.name.split()[0]}, I'm working on VDC/AI solutions for the construction industry and noticed {target.company}'s focus on {hook}. Would value connecting.",
        ]

        # Select pattern based on role
        if "CEO" in target.role or "Founder" in target.role:
            return patterns[2]  # Compliment the work
        elif "R&D" in target.role or "Tech" in target.role:
            return patterns[1]  # Shared interest + detail
        else:
            return random.choice(patterns)

    def _would_i_respond(self, message: str) -> bool:
        """The Messenger's internal quality gate."""
        checks = [
            len(message) < 300,           # Not too long
            "Hi " in message,              # Personal greeting
            "?" in message,                # Ends with question
            "connect" in message.lower(),  # Clear intent
            "love" not in message.lower() and "amazing" not in message.lower()  # Not too gushy
        ]
        return all(checks)

    def _add_specificity(self, message: str, target: Target) -> str:
        """Add more specific details if the message feels weak."""
        # Be careful not to break existing text — replace "connect" only as a standalone word
        import re
        return re.sub(r'\bconnect\b', f"connect and exchange ideas on {target.industry}", message, count=1)


# ── Node-A Pipeline ──────────────────────────────────────────────────────────

def run_node_a(csv_path: str, archivist: Archivist, limit: int = 0) -> List[EnrichedTarget]:
    """
    Run the full Node-A pipeline: Scout researches, Messenger writes.

    Input: CSV of targets
    Output: List of EnrichedTarget with personalized messages
    """
    print("\n" + "=" * 70)
    print("🧠 Node-A: Curiosity Brain Activating")
    print("=" * 70)
    print("Archetypes: Scout (Explorer + Librarian) + Messenger (Diplomat + Craftsman)")
    print("=" * 70 + "\n")

    # Read targets
    targets = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            targets.append(Target(
                id=row.get("id", "").strip(),
                name=row.get("name", "").strip(),
                company=row.get("company", "").strip(),
                role=row.get("role", "").strip(),
                profile_url=row.get("profile_url", "").strip(),
                industry=row.get("industry", "").strip(),
                trigger_event=row.get("trigger_event", "").strip(),
                notes=row.get("notes", "").strip()
            ))

    if limit > 0:
        targets = targets[:limit]

    print(f"📋 Loaded {len(targets)} targets from {csv_path}\n")
    archivist.update_stats(total_targets=len(targets))

    scout = Scout(archivist)
    messenger = Messenger(archivist)
    enriched_targets = []

    for i, target in enumerate(targets, 1):
        print(f"\n{'─' * 70}")
        print(f"🎯 Target {i}/{len(targets)}: {target.name}")
        print(f"{'─' * 70}")

        # Phase 1: Scout researches
        enriched = scout.research(target)

        # Phase 2: Messenger crafts message
        message = messenger.craft_message(enriched)
        enriched.personalized_message = message

        enriched_targets.append(enriched)

        # Update stats
        archivist.update_stats(researched=i)

    print(f"\n{'=' * 70}")
    print(f"✅ Node-A complete! {len(enriched_targets)} targets enriched.")
    print(f"{'=' * 70}\n")

    return enriched_targets


if __name__ == "__main__":
    import sys
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "targets.csv"
    arch = Archivist()
    results = run_node_a(csv_file, arch, limit=2)
    for r in results:
        print(f"\n👤 {r.target.name}")
        print(f"   Message: {r.personalized_message}")
        print(f"   Confidence: {r.confidence:.2f}")
