#!/usr/bin/env python3
"""
PicoClaw → Langfuse EventBridge Hook (Langfuse v4 API)
Receives agent events via JSON-RPC stdio and forwards them to Langfuse.

Protocol:
  - PicoClaw spawns this as a subprocess
  - Reads line-delimited JSON-RPC from stdin
  - Writes JSON-RPC responses to stdout
  - Must stay alive until stdin closes (handle events continuously)

Langfuse v4 API:
  - start_observation() creates traces/spans/generations
  - observation.update() patches metadata/output
  - observation.end() finalizes the observation
  - langfuse.flush() sends queued events immediately
"""

import json
import os
import signal
import sys
import time
import traceback
import uuid
from typing import Any, Dict, Optional

# ── Venv bootstrap ─────────────────────────────────────────────────────────
VENV_PYTHON = "/home/shivaramgoud/tinkering/tinkering-with-claws/picocloth/.venv/bin/python"
if sys.executable != VENV_PYTHON and os.path.exists(VENV_PYTHON):
    os.execv(VENV_PYTHON, [VENV_PYTHON, __file__] + sys.argv[1:])

try:
    from langfuse import Langfuse
except ImportError:
    print("ERROR: langfuse not installed. Run: pip install langfuse", file=sys.stderr)
    sys.exit(1)

# ── Configuration ──────────────────────────────────────────────────────────
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
NODE_ID = os.environ.get("FLEET_NODE_ID", "unknown-node")

# Initialize Langfuse client
langfuse: Optional[Langfuse] = None
if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
    langfuse = Langfuse(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_HOST,
        flush_interval=5,
    )
else:
    print(
        "WARN: Langfuse credentials not set. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY env vars.",
        file=sys.stderr,
    )

# In-memory state
_traces: Dict[str, Any] = {}          # trace_id → root observation (turn)
_generations: Dict[str, Any] = {}     # gen_key → generation observation
_spans: Dict[str, Any] = {}           # span_key → span observation
_trace_map: Dict[str, str] = {}       # session:turn → langfuse_trace_id

_shutting_down = False


def _shutdown_handler(signum, frame):
    global _shutting_down
    _shutting_down = True
    if langfuse:
        print(f"[{NODE_ID}] Flushing Langfuse events before exit...", file=sys.stderr)
        langfuse.flush()
    sys.exit(0)


signal.signal(signal.SIGTERM, _shutdown_handler)
signal.signal(signal.SIGINT, _shutdown_handler)


