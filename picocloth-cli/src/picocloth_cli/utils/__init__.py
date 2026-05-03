"""Utility modules: file I/O, HTTP client, citation registry."""

from picocloth_cli.utils.citations import Citation, CitationRegistry
from picocloth_cli.utils.files import (
    atomic_write_json,
    atomic_write_text,
    append_jsonl,
    lock_file,
    read_json_safe,
    read_jsonl,
)
from picocloth_cli.utils.http import (
    close_http_client,
    get_http_client,
    health_check,
    node_get,
    node_post,
    node_url,
)

__all__ = [
    # Citations
    "Citation",
    "CitationRegistry",
    # Files
    "lock_file",
    "atomic_write_json",
    "atomic_write_text",
    "read_json_safe",
    "append_jsonl",
    "read_jsonl",
    # HTTP
    "get_http_client",
    "node_url",
    "node_get",
    "node_post",
    "health_check",
    "close_http_client",
]
