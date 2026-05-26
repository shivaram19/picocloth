"""
PicoCloth-CLI main entry point.

Built with Typer for type-hinted, auto-documented command trees.
Every subcommand is backed by research-validated patterns from
2024-2026. See docs/CITATIONS.md for the full bibliography.

Citation: Typer framework (typer.tiangolo.com)
Citation: Anthropic "Building Effective Agents" — simplicity principle
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rich_print

from picocloth_cli import __version__
from picocloth_cli.core.config import load_config
from picocloth_cli.core.constants import PICOCLOTH_DIR
from picocloth_cli.core.logging import setup_logging
from picocloth_cli.utils.citations import CitationRegistry

# Import command modules — they register themselves via app.add_typer
from picocloth_cli.commands import fleet as fleet_cmd
from picocloth_cli.commands import chat as chat_cmd
from picocloth_cli.commands import task as task_cmd
from picocloth_cli.commands import agent as agent_cmd
from picocloth_cli.commands import memory as memory_cmd
from picocloth_cli.commands import twin as twin_cmd
from picocloth_cli.commands import config as config_cmd
from picocloth_cli.commands import extract as extract_cmd

# ---------------------------------------------------------------------------
# Main Typer application
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="picocloth",
    help="PicoCloth-CLI: Research-backed orchestration for the PicoCloth fleet.",
    rich_markup_mode="rich",
    no_args_is_help=True,
    invoke_without_command=True,
)

# Register subcommand groups
app.add_typer(fleet_cmd.app, name="fleet", help="Fleet management: status, launch, stop, monitor")
app.add_typer(chat_cmd.app, name="chat", help="Interactive chat with the fleet")
app.add_typer(task_cmd.app, name="task", help="Task delegation and tracking")
app.add_typer(agent_cmd.app, name="agent", help="Agent spawning and lifecycle")
app.add_typer(memory_cmd.app, name="memory", help="Shared memory layer operations")
app.add_typer(twin_cmd.app, name="twin", help="Digital twin archive queries")
app.add_typer(config_cmd.app, name="config", help="CLI configuration management")
app.add_typer(extract_cmd.app, name="extract", help="Knowledge extraction from search results")


# ---------------------------------------------------------------------------
# Global options & callbacks
# ---------------------------------------------------------------------------

@app.callback()
def main_callback(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error output"),
    config_path: Optional[Path] = typer.Option(  # noqa: UP007
        None,
        "--config",
        "-c",
        help="Path to config YAML file",
        exists=False,
        dir_okay=False,
        resolve_path=True,
    ),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
    citations: bool = typer.Option(False, "--citations", help="Show research bibliography and exit"),
) -> None:
    """PicoCloth-CLI global options."""
    if version:
        rich_print(f"[bold cyan]picocloth-cli[/bold cyan] version [green]{__version__}[/green]")
        rich_print(f"Project root: [dim]{PICOCLOTH_DIR}[/dim]")
        raise typer.Exit()

    if citations:
        rich_print(CitationRegistry.markdown_bibliography())
        raise typer.Exit()

    # Load configuration before any command runs
    load_config(config_path=config_path)

    # Setup logging based on verbosity flags
    level = "DEBUG" if verbose else ("WARNING" if quiet else "INFO")
    fmt = "plain" if quiet else "rich"
    setup_logging(level=level, fmt=fmt)


# ---------------------------------------------------------------------------
# Direct commands (not under a subcommand group)
# ---------------------------------------------------------------------------

@app.command()
def status() -> None:
    """Quick fleet status overview (alias for 'picocloth fleet status')."""
    fleet_cmd.status()


@app.command()
def version() -> None:
    """Show version information."""
    rich_print(f"[bold cyan]picocloth-cli[/bold cyan] version [green]{__version__}[/green]")
    rich_print(f"Project root: [dim]{PICOCLOTH_DIR}[/dim]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
