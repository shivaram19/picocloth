"""
Fleet launcher / stopper.

Delegates to the existing ram-optimized-launch.py script for node
management, providing a Pythonic wrapper with Rich output and error
handling.

Citation: PicoCloth ram-optimized-launch.py (existing project infrastructure)
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import NODES, PICOCLOTH_DIR
from picocloth_cli.core.exceptions import FleetError
from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)

LAUNCHER_SCRIPT = PICOCLOTH_DIR / "scripts" / "ram-optimized-launch.py"


def _run_script(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a launcher script command and capture output."""
    try:
        return subprocess.run(
            ["python3", str(LAUNCHER_SCRIPT)] + cmd,
            cwd=str(PICOCLOTH_DIR),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise FleetError(f"Launcher script not found: {LAUNCHER_SCRIPT}") from exc


def launch_fleet() -> dict[str, Any]:
    """Launch the full 10-node RAM-optimized fleet.

    Returns:
        Result dict with stdout, stderr, and returncode.
    """
    logger.info("Launching fleet via ram-optimized-launch.py")
    result = _run_script(["launch"])
    if result.returncode != 0:
        raise FleetError(f"Fleet launch failed: {result.stderr}")
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def stop_fleet() -> dict[str, Any]:
    """Stop all running picoclaw processes.

    Returns:
        Result dict with stdout, stderr, and returncode.
    """
    logger.info("Stopping fleet via ram-optimized-launch.py")
    result = _run_script(["stop"])
    # Also force-kill any stragglers
    subprocess.run(["pkill", "-9", "-f", "picoclaw gateway"], capture_output=True)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def get_fleet_status() -> dict[str, dict[str, Any]]:
    """Check status of all nodes by reading PID files and /proc.

    Returns:
        Dict mapping node_id -> status dict with keys: status, pid, port, memory_mb
    """
    from picocloth_cli.core.constants import NODE_PORTS

    statuses: dict[str, dict[str, Any]] = {}
    for i, node in enumerate(NODES):
        port = NODE_PORTS[i]
        pid_file = PICOCLOTH_DIR / node / "pid"
        status = {"node": node, "port": port, "status": "offline", "pid": None, "memory_mb": 0.0}

        if pid_file.exists():
            pid_str = pid_file.read_text().strip()
            status["pid"] = pid_str
            proc_dir = Path(f"/proc/{pid_str}")
            if proc_dir.exists():
                try:
                    # Read RSS from statm
                    statm = (proc_dir / "statm").read_text().split()
                    rss_pages = int(statm[1])
                    status["memory_mb"] = rss_pages * 4096 / 1024 / 1024
                    status["status"] = "online"
                except (OSError, ValueError, IndexError):
                    status["status"] = "unknown"
            else:
                status["status"] = "dead"

        statuses[node] = status

    return statuses


async def async_launch_fleet() -> dict[str, Any]:
    """Async wrapper for launch_fleet with progress display."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, launch_fleet)


async def async_stop_fleet() -> dict[str, Any]:
    """Async wrapper for stop_fleet."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, stop_fleet)
