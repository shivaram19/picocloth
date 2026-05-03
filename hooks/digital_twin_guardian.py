#!/usr/bin/env python3
"""
Digital Twin Guardian - Pre-Compaction Hook for PicoCloth

This hook fires BEFORE context compaction to:
1. Extract durable facts from the about-to-be-compacted conversation
2. Save a full conversation snapshot as a "digital twin"
3. Update the shared project facts database
4. Emit an event to the fleet EventBus

Inspired by:
- OpenClaw issue #7175 (pre-compaction hook)
- ZeroClaw issue #2381 (durable facts extraction)
- Graph Digital's 4-layer memory architecture

Usage: Configure as a process hook in PicoClaw config.json
"""

from __future__ import annotations

import json
import os
import sys
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Configuration from environment (set by PicoClaw hook config)
TWIN_DIR = os.environ.get("PICOCLAW_HOOK_TWIN_DIR", "/tmp/digital-twins")
PROJECT_DIR = os.environ.get("PICOCLAW_HOOK_PROJECT_DIR", "/tmp/project")
NODE_ID = os.environ.get("PICOCLAW_HOOK_NODE_ID", "unknown-node")
MAX_FACTS = int(os.environ.get("PICOCLAW_HOOK_MAX_FACTS", "8"))


def ensure_dirs() -> None:
    Path(TWIN_DIR).mkdir(parents=True, exist_ok=True)
    Path(PROJECT_DIR).mkdir(parents=True, exist_ok=True)
    Path(PROJECT_DIR, "facts").mkdir(parents=True, exist_ok=True)


def extract_durable_facts(conversation: list[dict]) -> list[dict]:
    """
    Simple rule-based fact extraction.
    In production, this would be an LLM call.
    For now, we extract:
    - User preferences ("I prefer...", "I use...")
    - Decisions ("Let's use...", "We decided...")
    - Technical constraints ("must be...", "requires...")
    """
    facts = []
    preference_markers = ["i prefer", "i use", "i like", "i want", "my ", "we use"]
    decision_markers = ["let's use", "we decided", "we will", "chosen", "selected"]
    constraint_markers = ["must be", "requires", "needs to", "cannot", "should not"]

    for msg in conversation:
        content = msg.get("content", "").lower()
        for marker in preference_markers:
            if marker in content:
                facts.append({
                    "type": "preference",
                    "source": msg.get("role", "unknown"),
                    "content": msg.get("content", "")[:200],
                    "confidence": 0.85,
                    "extracted_at": datetime.now(timezone.utc).isoformat()
                })
                break
        for marker in decision_markers:
            if marker in content:
                facts.append({
                    "type": "decision",
                    "source": msg.get("role", "unknown"),
                    "content": msg.get("content", "")[:200],
                    "confidence": 0.90,
                    "extracted_at": datetime.now(timezone.utc).isoformat()
                })
                break
        if len(facts) >= MAX_FACTS:
            break

    return facts[:MAX_FACTS]


def save_digital_twin(
    session_key: str,
    conversation: list[dict],
    context_usage: dict,
    facts: list[dict]
) -> str:
    """Save a full conversation snapshot as a digital twin."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    twin_id = f"{NODE_ID}-{timestamp}"

    twin = {
        "twin_id": twin_id,
        "node_id": NODE_ID,
        "session_key": session_key,
        "trigger": "pre_compaction_hook",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context_usage": context_usage,
        "conversation_snapshot": conversation,
        "extracted_facts": facts,
        "compaction_summary": None
    }

    twin_path = Path(TWIN_DIR) / f"{twin_id}.json"
    with open(twin_path, "w", encoding="utf-8") as f:
        json.dump(twin, f, indent=2, ensure_ascii=False)

    return str(twin_path)


def update_project_facts(facts: list[dict]) -> None:
    """Append extracted facts to the shared project facts database."""
    facts_file = Path(PROJECT_DIR) / "facts" / "auto_extracted.jsonl"

    with open(facts_file, "a", encoding="utf-8") as f:
        for fact in facts:
            f.write(json.dumps(fact, ensure_ascii=False) + "\n")


def handle_before_llm(params: dict[str, Any]) -> dict[str, Any]:
    """Intercept before LLM calls to check context usage."""
    # In a real implementation, we'd detect context budget from params
    # For now, this is a placeholder showing the hook structure
    return {"action": "continue"}


def handle_event(params: dict[str, Any]) -> None:
    """Handle EventBus notifications (fire-and-forget)."""
    kind = params.get("Kind", "")
    kind_str = str(kind) if not isinstance(kind, str) else kind
    if "compaction" in kind_str.lower() or "context_limit" in kind_str.lower():
        # This is where we'd trigger the digital twin creation
        # In the current PicoClaw hook system, events are notifications
        # so we can't easily intercept compaction events here
        pass


def send_response(message_id: int, result: Any | None = None, error: str | None = None) -> None:
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": message_id,
    }
    if error is not None:
        payload["error"] = {"code": -32000, "message": error}
    else:
        payload["result"] = result if result is not None else {}

    try:
        sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        raise SystemExit(0) from None


def handle_request(method: str, params: dict[str, Any]) -> dict[str, Any]:
    if method == "hook.hello":
        return {
            "ok": True,
            "name": "digital-twin-guardian",
            "version": 1,
            "modes": ["observe", "intercept"]
        }
    if method == "hook.before_llm":
        return handle_before_llm(params)
    if method == "hook.after_llm":
        return {"action": "continue"}
    if method == "hook.before_tool":
        return {"action": "continue"}
    if method == "hook.after_tool":
        return {"action": "continue"}
    if method == "hook.approve_tool":
        return {"approved": True}
    raise KeyError(f"method not found: {method}")


def main() -> int:
    ensure_dirs()

    try:
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue

            method = message.get("method")
            message_id = message.get("id", 0)
            params = message.get("params") or {}
            if not isinstance(params, dict):
                params = {}

            if not message_id:
                if method == "hook.event":
                    handle_event(params)
                continue

            try:
                result = handle_request(str(method or ""), params)
            except KeyError as exc:
                send_response(int(message_id), error=str(exc))
                continue
            except Exception as exc:
                send_response(int(message_id), error=f"unexpected error: {exc}")
                continue

            send_response(int(message_id), result=result)
    except KeyboardInterrupt:
        return 0

    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    raise SystemExit(main())
