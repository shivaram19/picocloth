"""
CLI configuration management commands.

Provides get/set operations for ~/.picocloth/config.yaml with
validation and type safety via Pydantic.

Citation: Pydantic Settings pattern (pydantic-settings docs)
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel

from picocloth_cli.core.config import CLIConfig, get_config, load_config, reload_config, save_config
from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)
app = typer.Typer(help="CLI configuration management")
console = Console()


def _get_nested(config: CLIConfig, key: str) -> any:
    """Get a nested config value by dot-notation key."""
    parts = key.split(".")
    current = config
    for part in parts:
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _set_nested(config: CLIConfig, key: str, value: str) -> None:
    """Set a nested config value by dot-notation key."""
    import json

    parts = key.split(".")
    current = config
    for part in parts[:-1]:
        current = getattr(current, part)

    target_key = parts[-1]
    current_val = getattr(current, target_key, None)

    # Try to preserve type
    if current_val is not None:
        if isinstance(current_val, bool):
            parsed = value.lower() in ("true", "1", "yes", "on")
        elif isinstance(current_val, int):
            parsed = int(value)
        elif isinstance(current_val, float):
            parsed = float(value)
        else:
            parsed = value
    else:
        # Try JSON parsing as fallback
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value

    setattr(current, target_key, parsed)


@app.command()
def get(
    key: Optional[str] = typer.Argument(None, help="Config key in dot notation, e.g., fleet.transport"),  # noqa: UP007
) -> None:
    """Show configuration value(s)."""
    config = get_config()

    if key:
        value = _get_nested(config, key)
        if value is None:
            console.print(f"[yellow]Key not found: {key}[/yellow]")
            raise typer.Exit(1)
        console.print(Panel(
            JSON.from_data(value),
            title=f"config.{key}",
            border_style="cyan",
        ))
    else:
        # Show full config
        console.print(Panel(
            JSON.from_data(config.model_dump(mode="json")),
            title="PicoCloth-CLI Configuration",
            border_style="cyan",
        ))
        console.print(f"\n[dim]Config file: {config.__pydantic_fields_set__}[/dim]")


@app.command()
def set(
    key: str = typer.Argument(..., help="Config key in dot notation"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value."""
    config = get_config()

    try:
        _set_nested(config, key, value)
    except (AttributeError, ValueError) as exc:
        console.print(f"[red]Failed to set {key}:[/red] {exc}")
        raise typer.Exit(1)

    try:
        save_config(config)
        console.print(f"[green]✓ Set[/green] {key} = {value}")
    except Exception as exc:
        console.print(f"[red]Failed to save config:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def reload() -> None:
    """Reload configuration from disk."""
    reload_config()
    console.print("[green]✓ Configuration reloaded[/green]")


@app.command()
def path() -> None:
    """Show the path to the current configuration file."""
    from picocloth_cli.core.constants import CLI_CONFIG_PATH
    console.print(f"[bold]Config path:[/bold] {CLI_CONFIG_PATH}")
