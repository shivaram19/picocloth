"""
Interactive REPL for PicoCloth-CLI chat mode.

Provides Rich markdown rendering, streaming output, meta-commands,
and session persistence.

Citation: Claude Code queryLoop() pattern (arXiv:2604.14228v1)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import CLI_SESSIONS_DIR, NODE_ROLES, NODES
from picocloth_cli.core.logging import get_logger
from picocloth_cli.utils.files import append_jsonl

logger = get_logger(__name__)
console = Console()


class ChatREPL:
    """Interactive chat REPL with session management."""

    def __init__(self, default_node: str = "node-a", session_id: str | None = None) -> None:
        if default_node not in NODES:
            raise ValueError(f"Unknown node: {default_node}")
        self.default_node = default_node
        self.session_id = session_id or f"session-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self.session_file = CLI_SESSIONS_DIR / f"{self.session_id}.jsonl"
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.turn_count = 0

    def print_header(self) -> None:
        role = NODE_ROLES.get(self.default_node, "unknown").replace("_", " ").title()
        console.print(Panel(
            f"[bold cyan]PicoCloth Chat[/bold cyan]\n"
            f"Session: [dim]{self.session_id}[/dim]  |  Node: [green]{self.default_node}[/green] ({role})\n"
            f"Type [bold]/help[/bold] for commands, [bold]/quit[/bold] to exit",
            title="🪶",
            border_style="cyan",
        ))

    def run(self) -> None:
        self.print_header()
        while True:
            try:
                user_input = Prompt.ask("\n[bold green]you[/bold green]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Goodbye.[/dim]")
                break

            if not user_input.strip():
                continue

            self._log_turn("user", user_input)

            if user_input.startswith("/"):
                result = self._handle_meta(user_input)
                if result == "quit":
                    break
                continue

            response = self._process_message(user_input)
            console.print(f"\n[bold blue]fleet[/bold blue]")
            console.print(Markdown(response))
            self._log_turn("assistant", response)
            self.turn_count += 1

    def _process_message(self, text: str) -> str:
        """Process a user message and return a response."""
        import asyncio
        from picocloth_cli.intent.engine import IntentEngine

        engine = IntentEngine(default_node=self.default_node)
        try:
            result = engine.resolve(text)
            return result.message
        except Exception as exc:
            logger.error("Message processing failed", extra={"error": str(exc)})
            return f"I encountered an error: {exc}"

    def _handle_meta(self, cmd: str) -> str | None:
        """Handle meta-commands. Returns 'quit' to exit."""
        parts = cmd.strip().split()
        command = parts[0].lower()

        if command in ("/quit", "/exit", "/q"):
            console.print("[dim]Session saved. Goodbye.[/dim]")
            return "quit"

        if command == "/help":
            console.print(Panel(
                "[bold]/status[/bold]          Show fleet status\n"
                "[bold]/switch <node>[/bold]    Change default node\n"
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
                self.default_node = new_node
                role = NODE_ROLES.get(new_node, "unknown").replace("_", " ").title()
                console.print(f"[green]Switched to {new_node} ({role})[/green]")
            else:
                console.print(f"[red]Unknown node: {new_node}[/red]")
            return None

        if command == "/session":
            console.print(f"Session: [dim]{self.session_id}[/dim]")
            console.print(f"Node: [green]{self.default_node}[/green]")
            console.print(f"Turns: {self.turn_count}")
            return None

        if command == "/clear":
            console.clear()
            return None

        console.print(f"[yellow]Unknown: {command}. Type /help for commands.[/yellow]")
        return None

    def _log_turn(self, role: str, content: str) -> None:
        append_jsonl(self.session_file, {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn": self.turn_count,
        })
