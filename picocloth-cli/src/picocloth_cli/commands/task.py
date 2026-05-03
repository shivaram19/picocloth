"""
Task delegation and tracking commands.

Provides explicit task management for users who prefer direct commands
over natural language delegation.

Citation: agent-fleet poll-based task queue (github.com/Luxuzhou/agent-fleet)
"""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from picocloth_cli.core.constants import NODES
from picocloth_cli.core.exceptions import FleetError
from picocloth_cli.core.logging import get_logger
from picocloth_cli.fleet.client import MCPFleetClient
from picocloth_cli.fleet.state import (
    append_task,
    get_completed_tasks,
    get_pending_tasks,
    get_running_tasks,
    get_task_queue,
    update_task_status,
)

logger = get_logger(__name__)
app = typer.Typer(help="Task delegation and tracking")
console = Console()


@app.command()
def spawn(
    target: str = typer.Argument(..., help="Target node ID, e.g., node-b"),
    task: str = typer.Argument(..., help="Task description"),
    priority: str = typer.Option("normal", "--priority", "-p", help="Priority: low, normal, high, critical"),
) -> None:
    """Spawn a new task on a fleet node."""
    if target not in NODES:
        console.print(f"[red]Unknown node: {target}[/red]")
        raise typer.Exit(1)

    try:
        result = append_task(target, task, priority=priority)
        console.print(f"[green]✓ Task spawned[/green]")
        console.print(f"  ID: [dim]{result['id']}[/dim]")
        console.print(f"  Target: [cyan]{target}[/cyan]")
        console.print(f"  Priority: [yellow]{priority}[/yellow]")
    except Exception as exc:
        console.print(f"[red]Failed to spawn task:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def status(
    task_id: Optional[str] = typer.Option(None, "--id", "-i", help="Check specific task ID"),  # noqa: UP007
) -> None:
    """Show task queue status."""
    if task_id:
        queue = get_task_queue()
        for t in queue:
            if t.get("id") == task_id or t.get("id", "").endswith(task_id):
                console.print(f"[bold]Task:[/bold] {t['id']}")
                console.print(f"  Target: {t['target_node']}")
                console.print(f"  Status: [{_status_color(t['status'])}]{t['status']}[/{_status_color(t['status'])}]")
                console.print(f"  Priority: {t.get('priority', 'normal')}")
                console.print(f"  Created: {t.get('created_at', 'unknown')}")
                if t.get("result"):
                    console.print(f"  Result: {t['result']}")
                return
        console.print(f"[yellow]Task not found: {task_id}[/yellow]")
        return

    pending = get_pending_tasks()
    running = get_running_tasks()
    completed = get_completed_tasks(limit=5)

    console.print(f"[bold]Task Queue Summary[/bold]")
    console.print(f"  ⏳ Pending:   [yellow]{len(pending)}[/yellow]")
    console.print(f"  🔄 Running:   [blue]{len(running)}[/blue]")
    console.print(f"  ✅ Completed: [green]{len(get_completed_tasks(limit=0))}[/green]")

    if pending:
        console.print("\n[bold]Pending Tasks:[/bold]")
        for t in pending[:5]:
            console.print(f"  • [{t['target_node']}] {t['task'][:50]}")


def _status_color(status: str) -> str:
    return {
        "pending": "yellow",
        "running": "blue",
        "completed": "green",
        "failed": "red",
    }.get(status, "white")


@app.command()
def complete(
    task_id: str = typer.Argument(..., help="Task ID to mark as completed"),
    result: Optional[str] = typer.Option(None, "--result", "-r", help="Optional result text"),  # noqa: UP007
) -> None:
    """Manually mark a task as completed."""
    updated = update_task_status(task_id, "completed", result=result)
    if updated:
        console.print(f"[green]✓ Task marked completed:[/green] {task_id}")
    else:
        console.print(f"[yellow]Task not found: {task_id}[/yellow]")


@app.command()
def cancel(
    task_id: str = typer.Argument(..., help="Task ID to cancel"),
) -> None:
    """Cancel a pending task."""
    updated = update_task_status(task_id, "cancelled")
    if updated:
        console.print(f"[yellow]✓ Task cancelled:[/yellow] {task_id}")
    else:
        console.print(f"[yellow]Task not found or not pending: {task_id}[/yellow]")
