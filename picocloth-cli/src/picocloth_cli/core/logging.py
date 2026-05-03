"""
Structured logging setup for PicoCloth-CLI.

Provides both Rich-formatted console output (for human interaction) and
JSON-structured file output (for Langfuse observability integration).

Citation: Langfuse open-source LLM observability (github.com/langfuse/langfuse)
Citation: Rich library for terminal formatting (github.com/Textualize/rich)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_tracebacks

from picocloth_cli.core.config import get_config

# Install Rich tracebacks globally for beautiful error displays
install_rich_tracebacks(show_locals=True)

# Console for Rich output — stderr to keep stdout clean for piping
CONSOLE = Console(stderr=True)


def _json_formatter(record: logging.LogRecord) -> str:
    """Format a log record as a JSON line for structured logging."""
    payload: dict[str, Any] = {
        "timestamp": record.created,
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
        "module": record.module,
        "function": record.funcName,
        "line": record.lineno,
    }
    if hasattr(record, "extra"):
        payload.update(record.extra)
    if record.exc_info:
        payload["exception"] = logging.Formatter().formatException(record.exc_info)
    return json.dumps(payload, default=str)


class JSONLineHandler(logging.Handler):
    """Custom handler emitting JSON Lines format for Langfuse ingestion."""

    def __init__(self, filepath: Path) -> None:
        super().__init__()
        self.filepath = filepath
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(_json_formatter(record) + "\n")
        except Exception:
            self.handleError(record)


def setup_logging(
    *,
    level: str | None = None,
    fmt: str | None = None,
    file_enabled: bool | None = None,
    file_path: Path | None = None,
) -> logging.Logger:
    """Configure root logger for PicoCloth-CLI.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
        fmt: Output format — "rich" (colorful console), "json" (structured file),
             or "plain" (simple text).
        file_enabled: Whether to write JSON logs to file.
        file_path: Path for JSON log file.

    Returns:
        The configured root logger.
    """
    config = get_config()
    log_cfg = config.logging

    effective_level = (level or log_cfg.level).upper()
    effective_fmt = fmt or log_cfg.format
    effective_file = file_enabled if file_enabled is not None else log_cfg.file_enabled
    effective_path = file_path or log_cfg.file_path

    logger = logging.getLogger("picocloth_cli")
    logger.setLevel(effective_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if logger.handlers:
        logger.handlers.clear()

    # ---- Console handler (Rich) ----
    if effective_fmt == "rich":
        console_handler = RichHandler(
            console=CONSOLE,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            show_time=True,
            show_path=False,
        )
        console_handler.setLevel(effective_level)
        console_handler.setFormatter(
            logging.Formatter("%(message)s", datefmt="[%X]")
        )
        logger.addHandler(console_handler)
    elif effective_fmt == "plain":
        plain_handler = logging.StreamHandler(sys.stderr)
        plain_handler.setLevel(effective_level)
        plain_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(plain_handler)

    # ---- File handler (JSON Lines) ----
    if effective_file:
        json_handler = JSONLineHandler(effective_path)
        json_handler.setLevel(logging.DEBUG)  # Always capture everything in file
        logger.addHandler(json_handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a namespaced logger under the picocloth_cli hierarchy.

    Usage:
        log = get_logger(__name__)
        log.info("Fleet launched", extra={"nodes": 10})
    """
    full_name = "picocloth_cli"
    if name:
        # Strip the package prefix to avoid double-nesting
        relative = name.removeprefix("picocloth_cli.")
        if relative:
            full_name = f"picocloth_cli.{relative}"
    return logging.getLogger(full_name)
