"""
Shared memory layer commands.

Provides CRUD access to the 4-layer shared memory architecture:
doctrine (immutable), project (append-only facts), state (real-time),
and run (ephemeral).

Citation: Graph Digital 4-layer memory (graph.digital/guides/ai-agents/memory)
Citation: Claude Code file-lock coordination (Anthropic, Feb 2026)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

from picocloth_cli.core.constants import (
    COMPACTION_ARCHIVE_DIR,
    DIGITAL_TWINS_DIR,
    DOCTRINE_DIR,
    PROJECT_DIR,
    RUN_DIR,
    SHARED_DIR,
    STATE_DIR,
)
from picocloth_cli.core.exceptions import MemoryError
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import (
    atomic_write_json,
    append_jsonl,
    lock_file,
    read_json_safe,
    read_jsonl,
)

logger = get_logger(__name__)
app = typer.Typer(help="Shared memory layer operations")
console = Console()

MEMORY_LAYERS = {
    "doctrine": DOCTRINE_DIR,
    "project": PROJECT_DIR,
    "state": STATE_DIR,
    "run": RUN_DIR,
    "digital-twins": DIGITAL_TWINS_DIR,
    "compaction-archive": COMPACTION_ARCHIVE_DIR,
}


def _resolve_path(layer: str, category: str, key: str) -> Path:
    """Resolve a memory address (layer/category/key) to a filesystem path."""
    base = MEMORY_LAYERS.get(layer)
    if base is None:
        raise MemoryError(f"Unknown memory layer: {layer}")
    return base / category / f"{key}.json"


@app.command()
def read(
    layer: str = typer.Argument(..., help="Memory layer: doctrine, project, state, run"),
    category: str = typer.Argument(..., help="Category within layer, e.g., facts, skills"),
    key: str = typer.Argument(..., help="Key / filename without extension"),
) -> None:
    """Read a value from shared memory."""
    try:
        path = _resolve_path(layer, category, key)
    except MemoryError as exc:
        console.print(f"[red]{exc.message}[/red]")
        raise typer.Exit(1)

    # Try JSON first, then JSONL
    data = read_json_safe(path, default=None)
    if data is None:
        jsonl_path = path.with_suffix(".jsonl")
        if jsonl_path.exists():
            data = read_jsonl(jsonl_path)
        else:
            console.print(f"[yellow]Not found:[/yellow] {layer}/{category}/{key}")
            return

    console.print(Panel(
        JSON.from_data(data),
        title=f"{layer}/{category}/{key}",
        border_style="cyan",
    ))


@app.command()
def write(
    layer: str = typer.Argument(..., help="Memory layer: doctrine, project, state, run"),
    category: str = typer.Argument(..., help="Category within layer"),
    key: str = typer.Argument(..., help="Key / filename without extension"),
    value: str = typer.Argument(..., help="JSON value to write"),
    append: bool = typer.Option(False, "--append", "-a", help="Append as JSONL instead of overwriting"),
) -> None:
    """Write a value to shared memory."""
    import json

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON:[/red] {exc}")
        raise typer.Exit(1)

    try:
        path = _resolve_path(layer, category, key)
    except MemoryError as exc:
        console.print(f"[red]{exc.message}[/red]")
        raise typer.Exit(1)

    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if append:
            append_jsonl(path.with_suffix(".jsonl"), parsed)
            console.print(f"[green]✓ Appended to[/green] {layer}/{category}/{key}.jsonl")
        else:
            with lock_file(path):
                atomic_write_json(path, parsed)
            console.print(f"[green]✓ Written[/green] {layer}/{category}/{key}.json")
    except Exception as exc:
        console.print(f"[red]Write failed:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def list_layers() -> None:
    """Show the 4-layer memory architecture with statistics."""
    table = Table(
        title="🧠 PicoCloth Shared Memory Architecture",
        title_style="bold cyan",
        header_style="bold magenta",
    )
    table.add_column("Layer", style="bold")
    table.add_column("Path", style="dim")
    table.add_column("Files", justify="right")
    table.add_column("Size", justify="right")

    for name, path in MEMORY_LAYERS.items():
        if not path.exists():
            table.add_row(name, str(path), "—", "—")
            continue
        files = list(path.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        size_str = f"{total_size / 1024:.1f} KB" if total_size < 1024 * 1024 else f"{total_size / 1024 / 1024:.1f} MB"
        table.add_row(name, str(path), str(file_count), size_str)

    console.print(table)
    console.print("\n[dim]Citation: Graph Digital 4-layer memory architecture[/dim]")
