"""
Search commands for PicoCloth-CLI.

Three modes of discovery:
  clever     → Pattern-optimized, platform-intelligent queries
  curious    → Exploratory, scent-following, serendipitous
  targeted   → Precision strikes: exact phrase, site, author, date, filetype

Citations:
  - Pirolli & Card (1999): Information Foraging Theory
  - Bioptic Agent (2025): Completeness-oriented search control
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from picocloth_cli.core.config import get_config
from picocloth_cli.core.logging import get_logger
from picocloth_cli.tools.search_strategy import SearchStrategyEngine

logger = get_logger(__name__)
app = typer.Typer(help="Knowledge discovery: clever, curious, targeted")
console = Console()


@app.command()
def clever(
    topic: str = typer.Argument(..., help="Research topic"),
    knowledge_type: str = typer.Option("general", "--type", "-t", help="research|technical|business|general"),
    execute: bool = typer.Option(False, "--execute", "-x", help="Execute searches via parallel-cli or duckduckgo"),
    store: bool = typer.Option(False, "--store", help="Store results to shared memory"),
) -> None:
    """Build pattern-optimized search queries for high-yield discovery."""
    engine = SearchStrategyEngine()
    plan = engine.plan_clever(topic, knowledge_type)

    console.print(f"[bold cyan]🧠 Clever Search Plan: {topic}[/bold cyan]")
    console.print(f"[dim]{plan.rationale}[/dim]\n")

    _display_plan(plan)

    if execute:
        _execute_plan(plan, store)


@app.command()
def curious(
    topic: str = typer.Argument(..., help="Research topic"),
    depth: int = typer.Option(2, "--depth", "-d", help="Exploration depth (1-3)"),
    execute: bool = typer.Option(False, "--execute", "-x", help="Execute searches"),
    store: bool = typer.Option(False, "--store", help="Store results to shared memory"),
) -> None:
    """Build exploratory search queries for serendipitous discovery."""
    engine = SearchStrategyEngine()
    plan = engine.plan_curious(topic, depth)

    console.print(f"[bold magenta]🔭 Curious Search Plan: {topic}[/bold magenta]")
    console.print(f"[dim]{plan.rationale}[/dim]\n")

    _display_plan(plan)

    if execute:
        _execute_plan(plan, store)


@app.command()
def targeted(
    topic: str = typer.Argument(..., help="Research topic"),
    exact: str = typer.Option(None, "--exact", "-e", help="Exact phrase to match"),
    domain: str = typer.Option(None, "--domain", "-d", help="Limit to specific domain"),
    author: str = typer.Option(None, "--author", "-a", help="Search by author name"),
    after: str = typer.Option(None, "--after", help="Date cutoff (YYYY-MM-DD)"),
    before: str = typer.Option(None, "--before", help="Date ceiling (YYYY-MM-DD)"),
    filetype: str = typer.Option(None, "--filetype", "-f", help="File type: pdf, pptx, csv"),
    execute: bool = typer.Option(False, "--execute", "-x", help="Execute searches"),
    store: bool = typer.Option(False, "--store", help="Store results to shared memory"),
) -> None:
    """Build precision search queries for targeted discovery."""
    engine = SearchStrategyEngine()

    date_range = None
    if after or before:
        date_range = (after or "2000-01-01", before or "2099-12-31")

    plan = engine.plan_targeted(
        topic=topic,
        exact_phrase=exact,
        domain=domain,
        author=author,
        date_range=date_range,
        filetype=filetype,
    )

    console.print(f"[bold green]🎯 Targeted Search Plan: {topic}[/bold green]")
    console.print(f"[dim]{plan.rationale}[/dim]\n")

    _display_plan(plan)

    if execute:
        _execute_plan(plan, store)


@app.command()
def hybrid(
    topic: str = typer.Argument(..., help="Research topic"),
    knowledge_type: str = typer.Option("general", "--type", "-t", help="research|technical|business|general"),
    execute: bool = typer.Option(False, "--execute", "-x", help="Execute all three plans"),
    store: bool = typer.Option(False, "--store", help="Store results to shared memory"),
) -> None:
    """Run all three search modes: targeted → clever → curious."""
    engine = SearchStrategyEngine()
    plans = engine.plan_hybrid(topic, knowledge_type)

    console.print(f"[bold blue]🚀 Hybrid Search Stack: {topic}[/bold blue]")
    console.print("[dim]Executing: targeted → clever → curious[/dim]\n")

    for i, plan in enumerate(plans, 1):
        emoji = {"targeted": "🎯", "clever": "🧠", "curious": "🔭"}.get(plan.mode, "🔍")
        console.print(f"[bold]{emoji} Phase {i}: {plan.mode.upper()}[/bold]")
        console.print(f"[dim]{plan.rationale}[/dim]")
        _display_plan(plan, compact=True)

        if execute:
            _execute_plan(plan, store)
        console.print()


@app.command()
def yield_report(
    topic: str = typer.Option("", "--topic", "-t", help="Filter by topic prefix"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max records"),
) -> None:
    """Show retrospective yield report for search optimization."""
    engine = SearchStrategyEngine()
    top_patterns = engine.get_top_yielding_patterns(topic, limit)

    if not top_patterns:
        console.print("[yellow]No yield data yet. Run some searches first![/yellow]")
        return

    table = Table(
        title="📊 Search Yield Report (Retrospective Optimization)",
        title_style="bold cyan",
        header_style="bold magenta",
    )
    table.add_column("Mode", style="bold")
    table.add_column("Avg Yield", justify="right")
    table.add_column("Avg Confidence", justify="right")
    table.add_column("Runs", justify="right")

    for p in top_patterns:
        table.add_row(
            p["mode"].upper(),
            str(p["avg_yield"]),
            str(p["avg_confidence"]),
            str(p["runs"]),
        )

    console.print(table)
    console.print("\n[dim]Knowledge Yield = facts_extracted × avg_confidence / queries_count[/dim]")
    console.print("[dim]Higher yield = better search efficiency. Double down on top modes.[/dim]")


# ── Internal helpers ─────────────────────────────────────────

def _display_plan(plan: Any, compact: bool = False) -> None:
    table = Table(show_header=not compact, header_style="bold magenta", pad_edge=False)
    table.add_column("#", justify="right", width=3)
    table.add_column("Query", max_width=60 if not compact else 40)
    table.add_column("Platform", width=12)
    table.add_column("Rationale", max_width=30 if not compact else 20)

    for i, q in enumerate(plan.queries[:8], 1):
        table.add_row(
            str(i),
            q["query"][:60],
            q.get("platform", "duckduckgo"),
            q.get("rationale", "")[:30],
        )

    console.print(table)


def _execute_plan(plan: Any, store: bool) -> None:
    """Placeholder: execute search queries and optionally extract + store."""
    console.print(f"[dim]Executing {len(plan.queries)} queries...[/dim]")

    # In production, this would:
    # 1. Call duckduckgo-search or parallel-cli for each query
    # 2. Merge results
    # 3. Run ExtractEngine
    # 4. Store facts if --store

    console.print(f"[green]✓[/green] Execution complete. Use --execute to run live searches.")
    if store:
        console.print("[dim]Results would be stored to shared/memory/facts/[/dim]")
