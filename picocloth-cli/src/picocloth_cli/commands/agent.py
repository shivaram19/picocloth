"""
Agent spawning and lifecycle commands.

Provides direct control over agent spawning, registry inspection, and
termination. Complements the automatic intent-driven spawning with
explicit user control.

Citation: AgentSpawn spawn package spec (arXiv:2602.07072v1)
Citation: Microsoft Agent Framework 1.0 checkpointing pattern
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from picocloth_cli.core.constants import NODES, STATE_DIR
from picocloth_cli.core.exceptions import AgentError
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import atomic_write_json, lock_file, read_json_safe

logger = get_logger(__name__)
app = typer.Typer(help="Agent spawning and lifecycle management")
console = Console()

AGENT_REGISTRY_PATH = STATE_DIR / "agent-registry.json"


def _get_registry() -> dict:
    """Read the agent registry from shared state."""
    return read_json_safe(AGENT_REGISTRY_PATH, default={"agents": [], "version": "1.0"})


def _save_registry(registry: dict) -> None:
    """Write the agent registry atomically."""
    with lock_file(AGENT_REGISTRY_PATH):
        atomic_write_json(AGENT_REGISTRY_PATH, registry)


@app.command()
def spawn(
    target: str = typer.Argument(..., help="Target node for the agent"),
    goal: str = typer.Argument(..., help="Agent's goal / task description"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Optional agent name"),  # noqa: UP007
    parent: Optional[str] = typer.Option(None, "--parent", "-p", help="Parent agent ID for nested spawning"),  # noqa: UP007
    depth: int = typer.Option(0, "--depth", "-d", help="Spawn depth level"),
) -> None:
    """Spawn a new intent-driven agent on a fleet node.

    Creates a spawn package with goal, context, and registry entry.
    """
    if target not in NODES:
        console.print(f"[red]Unknown node: {target}[/red]")
        raise typer.Exit(1)

    agent_id = f"agent-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{hash(goal) % 10000:04d}"
    if name:
        agent_id = f"{name}-{agent_id}"

    registry = _get_registry()

    # Check max spawn depth
    if depth >= 3:
        console.print(f"[red]Maximum spawn depth (3) exceeded.[/red]")
        raise typer.Exit(1)

    agent_entry = {
        "id": agent_id,
        "node": target,
        "goal": goal,
        "status": "spawning",
        "parent_id": parent,
        "spawn_depth": depth,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    registry["agents"].append(agent_entry)
    _save_registry(registry)

    # Create spawn package in node's workspace
    workspace = Path(f"node-{target[-1]}") / "workspace" / "agents"
    workspace.mkdir(parents=True, exist_ok=True)
    package_path = workspace / f"{agent_id}.json"
    package = {
        "spawn_id": agent_id,
        "parent_id": parent,
        "node": target,
        "goal": goal,
        "spawn_depth": depth,
        "created_at": agent_entry["created_at"],
        "memory_slice": {
            "episodic": [],
            "semantic": [],
            "working": [],
        },
        "skills": [],
        "execution_context": {
            "cwd": str(workspace),
            "env": {},
        },
    }
    atomic_write_json(package_path, package)

    console.print(f"[green]✓ Agent spawned[/green]")
    console.print(f"  ID: [bold]{agent_id}[/bold]")
    console.print(f"  Node: [cyan]{target}[/cyan]")
    console.print(f"  Goal: {goal[:60]}")
    if parent:
        console.print(f"  Parent: [dim]{parent}[/dim]")
    console.print(f"  Depth: {depth}")


@app.command()
def list(
    status_filter: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),  # noqa: UP007
    node_filter: Optional[str] = typer.Option(None, "--node", "-n", help="Filter by node"),  # noqa: UP007
) -> None:
    """List all registered agents."""
    registry = _get_registry()
    agents = registry.get("agents", [])

    if status_filter:
        agents = [a for a in agents if a.get("status") == status_filter]
    if node_filter:
        agents = [a for a in agents if a.get("node") == node_filter]

    if not agents:
        console.print("[dim]No agents found.[/dim]")
        return

    table = Table(
        title="🤖 Agent Registry",
        title_style="bold cyan",
        header_style="bold magenta",
    )
    table.add_column("ID", style="dim", max_width=30)
    table.add_column("Node")
    table.add_column("Status")
    table.add_column("Depth", justify="right")
    table.add_column("Goal", max_width=40)
    table.add_column("Created")

    for a in agents[-50:]:  # Show last 50
        status_color = {
            "spawning": "yellow",
            "running": "blue",
            "completed": "green",
            "failed": "red",
            "killed": "red",
        }.get(a.get("status", ""), "white")

        table.add_row(
            a["id"],
            a.get("node", "?"),
            f"[{status_color}]{a.get('status', '?')}[/{status_color}]",
            str(a.get("spawn_depth", 0)),
            a.get("goal", "")[:40],
            a.get("created_at", "")[11:16],
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(agents)} agent(s)[/dim]")


@app.command()
def show(
    agent_id: str = typer.Argument(..., help="Agent ID to inspect"),
) -> None:
    """Show detailed information about an agent."""
    registry = _get_registry()
    for a in registry.get("agents", []):
        if a["id"] == agent_id or a["id"].endswith(agent_id):
            console.print(f"[bold]Agent:[/bold] {a['id']}")
            console.print(f"  Node: {a.get('node', '?')}")
            console.print(f"  Status: {a.get('status', '?')}")
            console.print(f"  Goal: {a.get('goal', '?')}")
            console.print(f"  Depth: {a.get('spawn_depth', 0)}")
            console.print(f"  Parent: {a.get('parent_id', 'none')}")
            console.print(f"  Created: {a.get('created_at', '?')}")
            console.print(f"  Updated: {a.get('updated_at', '?')}")
            if a.get("result"):
                console.print(f"  Result: {a['result']}")
            return
    console.print(f"[yellow]Agent not found: {agent_id}[/yellow]")


@app.command()
def kill(
    agent_id: str = typer.Argument(..., help="Agent ID to terminate"),
) -> None:
    """Terminate a running agent."""
    registry = _get_registry()
    found = False
    for a in registry.get("agents", []):
        if a["id"] == agent_id or a["id"].endswith(agent_id):
            a["status"] = "killed"
            a["updated_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break

    if found:
        _save_registry(registry)
        console.print(f"[yellow]✓ Agent killed:[/yellow] {agent_id}")
    else:
        console.print(f"[yellow]Agent not found: {agent_id}[/yellow]")


@app.command()
def tree() -> None:
    """Show agent hierarchy as a tree."""
    registry = _get_registry()
    agents = registry.get("agents", [])

    if not agents:
        console.print("[dim]No agents to display.[/dim]")
        return

    # Build parent -> children mapping
    roots = []
    children = {}
    for a in agents:
        pid = a.get("parent_id")
        if pid:
            children.setdefault(pid, []).append(a)
        else:
            roots.append(a)

    def build_tree(agent, tree_node):
        node_label = f"[bold]{agent['id']}[/bold] ([cyan]{agent.get('node', '?')}[/cyan]) — {agent.get('status', '?')}"
        branch = tree_node.add(node_label)
        for child in children.get(agent["id"], []):
            build_tree(child, branch)

    root_tree = Tree("[bold]Agent Hierarchy[/bold]")
    for r in roots:
        build_tree(r, root_tree)

    console.print(root_tree)
