"""
Async HTTP client for PicoCloth node gateway communication.

Uses httpx for async HTTP requests to individual node gateways.
This is the primary transport for the CLI → Fleet communication path,
complementing the MCP stdio transport used between nodes.

Citation: agent-fleet Streamable HTTP MCP transport (github.com/Luxuzhou/agent-fleet)
Citation: httpx — modern async HTTP client for Python
"""

from __future__ import annotations

from typing import Any

import httpx

from picocloth_cli.core.config import get_config
from picocloth_cli.core.constants import NODE_PORTS, NODES
from picocloth_cli.core.exceptions import FleetError, NodeOfflineError
from picocloth_cli.core.logging import get_logger

logger = get_logger(__name__)

# Shared async client instance
_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return a shared async HTTP client with connection pooling."""
    global _client
    if _client is None:
        cfg = get_config()
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(cfg.fleet.connection_timeout),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _client


def node_url(node_id: str) -> str:
    """Resolve a node ID to its gateway HTTP URL.

    Args:
        node_id: e.g., "node-a", "node-b"

    Raises:
        NodeNotFoundError: If node_id is not in the fleet registry.
    """
    from picocloth_cli.core.exceptions import NodeNotFoundError

    if node_id not in NODES:
        raise NodeNotFoundError(f"Unknown node: {node_id}")
    idx = NODES.index(node_id)
    port = NODE_PORTS[idx]
    return f"http://127.0.0.1:{port}"


async def node_get(node_id: str, endpoint: str = "/") -> dict[str, Any]:
    """Send a GET request to a node's gateway.

    Returns:
        Parsed JSON response.

    Raises:
        NodeOfflineError: If the node does not respond.
        FleetError: For other HTTP or network errors.
    """
    url = f"{node_url(node_id)}{endpoint}"
    client = get_http_client()
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError as exc:
        raise NodeOfflineError(f"Node {node_id} is not responding at {url}") from exc
    except httpx.HTTPStatusError as exc:
        raise FleetError(f"Node {node_id} returned HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise FleetError(f"Unexpected error communicating with {node_id}: {exc}") from exc


async def node_post(
    node_id: str,
    endpoint: str = "/",
    json_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a POST request to a node's gateway."""
    url = f"{node_url(node_id)}{endpoint}"
    client = get_http_client()
    try:
        response = await client.post(url, json=json_payload)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError as exc:
        raise NodeOfflineError(f"Node {node_id} is not responding at {url}") from exc
    except httpx.HTTPStatusError as exc:
        raise FleetError(f"Node {node_id} returned HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise FleetError(f"Unexpected error communicating with {node_id}: {exc}") from exc


async def health_check(node_id: str) -> bool:
    """Quick health check: return True if node responds, False otherwise."""
    try:
        await node_get(node_id, "/")
        return True
    except NodeOfflineError:
        return False


async def close_http_client() -> None:
    """Close the shared HTTP client. Call on shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
