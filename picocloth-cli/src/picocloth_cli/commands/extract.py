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
    facts, report = engine.run(results, topic=topic or "untitled")

    # Filter
    facts = [f for f in facts if f.confidence >= min_confidence]

    # Local output
    if md:
        engine.to_markdown(output)
        console.print(f"[green]✓[/green] Markdown report → {output}")
    else:
        engine.to_jsonl(output)
        console.print(f"[green]✓[/green] JSONL facts → {output}")

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
    facts, report = engine.run(results, topic=query)
    facts = [f for f in facts if f.confidence >= min_confidence]

    # Default output to local file
    out_path = Path(f"facts_{query.replace(' ', '_')[:30]}.jsonl")
    engine.to_jsonl(out_path)
    console.print(f"[green]✓[/green] Facts written → {out_path}")

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
    nodes: str = typer.Option("all", "--nodes", help="Nodes to ask: all, or comma-separated list"),
) -> None:
    """Request fleet-wide verification of a fact via MCP."""
    console.print(f"[bold blue]🗳️ Requesting fleet verification for {fact_id}...[/bold blue]")

    async def _do_verify() -> None:
        async with MCPFleetClient() as client:
            result = await client.spawn_task(
                target_node=nodes,
                task=f"Verify fact {fact_id}: check corroboration, assess confidence, report contradictions.",
                priority="high",
            )
            console.print(f"[green]✓[/green] Verification task spawned: {result.get('task_id', 'N/A')}")

    try:
        asyncio.run(_do_verify())
    except FleetError as exc:
        console.print(f"[red]Verification failed:[/red] {exc.message}")
        raise typer.Exit(1)


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
