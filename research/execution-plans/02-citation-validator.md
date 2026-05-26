# Execution Plan: Gap 9 — Citation Association Quality

## Research Backing
- LiveResearchBench (Salesforce AI Research, 2026, arXiv:2510.14240): "Models struggle most with citation correctness and formatting." E3 errors (unsupported claims) dominate. Open Deep Research: 91.9 unsupported claims per market analysis.
- Deerflow+ Stabilization: Added inline-citation support + validation pass enforcing one-to-one mapping between in-text citations and reference entries.
- DEFT Taxonomy (Zhang et al., Dec 2025): Low-authority citation = 33.10% of failures. Strategic Content Fabrication = 18.95%.

## File
`picocloth-cli/src/picocloth_cli/tools/citation_validator.py`

## Status
✅ File created and compiles. Needs minor fixes + integration.

---

## Step 2.1: Fix `_check_url_health` for Batch Safety

**Problem**: Synchronous `urllib.request` HEAD can hang. Current timeout=5 is set but not robust for batch operations.
**Fix**: Add explicit `socket.setdefaulttimeout()` guard + `urllib.error` exception handling.

**Code change** in `citation_validator.py`:
```python
import socket
import urllib.error

def _check_url_health(self, url: str) -> tuple[bool, int | None]:
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(5)
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "PicoCloth-CitationValidator/1.0")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return True, resp.status
    except urllib.error.HTTPError as e:
        # 403/405 often means HEAD not allowed but site exists
        if e.code in (403, 405):
            return True, e.code
        return False, e.code
    except Exception:
        return False, None
    finally:
        socket.setdefaulttimeout(old_timeout)
```

**Acceptance criteria**:
- [ ] URL returning 403/405 is marked reachable (site exists)
- [ ] Network timeout returns `(False, None)` without hanging
- [ ] Default socket timeout restored after check

---

## Step 2.2: Add `ValidatedSource` Extension to `ExtractedFact`

**Problem**: `ExtractedFact` stores basic `Source` but not validation metadata.
**Fix**: After validation, upgrade `Source` objects to `ValidatedSource` metadata. Store `CitationReport` in `verified_by["citation_validation"]`.

**No schema change needed** — reuse existing `verified_by` dict.

**Code addition** to `extract.py` tool, in `ExtractEngine.run()`:
```python
def run(self, inputs, topic="", validate_citations: bool = False):
    # ... existing pipeline ...
    all_facts = self.xref.cross_reference(all_facts)
    
    if validate_citations:
        from picocloth_cli.tools.citation_validator import CitationValidator
        validator = CitationValidator(check_reachability=False)
        reports = validator.validate_batch(all_facts)
        for fact, report in zip(all_facts, reports):
            fact.verified_by["citation_validation"] = report.to_dict()
            # Update confidence based on citation health
            health = report.citation_health_score
            fact.confidence = round(fact.confidence * health, 2)
            fact.confidence_breakdown["citation_health"] = health
```

**Acceptance criteria**:
- [ ] `validate_citations=True` runs validator on all facts
- [ ] `fact.verified_by["citation_validation"]` contains report
- [ ] Confidence adjusted by citation health score
- [ ] Critical errors (E6_MISSING_CITATION) reduce confidence to near-zero

---

## Step 2.3: Add `validate-citations` CLI Command

**File**: `picocloth-cli/src/picocloth_cli/commands/extract.py`

**New command**:
```python
@app.command()
def validate_citations(
    input_file: Path = typer.Argument(..., exists=True, help="JSONL file with extracted facts"),
    check_urls: bool = typer.Option(False, "--check-urls", help="Verify URL reachability via HEAD"),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix common issues and write back"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path"),
):
    """Validate citations in extracted facts."""
    # 1. Load facts from JSONL
    # 2. Run CitationValidator(check_reachability=check_urls)
    # 3. Display Rich table: Fact | Health Score | Errors
    # 4. If --fix, run fix_citations() and write back
```

