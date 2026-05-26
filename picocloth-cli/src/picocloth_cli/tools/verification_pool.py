"""
Fleet Verification Pool (FVP) v1.0
==================================
Heterogeneous multi-agent fact verification with learned consensus.

Backed by research:
  - Six Sigma Agent (arXiv:2601.22290, Jan 2026): consensus-driven decomposed
    execution, atomic voting, dynamic scaling. ICE improved GPQA-diamond
    46.9% → 68.2% (45% relative gain).
  - A-HMAD (Springer s44443-025-00353-3, 2025): heterogeneous debate with
    learned consensus. 78% vs 68% majority vote in disagreements — 31%
    relative error reduction. GSM8K: 90.2% vs 84.0% standard debate.
  - MAV (Feb 2025): "increasing verifiers rather than model size" as scaling
    dimension. Aspect Verifiers with binary True/False approvals.
  - Adversary-Resistant Multi-Agent (arXiv:2505.24239, Apr 2025):
    credibility scoring per agent based on historical accuracy. Self-
    refinement before voting: track errors, measure variance, trigger
    reflection.

Pipeline:
  Fact → Heterogeneous Dispatch → Per-Agent Verification → Weighted Voting
  → Learned Consensus → VerificationResult
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)

# ── Consultant Role Mapping ──────────────────────────────────
# Each consultant node has a specialization. Facts are routed to the
# most appropriate verifier(s). Citation: A-HMAD "dynamic routing
# strategy that activates different subsets of agents depending on
# the query type and intermediate debate outcomes".

CONSULTANT_ROLES = {
    "consultant-academic": {
        "expertise": ["research", "scientific", "academic", "medical", "technical"],
        "weight": 1.2,  # Higher weight for domain-aligned facts
        "description": "Academic researcher — strong on peer-reviewed claims",
    },
    "consultant-solutions": {
        "expertise": ["business", "technical", "engineering", "product", "architecture"],
        "weight": 1.1,
        "description": "Solutions architect — strong on implementation claims",
    },
    "consultant-growth": {
        "expertise": ["market", "competitive", "growth", "financial", "trend"],
        "weight": 1.1,
        "description": "Growth strategist — strong on market and competitive claims",
    },
    "consultant-trainer": {
        "expertise": ["educational", "tutorial", "how-to", "best-practice", "guide"],
        "weight": 1.0,
        "description": "Technical trainer — strong on educational/tutorial claims",
    },
    "curious-kimi": {
        "expertise": ["general", "cross-domain", "overview", "summary"],
        "weight": 0.9,
        "description": "Generalist — broad coverage, lower domain depth",
    },
}

# Fact-type → consultant routing map
FACT_TYPE_ROUTING = {
    "statistic": ["consultant-academic", "consultant-growth", "curious-kimi"],
    "financial": ["consultant-growth", "consultant-academic", "curious-kimi"],
    "funding": ["consultant-growth", "consultant-solutions", "curious-kimi"],
    "quote": ["consultant-academic", "consultant-trainer", "curious-kimi"],
    "comparison": ["consultant-academic", "consultant-growth", "curious-kimi"],
    "growth": ["consultant-growth", "consultant-academic", "curious-kimi"],
    "decline": ["consultant-growth", "consultant-academic", "curious-kimi"],
    "founding": ["consultant-growth", "consultant-solutions", "curious-kimi"],
    "entity_list": ["curious-kimi", "consultant-trainer"],
    "claim": ["consultant-academic", "consultant-solutions", "consultant-growth", "curious-kimi"],
}


# ── Data Models ──────────────────────────────────────────────

@dataclass
class AgentVote:
    """A single consultant's vote on a fact."""
    agent_id: str
    verdict: str  # "SUPPORT", "REFUTE", "UNCERTAIN"
    confidence: float  # 0.0-1.0
    justification: str
    fact_type_alignment: float = 1.0  # How well agent expertise aligns
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class VerificationResult:
    """Final result of fleet verification on a fact."""
    fact_id: str
    verdict: str  # "VERIFIED", "DISPUTED", "REFUTED", "UNCERTAIN"
    confidence: float
    votes: list[AgentVote]
    consensus_method: str
    corroboration_count: int
    contradiction_count: int
    uncertainty_count: int
    credibility_weighted_score: float
    needs_deep_verification: bool
    verified_at: str = ""
    historical_accuracy_bonus: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["votes"] = [asdict(v) for v in self.votes]
        return d


# ── Credibility Tracker ──────────────────────────────────────
# Citation: Adversary-Resistant Multi-Agent (Apr 2025).
# Each agent tracks its own errors, measures variance, and we weight
# by historical accuracy. Credibility decays over time so recent
# performance matters more.

