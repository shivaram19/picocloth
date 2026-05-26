"""
Citation Validator (CV) v1.0
============================
Structured citation quality enforcement for extracted facts.

Backed by research:
  - LiveResearchBench (Salesforce AI Research, 2026, arXiv:2510.14240):
    "Models struggle most with citation correctness and formatting."
    Failure modes across ALL 17 evaluated systems:
      • Mismatched in-text citations and references
      • Missing or incomplete URLs
      • Inconsistent citation formats
      • Uncited references appearing in bibliography
      • Broken or incomplete table formatting
      • Out-of-order reference numbering
    E3 errors (unsupported claims) dominate wide search.
    Open Deep Research: 91.9 unsupported claims per market analysis.

  - Deerflow+ Stabilization (Appendix D, LiveResearchBench):
    "Added inline-citation support + validation pass. Enforces one-to-one
    mapping between in-text citations and reference entries. Checks
    numbering continuity and duplicates."
    Result: "higher information retention, stronger evidence structuring."

  - DEFT Taxonomy (Zhang et al., Dec 2025):
    Low-authority citation = specific retrieval failure mode (33.10% of
    all failures). Strategic Content Fabrication = 18.95% of generation
    failures — claims without backing sources.

Pipeline:
  ExtractedFact → URL Health Check → Inline Citation Mapping → Format
  Consistency → Duplicate Detection → Unsupported Claim Flagging →
  CitationReport
"""

from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)

# ── Citation Error Types ─────────────────────────────────────
# Aligned with LiveResearchBench E1/E2/E3 taxonomy and DEFT.

ERROR_TYPES = {
    "E1_INVALID_URL": "URL returns 4xx/5xx or is malformed",
    "E2_INCOMPLETE_URL": "URL missing scheme, domain, or path",
    "E3_UNSUPPORTED_CLAIM": "Claim not verifiable from cited source",
    "E4_MISMATCHED_CITATION": "In-text citation does not match reference",
    "E5_DUPLICATE_REFERENCE": "Same source cited multiple times with different numbers",
    "E6_MISSING_CITATION": "Claim has no supporting source",
    "E7_INCONSISTENT_FORMAT": "Citation format inconsistent with house style",
    "E8_ORPHANED_REFERENCE": "Reference appears in bibliography but never cited",
}


# ── Data Models ──────────────────────────────────────────────

@dataclass
class CitationError:
    error_type: str
    severity: str  # "critical", "warning", "info"
    message: str
    fact_id: str = ""
    source_url: str = ""
    suggestion: str = ""


@dataclass
class ValidatedSource:
    """Enhanced source with validation metadata."""
    url: str
    domain: str = ""
    tier: int = 3
    title: str = ""
    retrieved_at: str = ""
    reference_number: int = 0
    accessed_at: str = ""
    status_code: int | None = None
    is_reachable: bool = True
    canonical_url: str = ""
    content_fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "domain": self.domain,
            "tier": self.tier,
            "title": self.title,
            "retrieved_at": self.retrieved_at,
            "reference_number": self.reference_number,
            "accessed_at": self.accessed_at,
            "status_code": self.status_code,
            "is_reachable": self.is_reachable,
            "canonical_url": self.canonical_url,
            "content_fingerprint": self.content_fingerprint,
        }


@dataclass
class CitationReport:
    """Validation report for a set of facts."""
    fact_id: str
    total_sources: int
    valid_sources: int
    invalid_sources: int
    errors: list[CitationError]
    reference_map: dict[int, str]  # number → canonical URL
    citation_health_score: float  # 0.0-1.0
    format_consistency_score: float
    unsupported_claims_flagged: bool
    validated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "total_sources": self.total_sources,
            "valid_sources": self.valid_sources,
            "invalid_sources": self.invalid_sources,
            "errors": [{"type": e.error_type, "severity": e.severity,
                        "message": e.message, "suggestion": e.suggestion} for e in self.errors],
            "reference_map": self.reference_map,
            "citation_health_score": self.citation_health_score,
            "format_consistency_score": self.format_consistency_score,
            "unsupported_claims_flagged": self.unsupported_claims_flagged,
            "validated_at": self.validated_at,
        }


# ── Validator Engine ─────────────────────────────────────────

