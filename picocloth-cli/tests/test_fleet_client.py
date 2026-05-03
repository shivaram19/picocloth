"""
Tests for the MCP fleet client and HTTP utilities.

These tests validate the data structures and helper functions without
requiring a running fleet server.
"""

from __future__ import annotations

import pytest

from picocloth_cli.core.constants import NODE_PORTS, NODES
from picocloth_cli.core.exceptions import NodeNotFoundError
from picocloth_cli.fleet.state import append_task, get_task_queue
from picocloth_cli.utils.http import node_url


class TestNodeUrlResolution:
    """Test HTTP node URL resolution."""

    def test_valid_node(self) -> None:
        url = node_url("node-a")
        assert url == f"http://127.0.0.1:{NODE_PORTS[0]}"

    def test_last_node(self) -> None:
        url = node_url("node-j")
        assert url == f"http://127.0.0.1:{NODE_PORTS[-1]}"

    def test_invalid_node_raises(self) -> None:
        with pytest.raises(NodeNotFoundError):
            node_url("node-z")


class TestTaskQueue:
    """Test task queue operations with temporary state."""

    def test_append_and_read(self) -> None:
        # Clean test state
        from picocloth_cli.core.constants import STATE_DIR
        import json
        queue_path = STATE_DIR / "task-queue.json"
        original = queue_path.read_text() if queue_path.exists() else "[]"

        try:
            if queue_path.exists():
                queue_path.write_text("[]")

            task = append_task("node-b", "test task", priority="high")
            assert task["target_node"] == "node-b"
            assert task["priority"] == "high"
            assert task["status"] == "pending"

            queue = get_task_queue()
            assert len(queue) >= 1
        finally:
            queue_path.write_text(original)
