"""
AsyncGenerator-based streaming for chat output.

Implements the Claude Code queryLoop() pattern: an AsyncGenerator that
yields stream events, enabling reactive UI updates while maintaining
synchronous control flow.

Citation: Claude Code architecture (arXiv:2604.14228v1)
"""

from __future__ import annotations

import asyncio
from enum import Enum, auto
from typing import Any, AsyncGenerator

from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)


class StreamEventType(Enum):
    """Types of streaming events from the fleet."""

    START = auto()
    THINKING = auto()
    TOOL_CALL = auto()
    TOOL_RESULT = auto()
    CONTENT = auto()
    ERROR = auto()
    END = auto()


class StreamEvent:
    """A single event in the streaming output."""

    def __init__(
        self,
        event_type: StreamEventType,
        data: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.event_type = event_type
        self.data = data
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"StreamEvent({self.event_type.name}, data={self.data!r})"


async def stream_response(
    message: str,
    node: str = "node-a",
) -> AsyncGenerator[StreamEvent, None]:
    """Stream a response from a fleet node using AsyncGenerator.

    Yields StreamEvent objects that the UI can render incrementally.
    In production, this would connect to the node's SSE or WebSocket endpoint.

    Args:
        message: User message to send
        node: Target node ID

    Yields:
        StreamEvent objects
    """
    yield StreamEvent(StreamEventType.START, {"node": node, "message": message})

    # Simulate thinking delay
    yield StreamEvent(StreamEventType.THINKING, "Analyzing intent...")
    await asyncio.sleep(0.3)

    # Check if this looks like a tool-use request
    if any(kw in message.lower() for kw in ["search", "find", "look up", "query"]):
        yield StreamEvent(StreamEventType.TOOL_CALL, {"tool": "fleet_memory_read", "args": {"query": message}})
        await asyncio.sleep(0.5)
        yield StreamEvent(StreamEventType.TOOL_RESULT, {"status": "ok", "records": 3})

    # Stream content chunks
    response = f"Response from {node} for: '{message}'"
    words = response.split()
    for word in words:
        yield StreamEvent(StreamEventType.CONTENT, word + " ")
        await asyncio.sleep(0.05)

    yield StreamEvent(StreamEventType.END, {"total_tokens": len(message) + len(response)})
