"""
Search commands for PicoCloth-CLI.

Modes of discovery:
  clever        → Pattern-optimized, platform-intelligent queries
  curious       → Exploratory, scent-following, serendipitous
  targeted      → Precision strikes: exact phrase, site, author, date, filetype
  discover      → Indie web / expert blog discovery
  optimize      → Retrospective query optimization
  watch         → Continuous topic monitoring
  watch-daemon  → Run monitor daemon

Citations:
  - Pirolli & Card (1999): Information Foraging Theory
  - Bioptic Agent (2025): Completeness-oriented search control
  - Schultheiß et al. (2022): SEO vs content quality
  - ConvSearch-R1 (2025): RL query reformulation
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from picocloth_cli.core.config import get_config
from picocloth_cli.core.logging import get_logger
from picocloth_cli.tools.search_strategy import SearchStrategyEngine

logger = get_logger(__name__)
app = typer.Typer(help="Knowledge discovery: clever, curious, targeted, indie, optimize, watch")
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


@app.command()
def discover(
    topic: str = typer.Argument(..., help="Topic to discover indie sources for"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max sources"),
    hn: bool = typer.Option(True, "--hn/--no-hn", help="Search Hacker News"),
    extract_facts: bool = typer.Option(False, "--extract", "-x", help="Extract facts from discovered sources"),
) -> None:
    """Discover expert blogs, newsletters, and indie web sources."""
    from picocloth_cli.tools.indie_discovery import IndieWebDiscoveryEngine

    engine = IndieWebDiscoveryEngine()
    sources = engine.discover(topic, limit=limit, include_hn=hn)

    if not sources:
        console.print(f"[yellow]No indie sources found for '{topic}'.[/yellow]")
        return

    console.print(f"[bold cyan]🔭 Indie Web Discovery: {topic}[/bold cyan]")
    console.print(f"[dim]{len(sources)} expert/indie sources found[/dim]\n")

    table = Table(header_style="bold magenta")
    table.add_column("Source")
    table.add_column("Category")
    table.add_column("Quality", justify="right")
    table.add_column("Domain", style="dim")
    table.add_column("Topics", style="dim")

    for src in sources:
        qcolor = "green" if src.quality_score > 0.7 else "yellow" if src.quality_score > 0.4 else "red"
        table.add_row(
            src.name[:30],
            src.category,
            f"[{qcolor}]{src.quality_score}[/{qcolor}]",
            src.domain[:25],
            ", ".join(src.topics[:3]),
        )

    console.print(table)

    if extract_facts:
        console.print("\n[dim]Extracting facts from discovered sources...[/dim]")
        # Build queries and execute
        from picocloth_cli.tools.extract import ExtractEngine
        ee = ExtractEngine(tier="fast")
        all_facts = []
        for src in sources[:5]:  # Limit to top 5 for cost control
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(f"{topic} site:{src.domain}", max_results=3))
                if results:
                    facts, _ = ee.run(results, topic=topic)
                    all_facts.extend(facts)
            except Exception as exc:
                logger.debug("Extraction failed for %s: %s", src.domain, exc)
        console.print(f"[green]✓[/green] Extracted {len(all_facts)} facts from {len(sources)} sources")


@app.command()
def optimize(
    topic: str = typer.Argument(..., help="Research topic to optimize"),
    limit: int = typer.Option(5, "--limit", "-n", help="Max suggestions"),
    execute: bool = typer.Option(False, "--execute", "-x", help="Run suggested searches"),
) -> None:
    """Suggest optimized search queries based on historical yield data."""
    from picocloth_cli.tools.retrospective_optimizer import RetrospectiveOptimizer

    optimizer = RetrospectiveOptimizer()
    suggestions = optimizer.suggest_reformulation(topic, limit=limit)
    stats = optimizer.get_stats()

    if stats.get("total_records", 0) > 0:
        console.print(f"[bold cyan]🧠 Query Optimization: {topic}[/bold cyan]")
        console.print(f"[dim]Based on {stats['total_records']} historical searches[/dim]\n")
    else:
        console.print(f"[bold cyan]🧠 Query Optimization: {topic}[/bold cyan]")
        console.print(f"[dim]No history yet. Using generic high-yield templates.[/dim]\n")

    table = Table(header_style="bold magenta")
    table.add_column("Rank", justify="right", width=4)
    table.add_column("Suggested Query", max_width=50)
    table.add_column("Exp. Yield", justify="right")
    table.add_column("Confidence", justify="right")
    table.add_column("Rationale", style="dim")

    for i, sug in enumerate(suggestions, 1):
        table.add_row(
            str(i),
            sug.suggested_query[:50],
            str(sug.expected_yield),
            str(sug.confidence),
            sug.rationale[:35],
        )

    console.print(table)

    if execute:
        console.print("\n[dim]Executing suggested queries...[/dim]")
        for sug in suggestions[:3]:
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(sug.suggested_query, max_results=5))
                if results:
                    from picocloth_cli.tools.extract import ExtractEngine
                    ee = ExtractEngine(tier="fast")
                    facts, report = ee.run(results, topic=topic)
                    console.print(f"[green]✓[/green] '{sug.suggested_query[:40]}' → {len(facts)} facts")
            except Exception as exc:
                logger.warning("Execution failed for '%s': %s", sug.suggested_query, exc)


@app.command()
def watch(
    topic: str = typer.Argument(..., help="Topic to monitor"),
    query: str = typer.Option(None, "--query", "-q", help="Search query (defaults to topic)"),
    interval: int = typer.Option(24, "--interval", "-i", help="Hours between checks"),
    alert: str = typer.Option("new_facts", "--alert", "-a", help="Comma-separated: new_facts,confidence_drop"),
    remove: bool = typer.Option(False, "--remove", help="Remove existing watch"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all watches"),
    run_now: bool = typer.Option(False, "--run-now", help="Run check immediately"),
) -> None:
    """Monitor a topic for new facts and changes."""
    from picocloth_cli.tools.topic_monitor import TopicMonitor

    monitor = TopicMonitor()

    if list_all:
        watches = monitor.list_watches()
        if not watches:
            console.print("[yellow]No active watches.[/yellow]")
            return
        table = Table(header_style="bold magenta")
        table.add_column("Watch ID")
        table.add_column("Topic")
        table.add_column("Interval (h)", justify="right")
        table.add_column("Last Run", style="dim")
        table.add_column("Active")
        for w in watches:
            table.add_row(w.watch_id[:20], w.topic, str(w.interval_hours), w.last_run[:16] or "—", "✓" if w.active else "✗")
        console.print(table)
        return

    if remove:
        if monitor.remove_watch(topic):
            console.print(f"[green]✓[/green] Watch removed for '{topic}'")
        else:
            console.print(f"[yellow]No watch found for '{topic}'[/yellow]")
        return

    if run_now:
        # Find watch by topic
        watches = monitor.list_watches()
        target = None
        for w in watches:
            if w.topic.lower() == topic.lower():
                target = w.watch_id
                break
        if not target:
            target = monitor.add_watch(topic, query or topic, interval, alert.split(","))
        diff = monitor.run_watch(target)
        if diff:
            console.print(f"[bold]Diff for {topic}:[/bold] {diff.summary}")
            if diff.new_facts:
                console.print(f"[green]New:[/green] {len(diff.new_facts)} fact(s)")
        return

    # Add new watch
    watch_id = monitor.add_watch(topic, query or topic, interval, alert.split(","))
    console.print(f"[green]✓[/green] Watch added: {watch_id}")
    console.print(f"[dim]Will check every {interval} hour(s) for: {alert}[/dim]")


@app.command()
def watch_daemon(
    once: bool = typer.Option(False, "--once", help="Run once and exit"),
    interval: int = typer.Option(60, "--interval", help="Seconds between checks"),
) -> None:
    """Run the topic monitor daemon. Checks all due watches."""
    from picocloth_cli.tools.topic_monitor import TopicMonitor

    monitor = TopicMonitor()
    console.print("[bold]🔍 Topic Monitor Daemon started[/bold]")
    console.print(f"[dim]Checking every {interval}s. Press Ctrl+C to stop.[/dim]\n")

    try:
        while True:
            diffs = monitor.run_all_due()
            for diff in diffs:
                if diff.new_facts or diff.confidence_changes:
                    console.print(f"[bold green]🚨 Alert:[/bold green] {diff.summary}")
                else:
                    console.print(f"[dim]No changes for {diff.watch_id}[/dim]")
            if once:
                console.print("[dim]--once specified, exiting.[/dim]")
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Daemon stopped.[/dim]")


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
    """Execute search queries and optionally extract + store."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        console.print("[yellow]duckduckgo-search not installed. Install to execute.[/yellow]")
        return

    console.print(f"[dim]Executing {len(plan.queries)} queries...[/dim]")

    all_results = []
    for q in plan.queries[:3]:  # Cost control: max 3 queries
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(q["query"], max_results=5))
                all_results.extend(results)
                console.print(f"[dim]  {q['query'][:50]} → {len(results)} results[/dim]")
        except Exception as exc:
            logger.warning("Search failed for '%s': %s", q["query"], exc)

    if not all_results:
        console.print("[yellow]No results found.[/yellow]")
        return

    # Extract facts
    from picocloth_cli.tools.extract import ExtractEngine
    engine = ExtractEngine(tier="fast")
    facts, report = engine.run(all_results, topic=plan.topic)

    # Record yield for retrospective optimization
    from picocloth_cli.tools.retrospective_optimizer import RetrospectiveOptimizer
    opt = RetrospectiveOptimizer()
    opt.record(plan, len(all_results), len(facts), report.avg_confidence)

    console.print(f"[green]✓[/green] Extracted {len(facts)} facts (avg conf: {report.avg_confidence})")

    if store and facts:
        # Store locally
        out_path = Path(f"facts_{plan.topic.replace(' ', '_')[:30]}.jsonl")
        engine.to_jsonl(out_path)
        console.print(f"[green]✓[/green] Stored → {out_path}")
