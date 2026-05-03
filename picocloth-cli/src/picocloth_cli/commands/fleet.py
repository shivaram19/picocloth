"""
Fleet management commands for PicoCloth-CLI.

Provides subcommands for launching, stopping, monitoring, and inspecting
the PicoCloth fleet of nodes. Uses Rich for beautiful terminal output.

Citation: Rich for static tables (github.com/Textualize/rich)
Citation: agent-fleet poll-based task queue (github.com/Luxuzhou/agent-fleet)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import NODE_PORTS, NODE_ROLES, NODES
from picocloth_cli.core.exceptions import FleetError
from picocloth_cli.core.logging import get_logger
from picocloth_cli.fleet.launcher import (
    async_launch_fleet,
    async_stop_fleet,
    get_fleet_status,
    launch_fleet,
    stop_fleet,
)
from picocloth_cli.fleet.state import (
    get_completed_tasks,
    get_pending_tasks,
    get_running_tasks,
    get_task_queue,
)

logger = get_logger(__name__)
app = typer.Typer(help="Fleet management commands")
console = Console()


@app.command()
def status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show extra details"),
) -> None:
    """Show fleet status as a Rich table."""
    statuses = get_fleet_status()

    table = Table(
        title="🪶 PicoCloth Fleet Status",
        title_style="bold cyan",
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("Node", style="bold")
    table.add_column("Role", style="dim")
    table.add_column("Port", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("PID", justify="right")
    if verbose:
        table.add_column("Memory", justify="right")

    online = 0
    total_mem = 0.0

    for node in NODES:
        info = statuses[node]
        role = NODE_ROLES.get(node, "unknown")
        role_display = role.replace("_", " ").title()
        port = info["port"]
        status_str = info["status"]
        pid = info.get("pid") or "—"
        mem = info.get("memory_mb", 0.0)

        if status_str == "online":
            status_text = "[green]● online[/green]"
            online += 1
            total_mem += mem
        elif status_str == "starting":
            status_text = "[yellow]◐ starting[/yellow]"
        elif status_str == "dead":
            status_text = "[red]✖ dead[/red]"
        else:
            status_text = "[dim]○ offline[/dim]"

        row = [node, role_display, str(port), status_text, pid]
        if verbose:
            row.append(f"{mem:.1f} MB" if mem > 0 else "—")
        table.add_row(*row)

    console.print(table)
    console.print(f"\n[bold]{online}/{len(NODES)}[/bold] nodes online", end="")
    if total_mem > 0:
        console.print(f"  •  Total memory: [cyan]{total_mem:.1f} MB[/cyan]")
    else:
        console.print()

    # Show pending tasks if any
    pending = get_pending_tasks()
    if pending:
        console.print(f"\n[yellow]⏳ {len(pending)} pending task(s)[/yellow]")
        for t in pending[:5]:
            console.print(f"  • [{t['target_node']}] {t['task'][:60]}")


@app.command()
def launch(
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for nodes to be ready"),
) -> None:
    """Launch the full 10-node RAM-optimized fleet."""
    console.print("[bold blue]🚀 Launching PicoCloth fleet...[/bold blue]")
    try:
        result = launch_fleet()
        console.print(result["stdout"])
        if result["stderr"]:
            console.print(f"[yellow]{result['stderr']}[/yellow]")
    except FleetError as exc:
        console.print(f"[bold red]Launch failed:[/bold red] {exc.message}")
        raise typer.Exit(1)

    if wait:
        console.print("\n[dim]Waiting for nodes to come online...[/dim]")
        import time

        for _ in range(30):
            statuses = get_fleet_status()
            online = sum(1 for s in statuses.values() if s["status"] == "online")
            if online == len(NODES):
                console.print(f"[green]✓ All {len(NODES)} nodes online[/green]")
                return
            time.sleep(1)
        console.print("[yellow]⚠ Timeout waiting for all nodes[/yellow]")


@app.command()
def stop(
    force: bool = typer.Option(False, "--force", "-f", help="Force kill all processes"),
) -> None:
    """Stop all running fleet nodes."""
    console.print("[bold yellow]🛑 Stopping PicoCloth fleet...[/bold yellow]")
    try:
        result = stop_fleet()
        if result["stdout"]:
            console.print(result["stdout"])
        console.print("[green]✓ Fleet stopped[/green]")
    except FleetError as exc:
        console.print(f"[bold red]Stop failed:[/bold red] {exc.message}")
        raise typer.Exit(1)


@app.command()
def logs(
    node: str = typer.Argument(..., help="Node ID, e.g., node-a"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
) -> None:
    """Show node logs with Rich formatting."""
    if node not in NODES:
        console.print(f"[red]Unknown node: {node}[/red]")
        raise typer.Exit(1)

    log_file = Path(PICOCLOTH_DIR) / node / "node.log"
    if not log_file.exists():
        console.print(f"[yellow]No log file found for {node}[/yellow]")
        return

    if follow:
        import subprocess

        console.print(f"[dim]Following {node} logs (Ctrl+C to exit)...[/dim]\n")
        try:
            subprocess.run(["tail", "-f", str(log_file)])
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped.[/dim]")
    else:
        content = log_file.read_text().splitlines()
        shown = content[-lines:] if len(content) > lines else content
        for line in shown:
            # Simple colorization based on log level keywords
            if "ERROR" in line or "error" in line.lower():
                console.print(f"[red]{line}[/red]")
            elif "WARN" in line or "warning" in line.lower():
                console.print(f"[yellow]{line}[/yellow]")
            elif "INFO" in line:
                console.print(f"[cyan]{line}[/cyan]")
            else:
                console.print(line)
        console.print(f"\n[dim]Showing last {len(shown)} lines of {log_file}[/dim]")


@app.command()
def tasks(
    status_filter: Optional[str] = typer.Option(  # noqa: UP007
        None,
        "--status",
        "-s",
        help="Filter by status: pending, running, completed",
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum tasks to show"),
) -> None:
    """Show the fleet task queue."""
    all_tasks = get_task_queue()

    if status_filter == "pending":
        tasks = get_pending_tasks()
    elif status_filter == "running":
        tasks = get_running_tasks()
    elif status_filter == "completed":
        tasks = get_completed_tasks(limit=limit)
    else:
        tasks = all_tasks[-limit:]

    if not tasks:
        console.print("[dim]No tasks in queue.[/dim]")
        return

    table = Table(
        title="📋 Fleet Task Queue",
        title_style="bold cyan",
        header_style="bold magenta",
    )
    table.add_column("ID", style="dim")
    table.add_column("Target")
    table.add_column("Task", max_width=50)
    table.add_column("Priority", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Created", justify="right")

    for t in tasks:
        status_style = {
            "pending": "yellow",
            "running": "blue",
            "completed": "green",
            "failed": "red",
        }.get(t.get("status", ""), "white")

        table.add_row(
            t["id"][-12:],  # Last 12 chars of task ID
            t["target_node"],
            t["task"][:50],
            t.get("priority", "normal"),
            f"[{status_style}]{t['status']}[/{status_style}]",
            t.get("created_at", "")[11:19],  # HH:MM:SS
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(tasks)} of {len(all_tasks)} total tasks[/dim]")


@app.command()
def broadcast(
    message: str = typer.Argument(..., help="Message to broadcast to all nodes"),
) -> None:
    """Broadcast a message to all nodes via the MCP fleet server."""
    import asyncio

    from picocloth_cli.fleet.client import MCPFleetClient

    async def _broadcast() -> None:
        async with MCPFleetClient() as client:
            result = await client.broadcast(message=message, sender="picocloth-cli")
            recipients = result.get("recipients", [])
            console.print(f"[green]✓ Broadcast sent to {len(recipients)} node(s)[/green]")
            for r in recipients:
                console.print(f"  • {r}")

    try:
        asyncio.run(_broadcast())
    except FleetError as exc:
        console.print(f"[red]Broadcast failed:[/red] {exc.message}")
        raise typer.Exit(1)