class CitationValidator:
    """Validates citations for extracted facts.

    Usage:
        validator = CitationValidator()
        report = validator.validate_fact(fact)
        # Fix issues
        fixed_sources = validator.fix_citations(fact.sources)
    """

    def __init__(self, check_reachability: bool = False) -> None:
        """
        Args:
            check_reachability: If True, performs HTTP HEAD requests to
                verify URLs. Disabled by default to avoid latency.
        """
        self.check_reachability = check_reachability
        self._canonical_cache: dict[str, str] = {}
        self._reference_counter = 0

    def validate_fact(self, fact: Any) -> CitationReport:
        """Run full validation on a single fact."""
        errors: list[CitationError] = []
        sources = list(getattr(fact, "sources", []))
        claim = getattr(fact, "triple", None)
        claim_text = claim.claim if claim else getattr(fact, "raw_text", "")
        fact_id = getattr(fact, "fact_id", "unknown")

        # 1. E6: Missing citation check
        if not sources:
            errors.append(CitationError(
                error_type="E6_MISSING_CITATION",
                severity="critical",
                message="Claim has no supporting source. Every fact must be traceable.",
                fact_id=fact_id,
                suggestion="Add a primary source URL or mark as unverified hypothesis.",
            ))

        valid_sources = 0
        invalid_sources = 0
        reference_map: dict[int, str] = {}

        for source in sources:
            url = getattr(source, "url", "")
            domain = getattr(source, "domain", "")

            # 2. E2: Incomplete URL check
            if not url or not url.startswith(("http://", "https://")):
                errors.append(CitationError(
                    error_type="E2_INCOMPLETE_URL",
                    severity="critical",
                    message=f"URL is incomplete or missing scheme: '{url}'",
                    fact_id=fact_id,
                    source_url=url,
                    suggestion="Add https:// prefix and ensure full domain is present.",
                ))
                invalid_sources += 1
                continue

            # 3. E1: URL health check (if enabled)
            if self.check_reachability:
                is_reachable, status = self._check_url_health(url)
                if not is_reachable:
                    errors.append(CitationError(
                        error_type="E1_INVALID_URL",
                        severity="warning",
                        message=f"URL returned HTTP {status or 'error'}: {url}",
                        fact_id=fact_id,
                        source_url=url,
                        suggestion="Verify URL is correct and source is still available.",
                    ))
                    invalid_sources += 1
                    continue

            # 4. Canonicalization and deduplication
            canonical = self._canonicalize_url(url)
            if canonical in self._canonical_cache.values():
                errors.append(CitationError(
                    error_type="E5_DUPLICATE_REFERENCE",
                    severity="warning",
                    message=f"Duplicate citation detected: {url}",
                    fact_id=fact_id,
                    source_url=url,
                    suggestion="Merge duplicate sources or use a single reference number.",
                ))

            self._reference_counter += 1
            ref_num = self._reference_counter
            reference_map[ref_num] = canonical
            self._canonical_cache[url] = canonical
            valid_sources += 1

        # 5. E3: Unsupported claim heuristic
        # If claim is very specific (numbers, dates, quotes) but sources
        # are low-tier or few, flag as potentially unsupported.
        unsupported = self._flag_unsupported_claim(claim_text, sources, valid_sources)
        if unsupported:
            errors.append(CitationError(
                error_type="E3_UNSUPPORTED_CLAIM",
                severity="warning",
                message=f"Claim may not be fully supported by cited sources: '{claim_text[:80]}...'",
                fact_id=fact_id,
                suggestion="Verify claim text appears in source content, not just source domain.",
            ))

        # 6. E7: Format consistency check
        format_score = self._check_format_consistency(sources)

        # Compute health score
        if total := len(sources):
            health = valid_sources / total
        else:
            health = 0.0

        # Penalize for errors
        critical_count = sum(1 for e in errors if e.severity == "critical")
        warning_count = sum(1 for e in errors if e.severity == "warning")
        health = max(0.0, health - critical_count * 0.3 - warning_count * 0.1)

        return CitationReport(
            fact_id=fact_id,
            total_sources=len(sources),
            valid_sources=valid_sources,
            invalid_sources=invalid_sources,
            errors=errors,
            reference_map=reference_map,
            citation_health_score=round(health, 2),
            format_consistency_score=round(format_score, 2),
            unsupported_claims_flagged=unsupported,
            validated_at=datetime.now(timezone.utc).isoformat(),
        )

    def validate_batch(self, facts: list[Any]) -> list[CitationReport]:
        """Validate a batch of facts, assigning global reference numbers."""
        self._reference_counter = 0
        self._canonical_cache = {}
        return [self.validate_fact(f) for f in facts]

    def _canonicalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        try:
            parsed = urllib.parse.urlparse(url)
            # Remove www, trailing slash, fragment, common tracking params
            netloc = parsed.netloc.lower().lstrip("www.")
            path = parsed.path.rstrip("/")
            query = parsed.query
            # Strip common tracking parameters
            if query:
                params = urllib.parse.parse_qs(query)
                for key in list(params.keys()):
                    if key in ("utm_source", "utm_medium", "utm_campaign",
                               "fbclid", "gclid", "ref", "source"):
                        del params[key]
                query = urllib.parse.urlencode(params, doseq=True) if params else ""
            canonical = urllib.parse.urlunparse((
                parsed.scheme, netloc, path, "", query, ""
            ))
            return canonical
        except Exception:
            return url

    def _check_url_health(self, url: str) -> tuple[bool, int | None]:
        """Check if a URL is reachable. Returns (is_reachable, status_code)."""
        try:
            import urllib.request
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "PicoCloth-CitationValidator/1.0")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return True, resp.status
        except Exception:
            return False, None

    def _flag_unsupported_claim(
        self,
        claim_text: str,
        sources: list[Any],
        valid_sources: int,
    ) -> bool:
        """Heuristic: flag claims that may not be supported by sources.

        A claim is flagged if:
        - It contains specific numbers/dates/quotes
        - But has no sources or only low-tier sources
        - Or has very few valid sources (<2)
        """
        if not claim_text:
            return False

        # Specificity signals
        has_numbers = bool(re.search(r"\d+", claim_text))
        has_dates = bool(re.search(r"20\d{2}|Q[1-4]", claim_text))
        has_quotes = '"' in claim_text or "'" in claim_text
        is_specific = has_numbers or has_dates or has_quotes

        if not is_specific:
            return False

        # Source quality check
        if valid_sources == 0:
            return True

        if valid_sources == 1:
            tier = getattr(sources[0], "tier", 3)
            if tier >= 3:
                return True

        # Multi-source but all low-tier
        if valid_sources >= 1:
            avg_tier = sum(getattr(s, "tier", 3) for s in sources) / len(sources)
            if avg_tier >= 2.5 and valid_sources < 2:
                return True

        return False

    def _check_format_consistency(self, sources: list[Any]) -> float:
        """Check if all sources use consistent citation format.

        Returns a score 0.0-1.0 where 1.0 = perfectly consistent.
        """
        if not sources:
            return 0.0

        # Check for consistent field presence
        has_title = sum(1 for s in sources if getattr(s, "title", ""))
        has_domain = sum(1 for s in sources if getattr(s, "domain", ""))
        has_tier = sum(1 for s in sources if getattr(s, "tier", None) is not None)

        scores = []
        if sources:
            scores.append(has_title / len(sources))
            scores.append(has_domain / len(sources))
            scores.append(has_tier / len(sources))

        return round(sum(scores) / len(scores), 2) if scores else 0.0

    def fix_citations(self, sources: list[Any]) -> list[ValidatedSource]:
        """Auto-fix common citation issues.

        - Add https:// to URLs missing scheme
        - Extract domain if missing
        - Deduplicate
        """
        fixed: list[ValidatedSource] = []
        seen: set[str] = set()

        for src in sources:
            url = getattr(src, "url", "")
            if not url:
                continue

            # Fix missing scheme
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            canonical = self._canonicalize_url(url)
            if canonical in seen:
                continue
            seen.add(canonical)

            domain = getattr(src, "domain", "")
            if not domain:
                try:
                    domain = urllib.parse.urlparse(url).netloc.lower().lstrip("www.")
                except Exception:
                    domain = "unknown"

            fixed.append(ValidatedSource(
                url=url,
                domain=domain,
                tier=getattr(src, "tier", 3),
                title=getattr(src, "title", ""),
                retrieved_at=getattr(src, "retrieved_at", ""),
                canonical_url=canonical,
            ))

        return fixed

    def generate_bibliography(
        self,
        facts: list[Any],
        style: str = "inline-url",
    ) -> str:
        """Generate a formatted bibliography from facts.

        Styles:
          inline-url     → [1] Title. https://example.com
          apa-like       → Author. (Year). Title. URL
          markdown       → 1. [Title](URL)
        """
        self._reference_counter = 0
        self._canonical_cache = {}

        lines = ["# Bibliography", ""]
        all_sources: dict[str, tuple[int, ValidatedSource]] = {}

        for fact in facts:
            for src in getattr(fact, "sources", []):
                url = getattr(src, "url", "")
                if not url:
                    continue
                canonical = self._canonicalize_url(url)
                if canonical not in all_sources:
                    self._reference_counter += 1
                    vs = ValidatedSource(
                        url=url,
                        domain=getattr(src, "domain", ""),
                        tier=getattr(src, "tier", 3),
                        title=getattr(src, "title", ""),
                        retrieved_at=getattr(src, "retrieved_at", ""),
                        reference_number=self._reference_counter,
                    )
                    all_sources[canonical] = (self._reference_counter, vs)

        for num, src in sorted(all_sources.values(), key=lambda x: x[0]):
            if style == "inline-url":
                title = src.title or src.domain or "Untitled"
                lines.append(f"[{num}] {title}. {src.url}")
            elif style == "markdown":
                title = src.title or src.domain or "Link"
                lines.append(f"{num}. [{title}]({src.url})")
            elif style == "apa-like":
                title = src.title or "Untitled"
                lines.append(f"[{num}] {title}. Retrieved from {src.url}")

        return "\n".join(lines)
