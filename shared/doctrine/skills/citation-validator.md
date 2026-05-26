# Skill: Citation Validator v1.0

## Research

- **LiveResearchBench** (Salesforce AI Research, 2026, arXiv:2510.14240): Comprehensive evaluation of 17 frontier deep research systems. "Models struggle most with citation correctness and formatting, rather than surface fluency." Key failure modes observed across ALL systems:
  - Mismatched in-text citations and references
  - Missing or incomplete URLs
  - Inconsistent citation formats
  - Uncited references in bibliography
  - Out-of-order reference numbering

- **Deerflow+** (Appendix D, LiveResearchBench): Added inline-citation support + validation pass enforcing one-to-one mapping between in-text citations and reference entries. Result: "higher information retention, stronger evidence structuring."

- **DEFT Taxonomy** (Zhang et al., Dec 2025): Low-authority citation = specific retrieval failure mode (33.10% of all failures). Strategic Content Fabrication = 18.95% of generation failures.

## Architecture

```
ExtractedFact → URL Health Check → Inline Citation Mapping → Format Consistency
→ Duplicate Detection → Unsupported Claim Flagging → CitationReport
```

**E1-E8 Error Taxonomy** (aligned with LiveResearchBench):
- **E1_INVALID_URL**: URL returns 4xx/5xx
- **E2_INCOMPLETE_URL**: Missing scheme or domain
- **E3_UNSUPPORTED_CLAIM**: Claim not verifiable from cited source
- **E4_MISMATCHED_CITATION**: In-text doesn't match reference
- **E5_DUPLICATE_REFERENCE**: Same source cited multiple times
- **E6_MISSING_CITATION**: Claim has no source
- **E7_INCONSISTENT_FORMAT**: Format varies within document
- **E8_ORPHANED_REFERENCE**: Reference never cited

## CLI Usage

```bash
# Validate citations in a facts file
picocloth extract validate-citations facts.jsonl

# Also check URL reachability (slower)
picocloth extract validate-citations facts.jsonl --check-urls

# Auto-fix and write back
picocloth extract validate-citations facts.jsonl --fix

# Validate during extraction
picocloth extract search "topic" --validate-citations
picocloth extract from-file results.json --validate-citations

# Generate bibliography
picocloth extract from-file results.json --bibliography bib.md
```

## MCP Tool

- **Tool**: `fleet_validate_citations`
- **Parameters**: `facts` (array), `check_urls` (boolean)
- **Returns**: `{reports: [{fact_id, errors, valid}]}`

## Why This Design

We chose **E1-E8 taxonomy** instead of a generic pass/fail because LiveResearchBench showed that citation errors have distinct patterns. Knowing that a system produces E3 (unsupported claims) vs E6 (missing citations) tells us different things about its reliability.

We made **URL checking opt-in** (`--check-urls`) because synchronous HTTP requests add significant latency. The default validation is fast and rule-based.

We added **bibliography generation** because Deerflow+ showed that inline citations reduce hallucination risk. A structured bibliography makes claims easier to verify.
