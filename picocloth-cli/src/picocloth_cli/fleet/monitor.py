"""
Textual TUI dashboard for real-time fleet monitoring.

Provides live widgets for:
- Node Health Grid: status, memory, active turns per node
- Task Queue: pending/running/completed with progress
- Event Stream: real-time fleet events
- Memory Usage: 4-layer memory visualization

Citation: Textual reactive widget pattern (github.com/Textualize/textual)
Citation: Rich for live display components
"""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Log, Static

from picocloth_cli.core.constants import NODE_PORTS, NODE_ROLES, NODES
from picocloth_cli.core.logging import get_logger
from picocloth_cli.fleet.launcher import get_fleet_status
from picocloth_cli.fleet.state import get_pending_tasks, get_running_tasks, get_task_queue

logger = get_logger(__name__)


class NodeGrid(Static):
    """Widget displaying node health as a grid."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="node_table")

    def on_mount(self) -> None:
        table = self.query_one("#node_table", DataTable)
        table.add_columns("Node", "Role", "Port", "Status", "PID", "Memory")
        table.cursor_type = "row"
        self.refresh_nodes()

    def refresh_nodes(self) -> None:
        table = self.query_one("#node_table", DataTable)
        table.clear()
        statuses = get_fleet_status()
        for node in NODES:
            info = statuses[node]
            role = NODE_ROLES.get(node, "unknown").replace("_", " ").title()
            status = info["status"]
            status_style = {
                "online": "✓ green",
                "starting": "◐ yellow",
                "dead": "✖ red",
                "offline": "○ dim",
            }.get(status, "? white")
            mem = f"{info.get('memory_mb', 0):.1f} MB" if info.get("memory_mb") else "—"
            table.add_row(
                node,
                role,
                str(info["port"]),
                status_style,
                info.get("pid") or "—",
                mem,
            )


class TaskQueueWidget(Static):
    """Widget displaying the task queue."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="task_table")

    def on_mount(self) -> None:
        table = self.query_one("#task_table", DataTable)
        table.add_columns("ID", "Target", "Task", "Priority", "Status")
        table.cursor_type = "row"
        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        table = self.query_one("#task_table", DataTable)
        table.clear()
        tasks = get_task_queue()[-20:]  # Show last 20
        for t in tasks:
            status_style = {
                "pending": "⏳ yellow",
                "running": "🔄 blue",
                "completed": "✅ green",
                "failed": "❌ red",
                "cancelled": "🚫 dim",
            }.get(t.get("status", ""), "? white")
            table.add_row(
                t["id"][-12:],
                t["target_node"],
                t["task"][:30] + "..." if len(t["task"]) > 30 else t["task"],
                t.get("priority", "normal"),
                status_style,
            )


class EventLogWidget(Log):
    """Widget displaying real-time fleet events."""

    def on_mount(self) -> None:
        self.write_line("[dim]Fleet event monitor started...[/dim]")

    def log_event(self, message: str) -> None:
        self.write_line(message)


class MemoryWidget(Static):
    """Widget displaying 4-layer memory usage."""

    def compose(self) -> ComposeResult:
        yield Static(id="memory_display")

    def on_mount(self) -> None:
        self.refresh_memory()

    def refresh_memory(self) -> None:
        from pathlib import Path
        from picocloth_cli.core.constants import (
            COMPACTION_ARCHIVE_DIR,
            DIGITAL_TWINS_DIR,
            DOCTRINE_DIR,
            PROJECT_DIR,
            RUN_DIR,
            SHARED_DIR,
            STATE_DIR,
        )

        lines = ["[bold]Shared Memory Layers[/bold]\n"]
        layers = [
            ("Doctrine", DOCTRINE_DIR),
            ("Project", PROJECT_DIR),
            ("State", STATE_DIR),
            ("Run", RUN_DIR),
            ("Digital Twins", DIGITAL_TWINS_DIR),
            ("Compaction", COMPACTION_ARCHIVE_DIR),
        ]

        for name, path in layers:
            if path.exists():
                files = list(path.rglob("*"))
                file_count = sum(1 for f in files if f.is_file())
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                size_str = f"{total_size / 1024:.1f} KB" if total_size < 1024 * 1024 else f"{total_size / 1024 / 1024:.1f} MB"
                lines.append(f"  {name:20} {file_count:>6} files  {size_str:>12}")
            else:
                lines.append(f"  {name:20} —")

        display = self.query_one("#memory_display", Static)
        display.update("\n".join(lines))


class FleetMonitorApp(App):
    """Textual TUI application for fleet monitoring."""

    CSS = """
    Screen { align: center middle; }
    #node_table { height: 40%; }
    #task_table { height: 30%; }
    #memory_display { height: 30%; padding: 1; }
    Log { height: 100%; border: solid green; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._refresh_count = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical():
                yield Static("[bold cyan]🪶 PicoCloth Fleet Monitor[/bold cyan]")
                yield NodeGrid()
                yield TaskQueueWidget()
                yield MemoryWidget()
            yield EventLogWidget()
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(5.0, self.action_refresh)
        self.query_one(EventLogWidget).log_event("Monitor initialized. Press 'r' to refresh, 'q' to quit.")

    def action_refresh(self) -> None:
        self._refresh_count += 1
        self.query_one(NodeGrid).refresh_nodes()
        self.query_one(TaskQueueWidget).refresh_tasks()
        self.query_one(MemoryWidget).refresh_memory()
        self.query_one(EventLogWidget).log_event(f"Refreshed ({self._refresh_count})")


# Entry point for the command
def run_monitor() -> None:
    """Run the Textual fleet monitor TUI."""
    app = FleetMonitorApp()
    app.run()
