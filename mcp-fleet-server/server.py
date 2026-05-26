#!/usr/bin/env python3
"""
PicoCloth MCP Fleet Server

A Model Context Protocol server that enables inter-node communication
across the PicoCloth fleet. Each PicoClaw node connects to this server
as an MCP client, gaining access to fleet-wide tools.

Tools exposed:
- fleet_query_state: Get health/status of all registered nodes
- fleet_spawn_task: Delegate a task to a specific node
- fleet_broadcast: Send a message to all nodes
- fleet_memory_read: Read from shared project memory
- fleet_memory_write: Write to shared project memory
- fleet_digital_twin_search: Query historical digital twins

Architecture:
  Node-A <--MCP--> Fleet Server <--MCP--> Node-B
                      |
                      v
                shared/ directory
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# MCP SDK is preferred but we'll implement stdio protocol directly
# for zero-dependency operation on $10 hardware

SHARED_DIR = os.environ.get("FLEET_SHARED_DIR", "/tmp/picocloth-shared")
NODE_ID = os.environ.get("FLEET_NODE_ID", "fleet-server")


def ensure_shared_dirs() -> None:
    dirs = ["doctrine/skills", "doctrine/schemas", "doctrine/policies",
            "project/facts", "project/decisions", "project/entities",
            "state", "run", "digital-twins", "compaction-archive"]
    for d in dirs:
        Path(SHARED_DIR, d).mkdir(parents=True, exist_ok=True)


def get_fleet_state() -> dict:
    """Read the current fleet state from shared memory."""
    state_file = Path(SHARED_DIR, "state", "fleet-state.json")
    if state_file.exists():
        with open(state_file, "r") as f:
            return json.load(f)
    return {
        "nodes": {},
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "version": "1.0"
    }


def save_fleet_state(state: dict) -> None:
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    state_file = Path(SHARED_DIR, "state", "fleet-state.json")
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def register_node(node_id: str, info: dict) -> dict:
    state = get_fleet_state()
    state["nodes"][node_id] = {
        **info,
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        "status": "online"
    }
    save_fleet_state(state)
    return {"registered": True, "node_id": node_id}


def query_fleet_state() -> dict:
    return get_fleet_state()


def spawn_task(target_node: str, task: str, priority: str = "normal") -> dict:
    """Delegate a task to a specific node via the shared task queue."""
    task_id = f"task-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{hash(task) % 10000}"
    task_file = Path(SHARED_DIR, "state", "task-queue.json")

    queue = []
    if task_file.exists():
        with open(task_file, "r") as f:
            queue = json.load(f)

    queue.append({
        "id": task_id,
        "target_node": target_node,
        "task": task,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None
    })

    with open(task_file, "w") as f:
        json.dump(queue, f, indent=2)

    return {"task_id": task_id, "status": "queued", "target": target_node}


def broadcast_message(sender: str, message: str) -> dict:
    """Broadcast a message to all nodes via shared inbox."""
    inbox_file = Path(SHARED_DIR, "state", "fleet-inbox.jsonl")
    entry = {
        "type": "broadcast",
        "sender": sender,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(inbox_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return {"broadcast": True, "recipients": list(get_fleet_state()["nodes"].keys())}


def memory_read(category: str, key: str) -> dict:
    """Read from shared project memory."""
    path = Path(SHARED_DIR, "project", category, f"{key}.json")
    if path.exists():
        with open(path, "r") as f:
            return {"found": True, "data": json.load(f)}
    # Also check jsonl files
    path_jsonl = Path(SHARED_DIR, "project", category, f"{key}.jsonl")
    if path_jsonl.exists():
        lines = []
        with open(path_jsonl, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(json.loads(line))
        return {"found": True, "data": lines}
    return {"found": False, "data": None}


def memory_write(category: str, key: str, data: Any, append: bool = False) -> dict:
    """Write to shared project memory."""
    dir_path = Path(SHARED_DIR, "project", category)
    dir_path.mkdir(parents=True, exist_ok=True)

    if append:
        path = dir_path / f"{key}.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    else:
        path = dir_path / f"{key}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return {"written": True, "path": str(path)}


def digital_twin_search(node_id: str | None, query: str, limit: int = 10) -> dict:
    """Search digital twin archives."""
    twin_dir = Path(SHARED_DIR, "digital-twins")
    if node_id:
        twin_dir = twin_dir / node_id

    results = []
    if twin_dir.exists():
        for f in sorted(twin_dir.glob("*.json"), reverse=True)[:limit]:
            with open(f, "r") as fp:
                results.append(json.load(fp))

    return {"count": len(results), "twins": results}


# MCP Tool definitions for discovery
TOOLS = {
    "fleet_query_state": {
        "description": "Get the current health and status of all fleet nodes",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "fleet_spawn_task": {
        "description": "Delegate a task to a specific node in the fleet",
        "parameters": {
            "type": "object",
            "properties": {
                "target_node": {"type": "string", "description": "Node ID to delegate to"},
                "task": {"type": "string", "description": "Task description"},
                "priority": {"type": "string", "enum": ["low", "normal", "high", "critical"]}
            },
            "required": ["target_node", "task"]
        }
    },
    "fleet_broadcast": {
        "description": "Broadcast a message to all nodes in the fleet",
        "parameters": {
            "type": "object",
            "properties": {
                "sender": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["sender", "message"]
        }
    },
    "fleet_memory_read": {
        "description": "Read from the shared fleet memory store",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "e.g., facts, decisions, entities"},
                "key": {"type": "string"}
            },
            "required": ["category", "key"]
        }
    },
    "fleet_memory_write": {
        "description": "Write to the shared fleet memory store",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "key": {"type": "string"},
                "data": {},
                "append": {"type": "boolean", "default": False}
            },
            "required": ["category", "key", "data"]
        }
    },
    "fleet_digital_twin_search": {
        "description": "Search digital twin archives for historical context",
        "parameters": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    },
    "fleet_extract": {
        "description": "Extract structured facts from search results and store in shared memory",
        "parameters": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "description": "Search result objects with url, title, snippet/body"
                },
                "topic": {"type": "string", "description": "Query topic for context"},
                "tier": {"type": "string", "enum": ["fast", "deep", "hybrid"], "default": "hybrid"},
                "store": {"type": "boolean", "default": True},
                "broadcast": {"type": "boolean", "default": False}
            },
            "required": ["results"]
        }
    }
}


def run_extract(results: list, topic: str, tier: str, store: bool, broadcast: bool) -> dict:
    """Run the extract engine on search results."""
    import subprocess
    import tempfile
    import os

    # Write results to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(results, f)
        input_path = f.name

    # Determine engine path: prefer standalone, fallback to CLI package
    engine_paths = [
        Path(SHARED_DIR).parent / "shared" / "tools" / "extract-engine" / "extract_engine.py",
        Path(__file__).parent.parent / "shared" / "tools" / "extract-engine" / "extract_engine.py",
    ]
    engine_path = None
    for p in engine_paths:
        if p.exists():
            engine_path = p
            break

    if not engine_path:
        # Inline fallback: minimal fast-lane extraction
        facts = []
        for r in results:
            url = r.get("href") or r.get("link") or r.get("url", "")
            title = r.get("title", "")
            snippet = r.get("body", r.get("snippet", r.get("description", "")))
            facts.append({
                "fact_id": str(hash(snippet + url))[:16],
                "topic": topic,
                "triple": {"entity": topic, "relation": "mentions", "claim": snippet[:200]},
                "raw_text": snippet,
                "fact_type": "snippet",
                "sources": [{"url": url, "domain": url.split("/")[2] if "//" in url else "unknown", "tier": 3}],
                "confidence": 0.3,
                "extraction_tier": "fallback"
            })
        return {"extracted": len(facts), "facts": facts, "engine": "fallback"}

    cmd = [sys.executable, str(engine_path), "--input", input_path, "--topic", topic, "--tier", tier]
    if not store:
        cmd.append("--no-store")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        os.unlink(input_path)
        if result.returncode == 0:
            try:
                output = json.loads(result.stdout)
                if store:
                    # Write to shared memory
                    dir_path = Path(SHARED_DIR, "project", "facts")
                    dir_path.mkdir(parents=True, exist_ok=True)
                    path = dir_path / f"{topic.lower().replace(' ', '_')}.jsonl"
                    with open(path, "a") as f:
                        for fact in output.get("facts", []):
                            f.write(json.dumps(fact) + "\n")
                if broadcast:
                    inbox_file = Path(SHARED_DIR, "state", "fleet-inbox.jsonl")
                    entry = {
                        "type": "extract_broadcast",
                        "topic": topic,
                        "facts_count": len(output.get("facts", [])),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    with open(inbox_file, "a") as f:
                        f.write(json.dumps(entry) + "\n")
                return {"extracted": len(output.get("facts", [])), "facts": output.get("facts", []), "engine": "thee"}
            except json.JSONDecodeError:
                return {"extracted": 0, "raw": result.stdout[:500], "error": "Invalid JSON from engine"}
        else:
            return {"error": result.stderr[:500]}
    except Exception as e:
        return {"error": str(e)}


def handle_tool_call(name: str, arguments: dict) -> dict:
    try:
        if name == "fleet_query_state":
            return query_fleet_state()
        elif name == "fleet_spawn_task":
            return spawn_task(arguments["target_node"], arguments["task"], arguments.get("priority", "normal"))
        elif name == "fleet_broadcast":
            return broadcast_message(arguments["sender"], arguments["message"])
        elif name == "fleet_memory_read":
            return memory_read(arguments["category"], arguments["key"])
        elif name == "fleet_memory_write":
            return memory_write(arguments["category"], arguments["key"], arguments["data"], arguments.get("append", False))
        elif name == "fleet_digital_twin_search":
            return digital_twin_search(arguments.get("node_id"), arguments["query"], arguments.get("limit", 10))
        elif name == "fleet_extract":
            return run_extract(arguments["results"], arguments.get("topic", ""), arguments.get("tier", "hybrid"), arguments.get("store", True), arguments.get("broadcast", False))
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}


def send(message: dict) -> None:
    print(json.dumps(message, ensure_ascii=False), flush=True)


async def main() -> None:
    ensure_shared_dirs()

    # Register this node
    register_node(NODE_ID, {"role": "fleet-server", "tools": list(TOOLS.keys())})

    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        except KeyboardInterrupt:
            break
        if not line:
            break

        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        req_id = request.get("id")
        method = request.get("method", "")

        if method == "initialize":
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "picocloth-fleet-server", "version": "1.0.0"}
                }
            })
        elif method == "tools/list":
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {"name": k, "description": v["description"], "inputSchema": v["parameters"]}
                        for k, v in TOOLS.items()
                    ]
                }
            })
        elif method == "tools/call":
            params = request.get("params", {})
            result = handle_tool_call(params.get("name"), params.get("arguments", {}))
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                    "isError": "error" in result
                }
            })
        elif method == "prompts/list":
            send({"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}})
        elif method == "resources/list":
            send({"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}})


if __name__ == "__main__":
    asyncio.run(main())
