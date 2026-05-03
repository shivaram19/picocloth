"""
Interactive chat command for PicoCloth-CLI.

Provides a REPL with Rich markdown rendering, streaming output, and
meta-commands. Sessions are persisted for continuity.

Citation: Claude Code queryLoop() pattern (arXiv:2604.14228v1)
Citation: Rich for markdown rendering and live display
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import CLI_SESSIONS_DIR, NODE_ROLES, NODES
from picocloth_cli.core.exceptions import FleetError
from picocloth_cli.core.logging import get_logger
from picocloth_cli.fleet.client import MCPFleetClient
from picocloth_cli.intent.classifier import classify_intent
from picocloth_cli.intent.engine import resolve_intent
from picocloth_cli.utils.files import append_jsonl

logger = get_logger(__name__)
app = typer.Typer(help="Interactive chat with the PicoCloth fleet")
console = Console()


@app.command()
def interactive(
    node: Optional[str] = typer.Option(  # noqa: UP007
        "node-a",
        "--node",
        "-n",
        help="Default node to chat with",
    ),
    session: Optional[str] = typer.Option(  # noqa: UP007
        None,
        "--session",
        "-s",
        help="Resume a previous session ID",
    ),
) -> None:
    """Start an interactive chat session with the fleet.

    Supports natural language commands, meta-commands prefixed with '/',
    and automatic intent classification for delegation.
    """
    if node not in NODES:
        console.print(f"[red]Unknown node: {node}[/red]")
        raise typer.Exit(1)

    session_id = session or f"session-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    session_file = CLI_SESSIONS_DIR / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True, exist_ok=True)

    # Header
    role = NODE_ROLES.get(node, "unknown").replace("_", " ").title()
    console.print(Panel(
        f"[bold cyan]PicoCloth Chat[/bold cyan]\n"
        f"Session: [dim]{session_id}[/dim]  |  Default node: [green]{node}[/green] ({role})\n"
        f"Type [bold]/help[/bold] for commands, [bold]/quit[/bold] to exit",
        title="🪶",
        border_style="cyan",
    ))

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]you[/bold green]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input.strip():
            continue

        # Log user message
        append_jsonl(session_file, {
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Meta-commands
        if user_input.startswith("/"):
            handled = _handle_meta_command(user_input, session_id, node)
            if handled == "quit":
                break
            continue

        # Intent classification & resolution
        with Status("[dim]Thinking...[/dim]", spinner="dots"):
            intent = classify_intent(user_input)
            logger.debug("Intent classified", extra={
                "intent": intent.intent_type,
                "confidence": intent.confidence,
                "session": session_id,
            })

        try:
            response = asyncio.run(_execute_intent(intent, default_node=node))
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            response = f"Sorry, I encountered an error: {exc}"

        # Display response
        console.print(f"\n[bold blue]fleet[/bold blue]")
        console.print(Markdown(response))

        # Log assistant message
        append_jsonl(session_file, {
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": intent.intent_type,
        })


def _handle_meta_command(cmd: str, session_id: str, default_node: str) -> str | None:
    """Handle a /-prefixed meta-command. Returns 'quit' to exit loop."""
    parts = cmd.strip().split()
    command = parts[0].lower()

    if command in ("/quit", "/exit", "/q"):
        console.print("[dim]Session saved. Goodbye.[/dim]")
        return "quit"

    if command == "/help":
        console.print(Panel(
            "[bold]/status[/bold]          Show fleet status\n"
            "[bold]/switch <node>[/bold]    Change default node\n"
            "[bold]/spawn <node> <task>[/bold] Delegate task to node\n"
            "[bold]/memory <query>[/bold]   Search shared memory\n"
            "[bold]/twin <query>[/bold]     Search digital twins\n"
            "[bold]/session[/bold]        Show session info\n"
            "[bold]/clear[/bold]          Clear screen\n"
            "[bold]/quit[/bold]           Exit chat",
            title="Commands",
            border_style="dim",
        ))
        return None

    if command == "/status":
        from picocloth_cli.commands.fleet import status as fleet_status
        fleet_status()
        return None

    if command == "/switch" and len(parts) > 1:
        new_node = parts[1]
        if new_node in NODES:
            role = NODE_ROLES.get(new_node, "unknown").replace("_", " ").title()
            console.print(f"[green]Switched to {new_node} ({role})[/green]")
        else:
            console.print(f"[red]Unknown node: {new_node}[/red]")
        return None

    if command == "/spawn" and len(parts) >= 3:
        target = parts[1]
        task = " ".join(parts[2:])
        if target not in NODES:
            console.print(f"[red]Unknown node: {target}[/red]")
            return None
        try:
            result = asyncio.run(_spawn_task(target, task))
            console.print(f"[green]✓ Task spawned:[/green] {result.get('task_id', 'unknown')}")
        except Exception as exc:
            console.print(f"[red]Spawn failed:[/red] {exc}")
        return None

    if command == "/session":
        console.print(f"Session ID: [dim]{session_id}[/dim]")
        console.print(f"Default node: [green]{default_node}[/green]")
        return None

    if command == "/clear":
        console.clear()
        return None

    console.print(f"[yellow]Unknown command: {command}. Type /help for available commands.[/yellow]")
    return None


async def _execute_intent(intent, default_node: str) -> str:
    """Execute a classified intent and return a response string."""
    from picocloth_cli.intent.engine import IntentType

    if intent.intent_type == IntentType.ORCHESTRATE:
        # Fleet management — show status
        from picocloth_cli.fleet.state import get_fleet_state
        state = get_fleet_state()
        nodes = state.get("nodes", {})
        online = sum(1 for n in nodes.values() if n.get("status") == "online")
        return f"Fleet status: {online}/{len(NODES)} nodes online."

    elif intent.intent_type == IntentType.DELEGATE:
        # Delegate to a specific node
        target = intent.parameters.get("target_node", default_node)
        task = intent.parameters.get("task", intent.raw_input)
        result = await _spawn_task(target, task)
        return f"Delegated to {target}: task `{result.get('task_id')}` queued."

    elif intent.intent_type == IntentType.QUERY:
        # Search memory or twins
        query = intent.parameters.get("query", intent.raw_input)
        async with MCPFleetClient() as client:
            try:
                mem_result = await client.memory_read("facts", "auto_extracted")
                if mem_result.get("found"):
                    return f"Found facts related to '{query}'."
            except FleetError:
                pass
            try:
                twin_result = await client.digital_twin_search(query=query, limit=3)
                count = twin_result.get("count", 0)
                return f"Found {count} digital twin(s) matching '{query}'."
            except FleetError:
                pass
        return f"No results found for '{query}'."

    elif intent.intent_type == IntentType.CHAT:
        # Free-form chat — send to default node gateway
        try:
            from picocloth_cli.utils.http import node_post
            result = await node_post(default_node, "/", {"message": intent.raw_input})
            return result.get("response", "(no response)")
        except Exception as exc:
            return f"I'm not able to reach {default_node} right now. Error: {exc}"

    else:
        return f"Intent `{intent.intent_type}` recognized but not yet implemented in chat mode."


async def _spawn_task(target_node: str, task: str) -> dict:
    """Spawn a task via the MCP fleet client."""
    async with MCPFleetClient() as client:
        return await client.spawn_task(target_node, task)
