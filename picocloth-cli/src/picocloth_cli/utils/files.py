"""
File system utilities: lock-file coordination, atomic writes, safe I/O.

All shared memory operations in PicoCloth-CLI use lock-file-based mutual
exclusion rather than a message broker. This trades throughput for zero-
dependency deployment and full debuggability — a deliberate design choice
validated by Claude Code's production architecture.

Citation: Claude Code file-lock coordination (Anthropic, Feb 2026)
Citation: arXiv:2604.14228v1 — "Tasks claimed from shared lists via lock-file-based mutual exclusion"
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from picocloth_cli.core.config import get_config
from picocloth_cli.core.exceptions import LockFileError
from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)


@contextmanager
def lock_file(
    target: Path,
    *,
    timeout: float | None = None,
    poll_interval: float = 0.05,
) -> Generator[None, None, None]:
    """Acquire an advisory lock on a target file using a companion .lock file.

    This is the primary concurrency primitive for all shared memory access
    in PicoCloth-CLI. It guarantees that only one process modifies a given
    file at a time, preventing race conditions without requiring Redis,
    PostgreSQL, or any external service.

    Args:
        target: The file to protect. A {target}.lock companion is created.
        timeout: Maximum seconds to wait for the lock. None = block forever.
        poll_interval: Seconds between lock availability checks.

    Raises:
        LockFileError: If the lock cannot be acquired within the timeout.

    Example:
        with lock_file(path):
            data = json.loads(path.read_text())
            data["counter"] += 1
            path.write_text(json.dumps(data))
    """
    lock_path = target.with_suffix(target.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    effective_timeout = timeout if timeout is not None else get_config().memory.lock_timeout
    deadline = time.monotonic() + effective_timeout

    lock_fd: int | None = None
    acquired = False

    try:
        # Open (or create) the lock file
        lock_fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT)

        while not acquired:
            try:
                # Non-blocking exclusive lock
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                logger.debug("Lock acquired", extra={"lock": str(lock_path)})
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    raise LockFileError(
                        f"Could not acquire lock for {target} within {effective_timeout}s",
                        lock_path=lock_path,
                        timeout=effective_timeout,
                    )
                time.sleep(poll_interval)

        yield

    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
                logger.debug("Lock released", extra={"lock": str(lock_path)})
            except OSError:
                pass


def atomic_write_json(path: Path, data: Any, *, indent: int = 2) -> None:
    """Write JSON data atomically using temp-file-then-rename.

    Crash-safe: if the process dies mid-write, the original file is untouched.
    Citation: POSIX atomic rename semantics; Claude Code file-write pattern.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".tmp_{path.stem}_",
        suffix=path.suffix,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        # Clean up temp file on any failure
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise


def atomic_write_text(path: Path, text: str) -> None:
    """Write text atomically using temp-file-then-rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".tmp_{path.stem}_",
        suffix=path.suffix,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise


def read_json_safe(path: Path, default: Any | None = None) -> Any:
    """Read JSON from path, returning default if file missing or corrupt."""
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Failed to read JSON, returning default", extra={"path": str(path)})
        return default


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append a single JSON line to a JSONL file with lock protection."""
    with lock_file(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())


def read_jsonl(path: Path, limit: int = 0) -> list[dict[str, Any]]:
    """Read all (or last N) lines from a JSONL file."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    records = []
    for line in lines[-limit:] if limit > 0 else lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Skipping malformed JSONL line", extra={"path": str(path), "line": line[:100]})
    return records
