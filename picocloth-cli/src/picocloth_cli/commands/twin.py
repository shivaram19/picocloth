"""
Digital twin archive commands.

Query, extract, and inspect digital twin snapshots created by the
pre-compaction Digital Twin Guardian hook.

Citation: PicoCloth Digital Twin Protocol (docs/ARCHITECTURE.md)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

from picocloth_cli.core.constants import DIGITAL_TWINS_DIR, NODES
from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)
app = typer.Typer(help="Digital twin archive operations")
console = Console()


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (matches filenames and content)"),
    node: Optional[str] = typer.Option(None, "--node", "-n", help="Filter by node ID"),  # noqa: UP007
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum results"),
) -> None:
    """Search digital twin archives."""
    twin_dir = DIGITAL_TWINS_DIR
    if node:
        if node not in NODES:
            console.print(f"[red]Unknown node: {node}[/red]")
            raise typer.Exit(1)
        twin_dir = twin_dir / node

    if not twin_dir.exists():
        console.print("[dim]No digital twins found.[/dim]")
        return

    results = []
    for f in sorted(twin_dir.rglob("*.json"), reverse=True):
        try:
            content = f.read_text()
            if query.lower() in content.lower() or query.lower() in f.name.lower():
                results.append(f)
                if len(results) >= limit:
                    break
        except Exception:
            continue

    if not results:
        console.print(f"[yellow]No twins matching '{query}'[/yellow]")
        return

    table = Table(
        title=f"🔍 Digital Twin Search: '{query}'",
        title_style="bold cyan",
        header_style="bold magenta",
    )
    table.add_column("Node")
    table.add_column("File", style="dim")
    table.add_column("Size", justify="right")

    for r in results:
        node_name = r.parent.name if r.parent != DIGITAL_TWINS_DIR else "—"
        size = r.stat().st_size
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
        table.add_row(node_name, r.name, size_str)

    console.print(table)


@app.command()
def show(
    filepath: str = typer.Argument(..., help="Path to twin JSON file (relative to shared/digital-twins/)"),
) -> None:
    """Display a digital twin snapshot."""
    path = DIGITAL_TWINS_DIR / filepath
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    try:
        import json
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON:[/red] {exc}")
        raise typer.Exit(1)

    # Pretty display
    twin_id = data.get("twin_id", "unknown")
    node_id = data.get("node_id", "unknown")
    trigger = data.get("trigger", "unknown")
    timestamp = data.get("timestamp", "unknown")
    facts = data.get("extracted_facts", [])

    console.print(Panel(
        f"[bold]Twin ID:[/bold] {twin_id}\n"
        f"[bold]Node:[/bold] {node_id}\n"
        f"[bold]Trigger:[/bold] {trigger}\n"
        f"[bold]Timestamp:[/bold] {timestamp}\n"
        f"[bold]Facts Extracted:[/bold] {len(facts)}",
        title="🧬 Digital Twin Snapshot",
        border_style="magenta",
    ))

    if facts:
        console.print("\n[bold]Extracted Facts:[/bold]")
        for f in facts:
            confidence = f.get("confidence", 0.0)
            conf_color = "green" if confidence > 0.8 else "yellow" if confidence > 0.5 else "red"
            console.print(f"  • {f.get('key', '?')}: {f.get('content', '?')} [" + conf_color + f"]{confidence:.0%}[" + conf_color + "]")

    # Show raw JSON in expandable panel
    console.print(Panel(JSON.from_data(data), title="Raw JSON", border_style="dim"))


@app.command()
def stats() -> None:
    """Show digital twin archive statistics."""
    if not DIGITAL_TWINS_DIR.exists():
        console.print("[dim]No digital twin archive found.[/dim]")
        return

    table = Table(
        title="🧬 Digital Twin Archive Statistics",
        title_style="bold cyan",
        header_style="bold magenta",
    )
    table.add_column("Node")
    table.add_column("Twins", justify="right")
    table.add_column("Total Size", justify="right")
    table.add_column("Latest", style="dim")

    total_twins = 0
    total_size = 0

    for node in NODES:
        node_dir = DIGITAL_TWINS_DIR / node
        if not node_dir.exists():
            table.add_row(node, "0", "—", "—")
            continue
        files = list(node_dir.glob("*.json"))
        count = len(files)
        size = sum(f.stat().st_size for f in files)
        latest = max((f.name for f in files), default="—")
        total_twins += count
        total_size += size
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
        table.add_row(node, str(count), size_str, latest[:30])

    console.print(table)
    size_total_str = f"{total_size / 1024:.1f} KB" if total_size < 1024 * 1024 else f"{total_size / 1024 / 1024:.1f} MB"
    console.print(f"\n[bold]Total:[/bold] {total_twins} twins, {size_total_str}")
