"""
Tests for shared memory layer operations.

Validates CRUD, atomic writes, and lock-file coordination.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from picocloth_cli.core.constants import PROJECT_DIR, RUN_DIR
from picocloth_cli.memory.project import read_record, write_record
from picocloth_cli.memory.run import get_session_dir, write_context, read_context
from picocloth_cli.utils.files import atomic_write_json, lock_file, read_json_safe


class TestAtomicWrites:
    """Test atomic file write utilities."""

    def test_atomic_write_json(self, tmp_path: Path) -> None:
        path = tmp_path / "test.json"
        data = {"key": "value", "nested": {"a": 1}}
        atomic_write_json(path, data)
        assert path.exists()
        assert read_json_safe(path) == data

    def test_lock_file_coordination(self, tmp_path: Path) -> None:
        path = tmp_path / "shared.json"
        path.write_text("{}")

        acquired = []

        def acquire():
            with lock_file(path, timeout=1.0):
                acquired.append(True)

        import threading
        t1 = threading.Thread(target=acquire)
        t2 = threading.Thread(target=acquire)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(acquired) == 2


class TestProjectMemory:
    """Test project layer CRUD."""

    def test_write_and_read_record(self) -> None:
        write_record("facts", "test_fact", {"data": "hello"}, source="test")
        result = read_record("facts", "test_fact")
        assert result is not None
        assert result["data"] == {"data": "hello"}
        assert result["source"] == "test"


class TestRunMemory:
    """Test run layer session management."""

    def test_session_dir_creation(self) -> None:
        session_dir = get_session_dir("test-session-123")
        assert session_dir.exists()

    def test_context_roundtrip(self) -> None:
        write_context("test-session-456", {"turns": 5, "topic": "testing"})
        ctx = read_context("test-session-456")
        assert ctx is not None
        assert ctx["turns"] == 5
