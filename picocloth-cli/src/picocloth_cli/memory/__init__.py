"""Shared memory layer operations: doctrine, project, state, run, compaction."""

from picocloth_cli.memory.compaction import compact_session, CompactionResult
from picocloth_cli.memory.doctrine import list_policies, list_schemas, list_skills, read_skill
from picocloth_cli.memory.project import list_categories, list_records, read_record, write_record
from picocloth_cli.memory.run import (
    append_subagent_turn,
    append_tool_call,
    archive_session,
    create_subagent_transcript,
    get_session_dir,
    get_subagent_transcript,
    get_tool_calls,
    read_context,
    write_context,
)
from picocloth_cli.memory.state import read_state, update_fleet_node, write_state

__all__ = [
    # Doctrine
    "list_skills",
    "read_skill",
    "list_policies",
    "list_schemas",
    # Project
    "list_categories",
    "read_record",
    "write_record",
    "list_records",
    # State
    "read_state",
    "write_state",
    "update_fleet_node",
    # Run
    "get_session_dir",
    "write_context",
    "read_context",
    "append_tool_call",
    "get_tool_calls",
    "create_subagent_transcript",
    "append_subagent_turn",
    "get_subagent_transcript",
    "archive_session",
    # Compaction
    "compact_session",
    "CompactionResult",
]
