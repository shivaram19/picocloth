"""
MCP Fleet Client for PicoCloth-CLI.

Implements the Model Context Protocol (MCP) client over stdio transport,
enabling the CLI to communicate with the existing MCP Fleet Server.
This follows the zero-dependency design of the fleet server itself —
no MCP SDK required, just JSON-RPC over stdio.

Citation: MCP Protocol Spec (modelcontextprotocol.io)
Citation: agent-fleet Streamable HTTP + stdio dual transport (github.com/Luxuzhou/agent-fleet)
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import FLEET_SERVER_PATH, FLEET_SHARED_DIR
from picocloth_cli.core.exceptions import FleetError, MCPConnectionError
from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MCPResult:
    """Result of an MCP tool call."""

    success: bool
    data: Any
    raw: str


class MCPFleetClient:
    """MCP client connecting to the PicoCloth Fleet Server via stdio.

    Usage:
        async with MCPFleetClient() as client:
            state = await client.query_state()
            await client.spawn_task("node-b", "Build a REST API")
    """

    def __init__(
        self,
        *,
        server_path: Path | None = None,
        shared_dir: Path | None = None,
        node_id: str = "picocloth-cli",
    ) -> None:
        cfg = get_config()
        self.server_path = server_path or cfg.fleet.server_path
        self.shared_dir = shared_dir or cfg.fleet.shared_dir
        self.node_id = node_id
        self._proc: subprocess.Popen | None = None
        self._initialized = False
        self._tools: list[dict] = []

    async def __aenter__(self) -> MCPFleetClient:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Launch the fleet server subprocess and perform MCP handshake."""
        if self._proc is not None:
            return

        env = os.environ.copy()
        env["FLEET_SHARED_DIR"] = str(self.shared_dir)
        env["FLEET_NODE_ID"] = self.node_id

        try:
            self._proc = subprocess.Popen(
                [sys.executable, str(self.server_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
        except OSError as exc:
            raise MCPConnectionError(f"Failed to start fleet server: {exc}") from exc

        # MCP initialize handshake
        init_req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "picocloth-cli", "version": "0.1.0"},
            },
        }
        init_resp = await self._send_recv(init_req)
        if init_resp is None or "result" not in init_resp:
            await self.disconnect()
            raise MCPConnectionError("Fleet server failed initialize handshake")

        self._initialized = True
        logger.info("MCP fleet client connected", extra={"server": str(self.server_path)})

        # Discover available tools
        tools_req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
        }
        tools_resp = await self._send_recv(tools_req)
        if tools_resp and "result" in tools_resp:
            self._tools = tools_resp["result"].get("tools", [])
            logger.debug("Discovered fleet tools", extra={"count": len(self._tools)})

    async def disconnect(self) -> None:
        """Terminate the fleet server subprocess gracefully."""
        if self._proc is not None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, self._proc.wait),
                    timeout=3.0,
                )
            except asyncio.TimeoutError:
                self._proc.kill()
            except Exception as exc:
                logger.warning("Error disconnecting fleet client", extra={"error": str(exc)})
            finally:
                self._proc = None
                self._initialized = False
                logger.info("MCP fleet client disconnected")

    async def _send_recv(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Send a JSON-RPC request and await the response.

        This is the core transport primitive. It writes a single JSON line
to the server's stdin and reads a single JSON line from stdout.
        """
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise MCPConnectionError("Fleet server not connected")

        line = json.dumps(request, ensure_ascii=False)
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()

        # Read response line with timeout
        try:
            response_line = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, self._proc.stdout.readline),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.error("MCP response timeout", extra={"request_id": request.get("id")})
            return None

        if not response_line:
            return None

        try:
            return json.loads(response_line.strip())
        except json.JSONDecodeError as exc:
            logger.error("Invalid MCP response JSON", extra={"line": response_line[:200]})
            raise MCPConnectionError(f"Invalid JSON from fleet server: {exc}") from exc

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> MCPResult:
        """Call an MCP tool by name with arguments."""
        req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        resp = await self._send_recv(req)
        if resp is None:
            return MCPResult(success=False, data=None, raw="")

        if "error" in resp:
            error = resp["error"]
            return MCPResult(
                success=False,
                data=error,
                raw=json.dumps(resp),
            )

        result = resp.get("result", {})
        content = result.get("content", [])
        text = content[0].get("text", "") if content else ""
        is_error = result.get("isError", False)

        try:
            parsed = json.loads(text) if text else {}
        except json.JSONDecodeError:
            parsed = {"raw": text}

        return MCPResult(success=not is_error, data=parsed, raw=text)

    # -----------------------------------------------------------------------
    # Typed convenience methods
    # -----------------------------------------------------------------------

    async def query_state(self) -> dict[str, Any]:
        """Get current health and status of all fleet nodes."""
        result = await self._call_tool("fleet_query_state", {})
        if not result.success:
            raise FleetError(f"fleet_query_state failed: {result.data}")
        return result.data

    async def spawn_task(
        self,
        target_node: str,
        task: str,
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Delegate a task to a specific node in the fleet.

        Args:
            target_node: Node ID, e.g., "node-b"
            task: Task description
            priority: One of "low", "normal", "high", "critical"
        """
        result = await self._call_tool(
            "fleet_spawn_task",
            {"target_node": target_node, "task": task, "priority": priority},
        )
        if not result.success:
            raise FleetError(f"fleet_spawn_task failed: {result.data}")
        return result.data

    async def broadcast(self, message: str, sender: str = "picocloth-cli") -> dict[str, Any]:
        """Broadcast a message to all nodes in the fleet."""
        result = await self._call_tool(
            "fleet_broadcast",
            {"sender": sender, "message": message},
        )
        if not result.success:
            raise FleetError(f"fleet_broadcast failed: {result.data}")
        return result.data

    async def memory_read(self, category: str, key: str) -> dict[str, Any]:
        """Read from shared project memory.

        Args:
            category: e.g., "facts", "decisions", "entities"
            key: File key (without extension)
        """
        result = await self._call_tool(
            "fleet_memory_read",
            {"category": category, "key": key},
        )
        if not result.success:
            raise FleetError(f"fleet_memory_read failed: {result.data}")
        return result.data

    async def memory_write(
        self,
        category: str,
        key: str,
        data: Any,
        append: bool = False,
    ) -> dict[str, Any]:
        """Write to shared project memory."""
        result = await self._call_tool(
            "fleet_memory_write",
            {"category": category, "key": key, "data": data, "append": append},
        )
        if not result.success:
            raise FleetError(f"fleet_memory_write failed: {result.data}")
        return result.data

    async def digital_twin_search(
        self,
        query: str,
        node_id: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search digital twin archives for historical context."""
        args: dict[str, Any] = {"query": query, "limit": limit}
        if node_id:
            args["node_id"] = node_id
        result = await self._call_tool("fleet_digital_twin_search", args)
        if not result.success:
            raise FleetError(f"fleet_digital_twin_search failed: {result.data}")
        return result.data