class CredibilityTracker:
    """Tracks per-agent verification accuracy for learned consensus."""

    DECAY_DAYS = 30  # Exponential decay half-life

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or Path("shared/memory/verification-credibility.json")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._scores: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.db_path.exists():
            with open(self.db_path, encoding="utf-8") as f:
                self._scores = json.load(f)

    def _save(self) -> None:
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self._scores, f, indent=2, ensure_ascii=False)

    def record(self, agent_id: str, fact_type: str, was_correct: bool) -> None:
        """Record whether an agent's vote was correct."""
        key = f"{agent_id}:{fact_type}"
        now = datetime.now(timezone.utc).isoformat()

        if key not in self._scores:
            self._scores[key] = {
                "agent_id": agent_id,
                "fact_type": fact_type,
                "total": 0,
                "correct": 0,
                "history": [],
                "last_updated": now,
            }

        entry = self._scores[key]
        entry["total"] += 1
        if was_correct:
            entry["correct"] += 1
        entry["history"].append({"correct": was_correct, "at": now})
        # Trim history to last 50
        entry["history"] = entry["history"][-50:]
        entry["last_updated"] = now
        self._save()

    def get_accuracy(self, agent_id: str, fact_type: str) -> float:
        """Get time-decayed accuracy for an agent on a fact type."""
        key = f"{agent_id}:{fact_type}"
        entry = self._scores.get(key, {})
        history = entry.get("history", [])
        if not history:
            return 0.5  # Neutral prior

        now = datetime.now(timezone.utc)
        weighted_correct = 0.0
        weighted_total = 0.0

        for h in history:
            try:
                h_time = datetime.fromisoformat(h["at"].replace("Z", "+00:00"))
            except Exception:
                continue
            days_ago = (now - h_time).total_seconds() / 86400
            decay = 0.5 ** (days_ago / self.DECAY_DAYS)
            weighted_total += decay
            if h["correct"]:
                weighted_correct += decay

        if weighted_total == 0:
            return 0.5
        return weighted_correct / weighted_total

    def get_agent_weight(self, agent_id: str, fact_type: str) -> float:
        """Combined weight: base role weight × historical accuracy."""
        base = CONSULTANT_ROLES.get(agent_id, {}).get("weight", 1.0)
        accuracy = self.get_accuracy(agent_id, fact_type)
        # Accuracy below 0.4 reduces weight; above 0.7 increases it
        accuracy_factor = 0.5 + accuracy  # Range: 0.5 (bad) → 1.5 (excellent)
        return round(base * accuracy_factor, 3)


# ── Verification Pool ────────────────────────────────────────

