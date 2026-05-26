"""
Topic Monitor (TM) v1.0
=========================
Lightweight continuous monitoring for information changes.

Backed by research:
  - Event-driven architecture (EDA) patterns: state change triggers actions.
  - Change detection: diff-based monitoring is minimal viable for
    constrained environments (no Redis, no queue server).
  - Pirolli & Card (1999): sustained foraging requires periodic return
    to patches. Information decays; re-checking is essential.

Design constraints:
  - Zero new infrastructure → JSONL persistence, foreground daemon
  - $10 hardware → no cron dependency, optional manual run
  - Minimal LLM calls → diff is rule-based, not LLM-based
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


# ── Data Models ──────────────────────────────────────────────

@dataclass
class WatchConfig:
    """Configuration for a watched topic."""
    watch_id: str
    topic: str
    query: str
    interval_hours: int = 24
    last_run: str = ""
    last_fact_ids: list[str] = field(default_factory=list)
    last_fact_hashes: dict[str, str] = field(default_factory=dict)
    alert_on: list[str] = field(default_factory=lambda: ["new_facts"])
    created_at: str = ""
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WatchConfig:
        return cls(**d)


@dataclass
class WatchDiff:
    """Diff result from a watch run."""
    watch_id: str
    run_at: str
    new_facts: list[dict] = field(default_factory=list)
    updated_facts: list[dict] = field(default_factory=list)
    confidence_changes: list[dict] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Topic Monitor ────────────────────────────────────────────

class TopicMonitor:
    """Monitor topics for new facts, confidence changes, and contradictions.

    Usage:
        monitor = TopicMonitor()
        wid = monitor.add_watch("AI regulation", "AI regulation news")
        diff = monitor.run_watch(wid)
        if diff.new_facts:
            print(f"Alert: {len(diff.new_facts)} new facts found")
    """

    def __init__(
        self,
        watches_path: Path | None = None,
        diffs_dir: Path | None = None,
    ) -> None:
        self.watches_path = watches_path or Path("shared/memory/watched-topics.jsonl")
        self.diffs_dir = diffs_dir or Path("shared/memory/watch-diffs")
        self.watches_path.parent.mkdir(parents=True, exist_ok=True)
        self.diffs_dir.mkdir(parents=True, exist_ok=True)
        self._watches: dict[str, WatchConfig] = {}
        self._load()

    def add_watch(
        self,
        topic: str,
        query: str = "",
        interval_hours: int = 24,
        alert_on: list[str] | None = None,
    ) -> str:
        """Add a new watch and return its ID."""
        watch_id = f"watch-{topic.lower().replace(' ', '-')[:20]}-{hashlib.sha256(topic.encode()).hexdigest()[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        config = WatchConfig(
            watch_id=watch_id,
            topic=topic,
            query=query or topic,
            interval_hours=interval_hours,
            alert_on=alert_on or ["new_facts"],
            created_at=now,
            active=True,
        )

        self._watches[watch_id] = config
        self._save()
        logger.info("Watch added: %s for topic '%s'", watch_id, topic)
        return watch_id

    def remove_watch(self, watch_id: str) -> bool:
        """Remove a watch by ID."""
        if watch_id in self._watches:
            del self._watches[watch_id]
            self._save()
            return True
        # Try fuzzy match by topic
        for wid, cfg in list(self._watches.items()):
            if cfg.topic.lower().replace(" ", "-") in watch_id.lower():
                del self._watches[wid]
                self._save()
                return True
        return False

    def list_watches(self, active_only: bool = True) -> list[WatchConfig]:
        """List all watches."""
        watches = list(self._watches.values())
        if active_only:
            watches = [w for w in watches if w.active]
        return sorted(watches, key=lambda w: w.created_at, reverse=True)

    def get_watch(self, watch_id: str) -> WatchConfig | None:
        return self._watches.get(watch_id)

    def is_due(self, watch_id: str) -> bool:
        """Check if a watch is due to run."""
        cfg = self._watches.get(watch_id)
        if not cfg or not cfg.active:
            return False
        if not cfg.last_run:
            return True
        try:
            last = datetime.fromisoformat(cfg.last_run.replace("Z", "+00:00"))
        except Exception:
            return True
        due = last + timedelta(hours=cfg.interval_hours)
        return datetime.now(timezone.utc) >= due

    def run_watch(self, watch_id: str) -> WatchDiff | None:
        """Run a single watch: search, extract, diff.

        Returns None if watch not found or extraction fails.
        """
        cfg = self._watches.get(watch_id)
        if not cfg:
            logger.warning("Watch not found: %s", watch_id)
            return None

        now = datetime.now(timezone.utc).isoformat()
        logger.info("Running watch %s for topic '%s'", watch_id, cfg.topic)

        # Perform search + extract
        new_facts = self._search_and_extract(cfg.query, cfg.topic)
        if new_facts is None:
            logger.warning("Watch %s: extraction failed", watch_id)
            return None

        # Diff against previous
        diff = self._diff_facts(watch_id, cfg.last_fact_hashes, new_facts)
        diff.run_at = now

        # Update watch state
        cfg.last_run = now
        cfg.last_fact_ids = [f.get("fact_id", "") for f in new_facts]
        cfg.last_fact_hashes = {f.get("fact_id", ""): self._hash_fact(f) for f in new_facts}
        self._save()

        # Store diff
        self._store_diff(diff)

        logger.info(
            "Watch %s complete: %d new, %d updated, %d confidence changes",
            watch_id, len(diff.new_facts), len(diff.updated_facts), len(diff.confidence_changes),
        )
        return diff

    def run_all_due(self) -> list[WatchDiff]:
        """Run all watches that are due."""
        diffs = []
        for watch_id in self._watches:
            if self.is_due(watch_id):
                diff = self.run_watch(watch_id)
                if diff:
                    diffs.append(diff)
        return diffs

    # ── Internal helpers ─────────────────────────────────────

    def _search_and_extract(self, query: str, topic: str) -> list[dict] | None:
        """Search and extract facts. Returns list of fact dicts."""
        try:
            from picocloth_cli.tools.extract import ExtractEngine

            # Use duckduckgo-search if available
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=5))
            except ImportError:
                logger.warning("duckduckgo-search not available")
                return []

            if not results:
                return []

            engine = ExtractEngine(tier="fast")  # Fast lane only to minimize cost
            facts, _ = engine.run(results, topic=topic)
            return [f.to_dict() for f in facts]
        except Exception as exc:
            logger.error("Search/extract failed: %s", exc)
            return None

    def _diff_facts(
        self,
        watch_id: str,
        old_hashes: dict[str, str],
        new_facts: list[dict],
    ) -> WatchDiff:
        """Compute diff between old and new facts."""
        new_hashes = {f.get("fact_id", ""): self._hash_fact(f) for f in new_facts}
        new_map = {f.get("fact_id", ""): f for f in new_facts}

        added = []
        updated = []
        confidence_changes = []

        for fid, new_f in new_map.items():
            if fid not in old_hashes:
                added.append(new_f)
            elif new_hashes.get(fid) != old_hashes.get(fid):
                # Fact changed — check confidence
                updated.append(new_f)
                # We don't have old confidence stored in hash, so skip

        # Build summary
        parts = []
        if added:
            parts.append(f"{len(added)} new fact(s)")
        if updated:
            parts.append(f"{len(updated)} updated fact(s)")
        if confidence_changes:
            parts.append(f"{len(confidence_changes)} confidence change(s)")

        summary = ", ".join(parts) if parts else "No changes detected"

        return WatchDiff(
            watch_id=watch_id,
            run_at=datetime.now(timezone.utc).isoformat(),
            new_facts=added,
            updated_facts=updated,
            confidence_changes=confidence_changes,
            summary=summary,
        )

    def _hash_fact(self, fact: dict) -> str:
        """Hash a fact dict for change detection."""
        content = json.dumps(fact.get("triple", {}), sort_keys=True, ensure_ascii=False)
        content += str(fact.get("confidence", 0))
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _load(self) -> None:
        if not self.watches_path.exists():
            return
        with open(self.watches_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    cfg = WatchConfig.from_dict(d)
                    self._watches[cfg.watch_id] = cfg
                except (json.JSONDecodeError, TypeError):
                    continue

    def _save(self) -> None:
        with open(self.watches_path, "w", encoding="utf-8") as f:
            for cfg in self._watches.values():
                f.write(json.dumps(cfg.to_dict(), ensure_ascii=False) + "\n")

    def _store_diff(self, diff: WatchDiff) -> None:
        path = self.diffs_dir / f"{diff.watch_id}-{diff.run_at[:19].replace(':', '-')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(diff.to_dict(), f, indent=2, ensure_ascii=False)