def write_jsonrpc(msg: dict):
    """Write a JSON-RPC message to stdout."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _make_trace_id(session_key: str, turn_id: str) -> str:
    """Generate a deterministic Langfuse-compatible trace ID."""
    key = f"{NODE_ID}:{session_key}:{turn_id}"
    if key not in _trace_map:
        _trace_map[key] = uuid.uuid4().hex
    return _trace_map[key]


def handle_hello(req_id: int):
    write_jsonrpc({
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "name": "langfuse-bridge",
            "version": 1,
            "modes": ["observe"],
        },
    })


# PicoClaw EventKind enum → string names (uint8 values)
_EVENT_KIND_MAP = {
    0: "turn_start",
    1: "turn_end",
    2: "llm_request",
    3: "llm_delta",
    4: "llm_response",
    5: "llm_retry",
    6: "context_compress",
    7: "session_summarize",
    8: "tool_exec_start",
    9: "tool_exec_end",
    10: "tool_exec_skipped",
    11: "steering_injected",
    12: "follow_up_queued",
    13: "interrupt_received",
    14: "subturn_spawn",
    15: "subturn_end",
    16: "subturn_result_delivered",
    17: "subturn_orphan",
    18: "error",
}


def _normalize_kind(kind) -> str:
    if isinstance(kind, int):
        return _EVENT_KIND_MAP.get(kind, f"unknown({kind})")
    return str(kind)


def handle_event(params: dict):
    if not langfuse:
        return

    try:
        kind_raw = params.get("Kind", "")
        kind = _normalize_kind(kind_raw)
        meta = params.get("Meta", {}) or {}
        payload = params.get("Payload", {}) or {}

        turn_id = meta.get("TurnID", "")
        session_key = meta.get("SessionKey", "")
        agent_id = meta.get("AgentID", "")
        iteration = meta.get("Iteration", 0)
        trace_path = meta.get("TracePath", "")

        trace_id_key = f"{NODE_ID}:{session_key}:{turn_id}" if turn_id else f"{NODE_ID}:{session_key}"
        trace_id = _make_trace_id(session_key, turn_id)

        # ── Turn Start ─────────────────────────────────────────────────────
        if kind == "turn_start":
            user_msg = payload.get("UserMessage", "")
            _traces[trace_id_key] = langfuse.start_observation(
                name=f"{NODE_ID}-turn",
                as_type="agent",
                input=user_msg,
                metadata={
                    "node_id": NODE_ID,
                    "agent_id": agent_id,
                    "turn_id": turn_id,
                    "trace_path": trace_path,
                    "session_key": session_key,
                },
            )

        # ── Turn End ───────────────────────────────────────────────────────
        elif kind == "turn_end":
            status = payload.get("Status", "completed")
            iterations = payload.get("Iterations", 0)
            duration_ns = payload.get("Duration", 0)
            final_len = payload.get("FinalContentLen", 0)
            duration_ms = duration_ns // 1_000_000 if isinstance(duration_ns, int) else 0

            if trace_id_key in _traces:
                obs = _traces[trace_id_key]
                obs.update(
                    output={
                        "status": status,
                        "iterations": iterations,
                        "duration_ms": duration_ms,
                        "final_content_length": final_len,
                    },
                    metadata={
                        "status": status,
                        "iterations": iterations,
                        "duration_ms": duration_ms,
                    },
                )
                obs.end()
                langfuse.flush()
                _cleanup_trace(trace_id_key)

        # ── LLM Request ────────────────────────────────────────────────────
        elif kind == "llm_request":
            model = payload.get("Model", "unknown")
            messages_count = payload.get("MessagesCount", 0)
            tools_count = payload.get("ToolsCount", 0)
            max_tokens = payload.get("MaxTokens", 0)
            temperature = payload.get("Temperature", 0.0)

            gen_key = f"{trace_id_key}:llm:{iteration}"
            parent = _traces.get(trace_id_key)
            if parent:
                _generations[gen_key] = parent.start_observation(
                    name="llm-call",
                    as_type="generation",
                    model=model,
                    model_parameters={
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "tools_count": tools_count,
                    },
                    input={"messages_count": messages_count},
                    metadata={
                        "node_id": NODE_ID,
                        "iteration": iteration,
                    },
                )

        # ── LLM Response ───────────────────────────────────────────────────
        elif kind == "llm_response":
            content_len = payload.get("ContentLen", 0)
            tool_calls = payload.get("ToolCalls", 0)
            has_reasoning = payload.get("HasReasoning", False)
            usage = payload.get("Usage", {}) or {}

            gen_key = f"{trace_id_key}:llm:{iteration}"
            if gen_key in _generations:
                gen = _generations[gen_key]
                gen.update(
                    output={
                        "content_length": content_len,
                        "tool_calls": tool_calls,
                        "has_reasoning": has_reasoning,
                    },
                    metadata={"has_reasoning": has_reasoning},
                    usage_details=usage if usage else None,
                )
                gen.end()

        # ── Tool Exec Start ────────────────────────────────────────────────
        elif kind == "tool_exec_start":
            tool_name = payload.get("Tool", "unknown")
            arguments = payload.get("Arguments", {})

            span_key = f"{trace_id_key}:tool:{iteration}:{tool_name}"
            parent = _traces.get(trace_id_key)
            if parent:
                _spans[span_key] = parent.start_observation(
                    name=f"tool:{tool_name}",
                    as_type="tool",
                    input=arguments,
                    metadata={
                        "node_id": NODE_ID,
                        "iteration": iteration,
                        "tool": tool_name,
                    },
                )

        # ── Tool Exec End ──────────────────────────────────────────────────
        elif kind == "tool_exec_end":
            tool_name = payload.get("Tool", "unknown")
            duration_ns = payload.get("Duration", 0)
            is_error = payload.get("IsError", False)
            for_llm_len = payload.get("ForLLMLen", 0)
            result = payload.get("Result", None)
            duration_ms = duration_ns // 1_000_000 if isinstance(duration_ns, int) else 0

            span_key = f"{trace_id_key}:tool:{iteration}:{tool_name}"
            if span_key in _spans:
                span = _spans[span_key]
                span.update(
                    output=result if result is not None else {"result_length": for_llm_len},
                    metadata={
                        "duration_ms": duration_ms,
                        "is_error": is_error,
                        "result_length": for_llm_len,
                    },
                    level="ERROR" if is_error else "DEFAULT",
                )
                span.end()

        # ── SubTurn Spawn ──────────────────────────────────────────────────
        elif kind == "subturn_spawn":
            child_agent = payload.get("AgentID", "")
            label = payload.get("Label", "")
            parent_turn = payload.get("ParentTurnID", "")
            span_key = f"{trace_id_key}:subturn:{child_agent}"
            parent = _traces.get(trace_id_key)
            if parent:
                _spans[span_key] = parent.start_observation(
                    name=f"subturn:{child_agent}",
                    as_type="span",
                    input=label,
                    metadata={
                        "subturn_spawned": True,
                        "subturn_agent": child_agent,
                        "subturn_label": label,
                        "subturn_parent": parent_turn,
                    },
                )

        # ── SubTurn End ────────────────────────────────────────────────────
        elif kind == "subturn_end":
            child_agent = payload.get("AgentID", "")
            status = payload.get("Status", "completed")
            span_key = f"{trace_id_key}:subturn:{child_agent}"
            if span_key in _spans:
                span = _spans[span_key]
                span.update(
                    output={"status": status},
                    metadata={"subturn_status": status},
                )
                span.end()

        # ── Error ──────────────────────────────────────────────────────────
        elif kind == "error":
            stage = payload.get("Stage", "unknown")
            message = payload.get("Message", "")
            parent = _traces.get(trace_id_key)
            if parent:
                parent.update(
                    metadata={
                        "error_stage": stage,
                        "error_message": message,
                    },
                    level="ERROR",
                    status_message=message,
                )

        # ── Context Compress ───────────────────────────────────────────────
        elif kind == "context_compress":
            reason = payload.get("Reason", "")
            dropped = payload.get("DroppedMessages", 0)
            remaining = payload.get("RemainingMessages", 0)
            parent = _traces.get(trace_id_key)
            if parent:
                parent.update(
                    metadata={
                        "context_compressed": True,
                        "compress_reason": reason,
                        "dropped_messages": dropped,
                        "remaining_messages": remaining,
                    },
                )

    except Exception as e:
        print(f"ERROR in handle_event ({kind}): {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


def _cleanup_trace(trace_id_key: str):
    """Remove all state associated with a completed turn."""
    _traces.pop(trace_id_key, None)
    _trace_map.pop(trace_id_key, None)
    for key in list(_generations.keys()):
        if key.startswith(trace_id_key + ":"):
            _generations.pop(key, None)
    for key in list(_spans.keys()):
        if key.startswith(trace_id_key + ":"):
            _spans.pop(key, None)


def main():
    print("Langfuse Bridge Hook started", file=sys.stderr)
    print(f"  Node: {NODE_ID}", file=sys.stderr)
    print(f"  Langfuse: {LANGFUSE_HOST}", file=sys.stderr)
    print(f"  Connected: {langfuse is not None}", file=sys.stderr)
    sys.stderr.flush()

    for line in sys.stdin:
        if _shutting_down:
            break

        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg_id = msg.get("id", 0)
        method = msg.get("method", "")

        if method == "hook.hello":
            handle_hello(msg_id)

        elif method == "hook.event":
            params = msg.get("params", {})
            handle_event(params)
            if msg_id:
                write_jsonrpc({"jsonrpc": "2.0", "id": msg_id, "result": {}})

        elif msg_id:
            write_jsonrpc({"jsonrpc": "2.0", "id": msg_id, "result": {}})

    if langfuse:
        print(f"[{NODE_ID}] Stdin closed. Flushing remaining events...", file=sys.stderr)
        langfuse.flush()


if __name__ == "__main__":
    main()