class FleetVerificationPool:
    """Orchestrates heterogeneous multi-agent verification.

    Usage:
        pool = FleetVerificationPool()
        result = pool.verify_fact(fact, strategy="weighted")
        # After ground truth known:
        pool.record_outcome(result, ground_truth=True)
    """

    def __init__(
        self,
        credibility_db: Path | None = None,
        min_votes: int = 3,
        consensus_threshold: float = 0.65,
    ) -> None:
        self.credibility = CredibilityTracker(db_path=credibility_db)
        self.min_votes = min_votes
        self.consensus_threshold = consensus_threshold
        self._verification_cache: dict[str, VerificationResult] = {}

    def verify_fact(
        self,
        fact: Any,  # ExtractedFact
        strategy: str = "weighted",
        available_nodes: list[str] | None = None,
    ) -> VerificationResult:
        """Verify a fact using the fleet verification pool.

        Strategies:
          weighted    — A-HMAD learned consensus with credibility weighting
          unanimous   — All agents must agree (strict, high precision)
          threshold   — Simple majority above consensus_threshold
        """
        fact_id = fact.fact_id
        fact_type = getattr(fact, "fact_type", "claim")

        # Cache hit
        if fact_id in self._verification_cache:
            return self._verification_cache[fact_id]

        # Determine which agents to dispatch
        agents = self._select_agents(fact_type, available_nodes)
        if len(agents) < self.min_votes:
            logger.warning(
                "Not enough agents for verification: %d < %d",
                len(agents), self.min_votes,
            )

        # Simulate votes (in production, these would be MCP calls)
        votes = self._dispatch_votes(fact, agents)

        # Apply learned consensus
        if strategy == "weighted":
            result = self._weighted_consensus(fact_id, fact_type, votes)
        elif strategy == "unanimous":
            result = self._unanimous_consensus(fact_id, votes)
        else:
            result = self._threshold_consensus(fact_id, votes)

        self._verification_cache[fact_id] = result
        return result

    def _select_agents(
        self,
        fact_type: str,
        available_nodes: list[str] | None,
    ) -> list[str]:
        """Select the most appropriate agents for a fact type."""
        candidates = FACT_TYPE_ROUTING.get(fact_type, FACT_TYPE_ROUTING["claim"])
        if available_nodes:
            candidates = [c for c in candidates if c in available_nodes]
        return candidates

    def _dispatch_votes(
        self,
        fact: Any,
        agents: list[str],
    ) -> list[AgentVote]:
        """Dispatch verification tasks and collect votes.

        In the current implementation, we simulate agent reasoning based on
        fact confidence and source quality. In production with live MCP
        fleet, this would call `await client.spawn_task()` for each agent.
        """
        votes: list[AgentVote] = []
        base_confidence = getattr(fact, "confidence", 0.5)
        sources = getattr(fact, "sources", [])

        # Deterministic seed from fact_id for reproducible simulation
        import random
        fid = getattr(fact, "fact_id", "unknown")
        seed = int(hashlib.sha256(str(fid).encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        for agent_id in agents:
            role = CONSULTANT_ROLES.get(agent_id, {})
            alignment = 1.0 if any(
                e in getattr(fact, "fact_type", "") for e in role.get("expertise", [])
            ) else 0.7

            # Simulate agent reasoning:
            # - Higher base confidence → more likely SUPPORT
            # - More corroboration → more likely SUPPORT
            # - More contradictions → more likely REFUTE
            corroborated = len(getattr(fact, "corroborated_by", []))
            contradicted = len(getattr(fact, "contradicts", []))

            # Base signal from fact quality
            support_prob = base_confidence * 0.8 + 0.1
            support_prob += min(0.1, corroborated * 0.03)
            support_prob -= min(0.2, contradicted * 0.05)
            support_prob *= alignment
            support_prob = max(0.1, min(0.95, support_prob))

            roll = rng.random()
            if roll < support_prob:
                verdict = "SUPPORT"
                confidence = round(support_prob + rng.uniform(-0.05, 0.05), 2)
                justification = f"Source quality is strong (tier {sources[0].tier if sources else 3}), claim is specific and verifiable."
            elif roll < support_prob + 0.15:
                verdict = "UNCERTAIN"
                confidence = round(0.5 + rng.uniform(-0.1, 0.1), 2)
                justification = "Insufficient evidence to fully support or refute this claim."
            else:
                verdict = "REFUTE"
                confidence = round(1 - support_prob + rng.uniform(-0.05, 0.05), 2)
                justification = "Claim appears unsupported or contradicted by known evidence."

            votes.append(AgentVote(
                agent_id=agent_id,
                verdict=verdict,
                confidence=round(max(0.0, min(1.0, confidence)), 2),
                justification=justification,
                fact_type_alignment=round(alignment, 2),
            ))

        return votes

    def _weighted_consensus(
        self,
        fact_id: str,
        fact_type: str,
        votes: list[AgentVote],
    ) -> VerificationResult:
        """A-HMAD learned consensus: weight by credibility × alignment."""
        support_score = 0.0
        refute_score = 0.0
        uncertain_score = 0.0
        total_weight = 0.0

        for vote in votes:
            weight = self.credibility.get_agent_weight(vote.agent_id, fact_type)
            weight *= vote.fact_type_alignment
            weight *= vote.confidence  # Agent's own confidence in its vote

            if vote.verdict == "SUPPORT":
                support_score += weight
            elif vote.verdict == "REFUTE":
                refute_score += weight
            else:
                uncertain_score += weight
            total_weight += weight

        if total_weight == 0:
            total_weight = 1.0

        support_ratio = support_score / total_weight
        refute_ratio = refute_score / total_weight
        uncertain_ratio = uncertain_score / total_weight

        # Determine final verdict
        if support_ratio > self.consensus_threshold and support_ratio > refute_ratio:
            verdict = "VERIFIED"
            confidence = round(support_ratio, 2)
        elif refute_ratio > self.consensus_threshold and refute_ratio > support_ratio:
            verdict = "REFUTED"
            confidence = round(refute_ratio, 2)
        elif uncertain_ratio > 0.5:
            verdict = "UNCERTAIN"
            confidence = round(uncertain_ratio, 2)
        else:
            verdict = "DISPUTED"
            confidence = round(max(support_ratio, refute_ratio), 2)

        # Deep verification needed if split decision
        needs_deep = (
            abs(support_ratio - refute_ratio) < 0.2
            and support_ratio > 0.3
            and refute_ratio > 0.3
        )

        # Historical accuracy bonus for agents that voted correctly
        # (will be updated after ground truth is known)
        hist_bonus = sum(
            self.credibility.get_accuracy(v.agent_id, fact_type)
            for v in votes
        ) / len(votes) if votes else 0.0

        return VerificationResult(
            fact_id=fact_id,
            verdict=verdict,
            confidence=confidence,
            votes=votes,
            consensus_method="weighted",
            corroboration_count=sum(1 for v in votes if v.verdict == "SUPPORT"),
            contradiction_count=sum(1 for v in votes if v.verdict == "REFUTE"),
            uncertainty_count=sum(1 for v in votes if v.verdict == "UNCERTAIN"),
            credibility_weighted_score=round(support_score, 3),
            needs_deep_verification=needs_deep,
            verified_at=datetime.now(timezone.utc).isoformat(),
            historical_accuracy_bonus=round(hist_bonus, 3),
        )

    def _unanimous_consensus(
        self,
        fact_id: str,
        votes: list[AgentVote],
    ) -> VerificationResult:
        """All agents must agree. Highest precision, lowest recall."""
        verdicts = [v.verdict for v in votes]
        all_support = all(v == "SUPPORT" for v in verdicts)
        all_refute = all(v == "REFUTE" for v in verdicts)

        if all_support:
            final = "VERIFIED"
            conf = round(sum(v.confidence for v in votes) / len(votes), 2)
        elif all_refute:
            final = "REFUTED"
            conf = round(sum(v.confidence for v in votes) / len(votes), 2)
        elif all(v == "UNCERTAIN" for v in verdicts):
            final = "UNCERTAIN"
            conf = 0.5
        else:
            final = "DISPUTED"
            conf = 0.5

        return VerificationResult(
            fact_id=fact_id,
            verdict=final,
            confidence=conf,
            votes=votes,
            consensus_method="unanimous",
            corroboration_count=sum(1 for v in votes if v.verdict == "SUPPORT"),
            contradiction_count=sum(1 for v in votes if v.verdict == "REFUTE"),
            uncertainty_count=sum(1 for v in votes if v.verdict == "UNCERTAIN"),
            credibility_weighted_score=0.0,
            needs_deep_verification=final == "DISPUTED",
            verified_at=datetime.now(timezone.utc).isoformat(),
        )

    def _threshold_consensus(
        self,
        fact_id: str,
        votes: list[AgentVote],
    ) -> VerificationResult:
        """Simple majority above threshold."""
        support = sum(1 for v in votes if v.verdict == "SUPPORT")
        refute = sum(1 for v in votes if v.verdict == "REFUTE")
        uncertain = sum(1 for v in votes if v.verdict == "UNCERTAIN")
        total = len(votes)

        if total == 0:
            return VerificationResult(
                fact_id=fact_id, verdict="UNCERTAIN", confidence=0.0,
                votes=votes, consensus_method="threshold",
                corroboration_count=0, contradiction_count=0,
                uncertainty_count=0, credibility_weighted_score=0.0,
                needs_deep_verification=True,
                verified_at=datetime.now(timezone.utc).isoformat(),
            )

        if support / total > self.consensus_threshold:
            final = "VERIFIED"
            conf = round(support / total, 2)
        elif refute / total > self.consensus_threshold:
            final = "REFUTED"
            conf = round(refute / total, 2)
        elif uncertain / total > 0.5:
            final = "UNCERTAIN"
            conf = round(uncertain / total, 2)
        else:
            final = "DISPUTED"
            conf = round(max(support, refute) / total, 2)

        return VerificationResult(
            fact_id=fact_id,
            verdict=final,
            confidence=conf,
            votes=votes,
            consensus_method="threshold",
            corroboration_count=support,
            contradiction_count=refute,
            uncertainty_count=uncertain,
            credibility_weighted_score=round(support / total, 3),
            needs_deep_verification=final == "DISPUTED",
            verified_at=datetime.now(timezone.utc).isoformat(),
        )

    def record_outcome(
        self,
        result: VerificationResult,
        fact_type: str,
        was_correct: bool,
    ) -> None:
        """After ground truth is known, update credibility scores."""
        for vote in result.votes:
            # A vote was "correct" if its verdict aligned with ground truth
            vote_correct = (
                (vote.verdict == "SUPPORT" and was_correct)
                or (vote.verdict == "REFUTE" and not was_correct)
                or (vote.verdict == "UNCERTAIN")  # Uncertain is neutral
            )
            self.credibility.record(vote.agent_id, fact_type, vote_correct)

    def verify_batch(
        self,
        facts: list[Any],
        strategy: str = "weighted",
    ) -> list[VerificationResult]:
        """Verify a batch of facts efficiently."""
        return [self.verify_fact(f, strategy=strategy) for f in facts]
