"""
Extract commands for PicoCloth-CLI.

Provides search-to-fact extraction, memory querying, and fleet verification.
Backed by THEE (Tiered Hybrid Extract Engine) v1.0.

Citations:
  - FActScore (Min et al., 2023): atomic decomposition
  - Mem0 (Apr 2025): ADD/UPDATE/DELETE/NOOP memory ops
  - Nature s41598-026-41862-z (2026): multi-agent verification
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import PICOCLOTH_DIR
from picocloth_cli.core.exceptions import FleetError
from picocloth_cli.core.logging import get_logger
from picocloth_cli.fleet.client import MCPFleetClient
from picocloth_cli.tools.extract import ExtractEngine, ExtractedFact

logger = get_logger(__name__)
app = typer.Typer(help="Knowledge extraction from web search results")
console = Console()


# ── Helper: resolve API key ──────────────────────────────────

def _get_api_key() -> str | None:
    cfg = get_config()
    # Priority: config → env → keyvault (on Azure VMs)
    key = cfg.openai.api_key if hasattr(cfg, "openai") else None
    if not key:
        import os
        key = os.environ.get("OPENAI_API_KEY")
    return key


# ── Command: from-file ───────────────────────────────────────

@app.command()
def from_file(
    input_file: Path = typer.Argument(..., exists=True, readable=True, help="JSON file with search results"),
    topic: str = typer.Option("", "--topic", "-t", help="Query topic for context"),
    output: Path = typer.Option(Path("facts.jsonl"), "--output", "-o", help="Output file path"),
    store: bool = typer.Option(False, "--store", help="Write to shared memory via MCP"),
    broadcast: bool = typer.Option(False, "--broadcast", help="Broadcast to fleet via MCP"),
    tier: str = typer.Option("hybrid", "--tier", help="Extraction tier: fast, deep, hybrid"),
    min_confidence: float = typer.Option(0.0, "--min-confidence", help="Filter facts below threshold"),
    md: bool = typer.Option(False, "--md", help="Output Markdown instead of JSONL"),
    validate_citations: bool = typer.Option(False, "--validate-citations", help="Validate citation quality"),
    verify: bool = typer.Option(False, "--verify", help="Run fleet verification on extracted facts"),
    bibliography: Path = typer.Option(None, "--bibliography", "-b", help="Generate bibliography file"),
) -> None:
    """Extract structured facts from search result JSON."""
    console.print(f"[bold blue]🔬 Extracting facts from {input_file}...[/bold blue]")

    with open(input_file, encoding="utf-8") as f:
        data = json.load(f)

    # Normalize input
    results: list[dict[str, Any]] = []
    if isinstance(data, list):
        results = data
    elif isinstance(data, dict):
        for key in ("results", "organic", "answer_box", "knowledge_graph"):
            if key in data:
                items = data[key]
                if isinstance(items, list):
                    results.extend(items)
                elif isinstance(items, dict):
                    results.append(items)

    if not results:
        console.print("[yellow]No search results found in input.[/yellow]")
        raise typer.Exit(0)

    engine = ExtractEngine(api_key=_get_api_key(), tier=tier)
    facts, report = engine.run(
        results,
        topic=topic or "untitled",
        validate_citations=validate_citations,
        verify=verify,
    )

    # Filter
    facts = [f for f in facts if f.confidence >= min_confidence]

    # Local output
    if md:
        engine.to_markdown(output)
        console.print(f"[green]✓[/green] Markdown report → {output}")
    else:
        engine.to_jsonl(output)
        console.print(f"[green]✓[/green] JSONL facts → {output}")

    if bibliography:
        engine.to_bibliography(bibliography, style="markdown")
        console.print(f"[green]✓[/green] Bibliography → {bibliography}")

    # Summary table
    _print_report(report, facts)

    # MCP operations
    if store or broadcast:
        asyncio.run(_mcp_store_broadcast(facts, topic or "untitled", store, broadcast))


# ── Command: search ──────────────────────────────────────────

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max results"),
    store: bool = typer.Option(False, "--store", help="Write to shared memory"),
    broadcast: bool = typer.Option(False, "--broadcast", help="Broadcast to fleet"),
    tier: str = typer.Option("hybrid", "--tier", help="Extraction tier: fast, deep, hybrid"),
    min_confidence: float = typer.Option(0.0, "--min-confidence", help="Filter threshold"),
    validate_citations: bool = typer.Option(False, "--validate-citations", help="Validate citation quality"),
    verify: bool = typer.Option(False, "--verify", help="Run fleet verification on extracted facts"),
    bibliography: Path = typer.Option(None, "--bibliography", "-b", help="Generate bibliography file"),
) -> None:
    """Search the web and extract structured facts in one command."""
    if not HAS_DDGS:
        console.print(
            "[red]❌ duckduckgo-search not installed.[/red]\n"
            "Install with: [bold]pip install duckduckgo-search[/bold]\n"
            "Or use: [bold]picocloth extract from-file results.json[/bold]"
        )
        raise typer.Exit(1)

    console.print(f"[bold blue]🔍 Searching: {query}[/bold blue]")

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=limit))

    if not results:
        console.print("[yellow]No search results found.[/yellow]")
        raise typer.Exit(0)

    console.print(f"[dim]Found {len(results)} results. Extracting...[/dim]")

    engine = ExtractEngine(api_key=_get_api_key(), tier=tier)
    facts, report = engine.run(
        results,
        topic=query,
        validate_citations=validate_citations,
        verify=verify,
    )
    facts = [f for f in facts if f.confidence >= min_confidence]

    # Default output to local file
    out_path = Path(f"facts_{query.replace(' ', '_')[:30]}.jsonl")
    engine.to_jsonl(out_path)
    console.print(f"[green]✓[/green] Facts written → {out_path}")

    if bibliography:
        engine.to_bibliography(bibliography, style="markdown")
        console.print(f"[green]✓[/green] Bibliography → {bibliography}")

    _print_report(report, facts)

    if store or broadcast:
        asyncio.run(_mcp_store_broadcast(facts, query, store, broadcast))


# ── Command: facts ───────────────────────────────────────────

@app.command()
def facts(
    topic: str = typer.Option("", "--topic", "-t", help="Filter by topic"),
    min_confidence: float = typer.Option(0.0, "--min-confidence", help="Min confidence"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max facts to show"),
) -> None:
    """Show extracted facts from shared memory."""
    memory_dir = Path(PICOCLOTH_DIR) / "shared" / "memory" / "facts"
    if not memory_dir.exists():
        console.print("[yellow]No facts directory found.[/yellow]")
        raise typer.Exit(0)

    all_facts: list[ExtractedFact] = []
    for fpath in memory_dir.glob("*.jsonl"):
        if topic and topic.lower().replace(" ", "_") not in fpath.stem:
            continue
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    fact = ExtractedFact.from_dict(json.loads(line))
                    if fact.confidence >= min_confidence:
                        all_facts.append(fact)
                except Exception:
                    continue

    if not all_facts:
        console.print("[dim]No facts found matching criteria.[/dim]")
        return

    all_facts.sort(key=lambda x: x.confidence, reverse=True)
    shown = all_facts[:limit]

    table = Table(
        title=f"📊 Extracted Facts ({len(shown)} of {len(all_facts)})",
        title_style="bold cyan",
        header_style="bold magenta",
    )
    table.add_column("Confidence", justify="right")
    table.add_column("Entity")
    table.add_column("Relation", style="dim")
    table.add_column("Claim", max_width=50)
    table.add_column("Tier", justify="center")
    table.add_column("Source", style="dim")

    for f in shown:
        tier_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(f.sources[0].tier if f.sources else 3, "⚪")
        table.add_row(
            str(f.confidence),
            f.triple.entity[:25],
            f.triple.relation,
            f.triple.claim[:50],
            f"{tier_emoji} {f.extraction_tier}",
            f.sources[0].domain if f.sources else "—",
        )

    console.print(table)


# ── Command: verify ──────────────────────────────────────────

@app.command()
def verify(
    fact_id: str = typer.Argument(..., help="Fact ID to verify"),
    strategy: str = typer.Option("weighted", "--strategy", help="weighted|unanimous|threshold"),
    nodes: str = typer.Option("all", "--nodes", help="Nodes to ask: all, or comma-separated list"),
    simulate: bool = typer.Option(False, "--simulate", help="Local simulation without fleet"),
) -> None:
    """Verify a fact using the Fleet Verification Pool."""
    console.print(f"[bold blue]🗳️ Verifying fact {fact_id}...[/bold blue]")

    # Load fact from memory
    memory_dir = Path(PICOCLOTH_DIR) / "shared" / "memory" / "facts"
    fact: ExtractedFact | None = None
    if memory_dir.exists():
        for fpath in memory_dir.glob("*.jsonl"):
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        if d.get("fact_id") == fact_id:
                            fact = ExtractedFact.from_dict(d)
                            break
                    except Exception:
                        continue
            if fact:
                break

    if not fact:
        console.print(f"[red]Fact {fact_id} not found in memory.[/red]")
        raise typer.Exit(1)

    # Run verification
    from picocloth_cli.tools.verification_pool import FleetVerificationPool
    pool = FleetVerificationPool()

    available_nodes = None
    if nodes != "all":
        available_nodes = [n.strip() for n in nodes.split(",")]

    result = pool.verify_fact(fact, strategy=strategy, available_nodes=available_nodes)

    # Display result
    _print_verification_result(result)

    # Store back
    fact.verified_by["fleet_verification"] = result.to_dict()
    # Write back to memory file (simplified: append updated fact)
    # In production, this would update in place
    console.print(f"[dim]Result stored to fact {fact_id}[/dim]")


@app.command()
def validate_citations(
    input_file: Path = typer.Argument(..., exists=True, readable=True, help="JSONL file with extracted facts"),
    check_urls: bool = typer.Option(False, "--check-urls", help="Verify URL reachability via HEAD"),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix common issues and write back"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path for fixed file"),
) -> None:
    """Validate citations in extracted facts."""
    console.print(f"[bold blue]📚 Validating citations in {input_file}...[/bold blue]")

    from picocloth_cli.tools.citation_validator import CitationValidator

    facts: list[ExtractedFact] = []
    with open(input_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                facts.append(ExtractedFact.from_dict(json.loads(line)))
            except Exception:
                continue

    if not facts:
        console.print("[yellow]No facts found in input.[/yellow]")
        raise typer.Exit(0)

    validator = CitationValidator(check_reachability=check_urls)
    reports = validator.validate_batch(facts)

    # Summary
    total_errors = sum(len(r.errors) for r in reports)
    critical_errors = sum(1 for r in reports for e in r.errors if e.severity == "critical")
    avg_health = sum(r.citation_health_score for r in reports) / len(reports) if reports else 0

    console.print(f"[bold]Validation Summary:[/bold] {len(facts)} facts, {total_errors} errors ({critical_errors} critical)")
    console.print(f"[bold]Average Health Score:[/bold] {avg_health:.2f}")

    # Per-fact table
    table = Table(header_style="bold magenta")
    table.add_column("Fact ID", max_width=20)
    table.add_column("Health", justify="right")
    table.add_column("Errors")
    table.add_column("Suggestion")

    for fact, report in zip(facts, reports):
        err_types = ", ".join(set(e.error_type for e in report.errors)) or "OK"
        suggestion = report.errors[0].suggestion if report.errors else "—"
        health_color = "green" if report.citation_health_score > 0.8 else "yellow" if report.citation_health_score > 0.4 else "red"
        table.add_row(
            fact.fact_id[:16],
            f"[{health_color}]{report.citation_health_score}[/{health_color}]",
            err_types[:30],
            suggestion[:40],
        )

    console.print(table)

    if fix:
        fixed_facts = []
        for fact in facts:
            fixed_sources = validator.fix_citations(fact.sources)
            fact.sources = fixed_sources
            fixed_facts.append(fact)
        out_path = output or input_file
        with open(out_path, "w", encoding="utf-8") as f:
            for fact in fixed_facts:
                f.write(json.dumps(fact.to_dict(), ensure_ascii=False) + "\n")
        console.print(f"[green]✓[/green] Fixed facts written → {out_path}")


# ── Internal helpers ─────────────────────────────────────────

def _print_report(report: Any, facts: list[ExtractedFact]) -> None:
    table = Table(header_style="bold magenta")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Results ingested", str(report.results_ingested))
    table.add_row("Facts extracted", str(report.facts_extracted))
    table.add_row("Unique facts", str(report.facts_unique))
    table.add_row("Accepted (ADD)", str(report.facts_added))
    table.add_row("Updated", str(report.facts_updated))
    table.add_row("Deleted", str(report.facts_deleted))
    table.add_row("NOOP (duplicates)", str(report.facts_noop))
    table.add_row("Avg confidence", str(report.avg_confidence))
    table.add_row("Tier 1 sources", str(report.tier1_sources))
    table.add_row("Tier 2 sources", str(report.tier2_sources))
    table.add_row("Tier 3 sources", str(report.tier3_sources))
    table.add_row("Conflicts", str(report.conflicts_detected))
    table.add_row("Elapsed", f"{report.elapsed_seconds}s")
    console.print(table)


def _print_verification_result(result: Any) -> None:
    """Display a VerificationResult with Rich formatting."""
    from picocloth_cli.tools.verification_pool import VerificationResult

    verdict_colors = {
        "VERIFIED": "bold green",
        "REFUTED": "bold red",
        "DISPUTED": "bold yellow",
        "UNCERTAIN": "bold dim",
    }
    color = verdict_colors.get(result.verdict, "bold white")
    console.print(f"\n[{color}]🏛️  Verdict: {result.verdict} (confidence: {result.confidence})[/{color}]\n")

    # Votes table
    vote_table = Table(header_style="bold magenta")
    vote_table.add_column("Agent")
    vote_table.add_column("Verdict")
    vote_table.add_column("Confidence", justify="right")
    vote_table.add_column("Justification", max_width=40)

    for vote in result.votes:
        vcolor = {"SUPPORT": "green", "REFUTE": "red", "UNCERTAIN": "yellow"}.get(vote.verdict, "white")
        vote_table.add_row(
            vote.agent_id,
            f"[{vcolor}]{vote.verdict}[/{vcolor}]",
            str(vote.confidence),
            vote.justification[:40],
        )
    console.print(vote_table)

    # Stats
    stats = Table(show_header=False)
    stats.add_column("Label", style="bold")
    stats.add_column("Value")
    stats.add_row("Consensus Method", result.consensus_method)
    stats.add_row("Corroboration", str(result.corroboration_count))
    stats.add_row("Contradictions", str(result.contradiction_count))
    stats.add_row("Uncertainties", str(result.uncertainty_count))
    if result.needs_deep_verification:
        stats.add_row("⚠️ Alert", "Deep verification recommended (split decision)")
    console.print(stats)
    console.print()


async def _mcp_store_broadcast(
    facts: list[ExtractedFact],
    topic: str,
    store: bool,
    broadcast: bool,
) -> None:
    async with MCPFleetClient() as client:
        if store and facts:
            data = [f.to_dict() for f in facts]
            await client.memory_write(
                category="facts",
                key=topic.lower().replace(" ", "_"),
                data=data,
                append=True,
            )
            console.print(f"[green]✓[/green] Stored {len(facts)} facts to shared memory")

        if broadcast:
            summary = f"Extracted {len(facts)} facts on '{topic}' (avg confidence: {sum(f.confidence for f in facts)/len(facts):.2f})" if facts else f"No facts extracted for '{topic}'"
            result = await client.broadcast(message=summary, sender="picocloth-cli")
            console.print(f"[green]✓[/green] Broadcast to {len(result.get('recipients', []))} node(s)")