**Rich display**:
- Summary: Total facts, Valid sources, Invalid sources, Critical errors, Warnings
- Per-fact table: Fact ID | Health | Error types | Suggestion
- Bibliography preview (top 10 sources)

**Acceptance criteria**:
- [ ] `picocloth extract validate-citations facts.jsonl` shows health scores
- [ ] `--check-urls` performs HEAD requests (slower but thorough)
- [ ] `--fix` writes corrected sources back to file

---

## Step 2.4: Add `--validate-citations` to `search` and `from-file`

**Code change** in `commands/extract.py`:
- Add `validate_citations: bool = typer.Option(False, "--validate-citations")` to both commands
- Pass through to `ExtractEngine.run(validate_citations=validate_citations)`

**Acceptance criteria**:
- [ ] `picocloth extract search "topic" --validate-citations` validates after extraction
- [ ] Default behavior unchanged (no validation)

---

## Step 2.5: Register `fleet_validate_citations` MCP Tool

**File**: `mcp-fleet-server/server.py`

**Add to `TOOLS`**:
```python
"fleet_validate_citations": {
    "description": "Validate citations for a set of facts",
    "parameters": {
        "type": "object",
        "properties": {
            "facts": {"type": "array", "description": "List of fact objects"},
            "check_urls": {"type": "boolean", "default": False}
        },
        "required": ["facts"]
    }
}
```

**Add handler**:
```python
elif name == "fleet_validate_citations":
    facts = arguments["facts"]
    check_urls = arguments.get("check_urls", False)
    # Inline minimal validation (server has no CLI dependency)
    reports = []
    for fact in facts:
        errors = []
        sources = fact.get("sources", [])
        if not sources:
            errors.append({"type": "E6_MISSING_CITATION", "severity": "critical"})
        for s in sources:
            url = s.get("url", "")
            if not url.startswith(("http://", "https://")):
                errors.append({"type": "E2_INCOMPLETE_URL", "severity": "critical", "url": url})
        reports.append({"fact_id": fact.get("fact_id"), "errors": errors, "valid": len(errors) == 0})
    return {"reports": reports}
```

**Acceptance criteria**:
- [ ] MCP tool returns validation reports without external dependencies
- [ ] Handles missing/empty inputs gracefully

---

## Step 2.6: Skill Documentation

**File**: `shared/doctrine/skills/citation-validator.md`

**Contents**:
- LiveResearchBench failure modes (E1-E8)
- Deerflow+ inline citation approach
- DEFT taxonomy alignment
- CLI usage: `validate-citations`, `--check-urls`, `--fix`
- Error type reference table

**Acceptance criteria**:
- [ ] Every error type (E1-E8) documented with example
- [ ] Research citations included

---

## Step 2.7: Test & Commit

**Test commands**:
```bash
cd /Users/shivaramgoud/picocloth-work
python3 -m py_compile picocloth-cli/src/picocloth_cli/tools/citation_validator.py
python3 -m py_compile picocloth-cli/src/picocloth_cli/commands/extract.py
python3 -c "
from picocloth_cli.tools.citation_validator import CitationValidator
v = CitationValidator()
# Test with a sample fact-like object
class FakeFact:
    fact_id = 'test1'
    sources = []
    triple = type('T', (), {'claim': 'AI market is $100B'})
    raw_text = 'AI market is $100B'
print(v.validate_fact(FakeFact()).to_dict())
"
```

**Commit message**:
```
feat(citations): Citation Validator v1.0

- E1-E8 error taxonomy aligned with LiveResearchBench
- URL canonicalization and duplicate detection
- Unsupported claim flagging heuristic
- Bibliography generation (inline-url, markdown, apa-like)
- Auto-fix for missing schemes and deduplication
- CLI: extract validate-citations --check-urls --fix
- MCP: fleet_validate_citations tool registered

Research: LiveResearchBench (2026), Deerflow+, DEFT Taxonomy
```
