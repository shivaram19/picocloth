"""
Citation registry for PicoCloth-CLI.

Every significant architectural decision in this codebase must be traceable
to a peer-reviewed paper, production system documentation, or authoritative
blog post. This module provides a lightweight registry for attaching
citations to code paths, commands, and log messages.

Citation: Anthropic "Building Effective Agents" — evidence-based engineering
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Citation:
    """A single research citation with metadata."""

    key: str
    title: str
    authors: str
    year: int
    url: str
    insight: str

    def __str__(self) -> str:
        return f"[{self.key}] {self.authors} ({self.year}). {self.title}. {self.url}"


class CitationRegistry:
    """Central registry of all research citations used in PicoCloth-CLI."""

    _registry: ClassVar[dict[str, Citation]] = {}

    @classmethod
    def register(cls, citation: Citation) -> Citation:
        cls._registry[citation.key] = citation
        return citation

    @classmethod
    def get(cls, key: str) -> Citation | None:
        return cls._registry.get(key)

    @classmethod
    def all(cls) -> list[Citation]:
        return list(cls._registry.values())

    @classmethod
    def markdown_bibliography(cls) -> str:
        lines = ["# Bibliography\n"]
        for c in sorted(cls._registry.values(), key=lambda x: (x.year, x.key)):
            lines.append(f"## {c.key}\n")
            lines.append(f"- **Title:** {c.title}")
            lines.append(f"- **Authors:** {c.authors}")
            lines.append(f"- **Year:** {c.year}")
            lines.append(f"- **URL:** {c.url}")
            lines.append(f"- **Insight:** {c.insight}\n")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Register core citations
# ---------------------------------------------------------------------------

CitationRegistry.register(
    Citation(
        key="anthropic-2024-agents",
        title="Building Effective Agents",
        authors="Anthropic",
        year=2024,
        url="https://www.anthropic.com/research/building-effective-agents",
        insight="Five composable workflow patterns; agents vs. workflows distinction; simplicity principle",
    )
)

CitationRegistry.register(
    Citation(
        key="arxiv-2604.14228",
        title="The Design Space of Today's and Future AI Agent Systems",
        authors="Various",
        year=2026,
        url="https://arxiv.org/html/2604.14228v1",
        insight="Claude Code architecture analysis; sidechain transcripts; AsyncGenerator queryLoop; file-lock coordination",
    )
)

CitationRegistry.register(
    Citation(
        key="arxiv-2602.07072",
        title="AgentSpawn: Adaptive Multi-Agent Collaboration Through Dynamic Spawning",
        authors="Various",
        year=2026,
        url="https://arxiv.org/html/2602.07072v1",
        insight="Runtime agent spawning; memory slicing algorithm (42% overhead reduction); spawn package spec; 34% completion improvement",
    )
)

CitationRegistry.register(
    Citation(
        key="arxiv-2602.16873",
        title="Task-Adaptive Multi-Agent Orchestration in the Era of LLM Performance Convergence",
        authors="Various",
        year=2024,
        url="https://arxiv.org/html/2602.16873",
        insight="Orchestration structure as primary performance lever; dynamic topology based on task characteristics",
    )
)

CitationRegistry.register(
    Citation(
        key="arxiv-2511.03690",
        title="OpenHands Software Agent SDK",
        authors="Various",
        year=2025,
        url="https://arxiv.org/html/2511.03690v1",
        insight="Modular SDK design (sdk/tool/workspace/application); opt-in sandboxing; V1 architecture",
    )
)

CitationRegistry.register(
    Citation(
        key="arxiv-2604.08290",
        title="A Context Engineering Toolkit for AI Coding Assistants",
        authors="Various",
        year=2026,
        url="https://arxiv.org/html/2604.08290v1",
        insight="Context rot research; per-file relevance scoring; graduated compaction pipeline; zone-based pruning",
    )
)

CitationRegistry.register(
    Citation(
        key="arxiv-2601.11595",
        title="Enhancing MCP with Context-Aware Server Collaboration",
        authors="Various",
        year=2026,
        url="https://arxiv.org/html/2601.11595v2",
        insight="Context-aware MCP server collaboration reduces repeated inference calls; prevents context loss between steps",
    )
)

CitationRegistry.register(
    Citation(
        key="mcp-spec",
        title="Model Context Protocol Specification",
        authors="Anthropic",
        year=2024,
        url="https://modelcontextprotocol.io",
        insight="Standardized agent-tool interface; stdio + HTTP transports; enterprise default-on",
    )
)

CitationRegistry.register(
    Citation(
        key="ms-agent-framework",
        title="Microsoft Agent Framework 1.0",
        authors="Microsoft",
        year=2026,
        url="https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/",
        insight="Production multi-agent SDK; declarative YAML agents; checkpointing/hydration; A2A + MCP support",
    )
)

CitationRegistry.register(
    Citation(
        key="graph-digital-memory",
        title="Katelyn Skills OS — 4-Layer Memory Architecture",
        authors="Graph Digital",
        year=2024,
        url="https://graph.digital/guides/ai-agents/memory",
        insight="Doctrine/Project/State/Run separation; immutable constitution; append-only facts; real-time operational truth",
    )
)

CitationRegistry.register(
    Citation(
        key="agent-fleet",
        title="agent-fleet: Orchestrate Multiple AI CLIs as a Team",
        authors="Luxuzhou",
        year=2026,
        url="https://github.com/Luxuzhou/agent-fleet",
        insight="MCP-native fleet orchestration; role-based tool routing; poll-based task queue; Streamable HTTP transport",
    )
)

CitationRegistry.register(
    Citation(
        key="typer",
        title="Typer — Build great CLIs. Easy to code. Based on Python type hints.",
        authors="Sebastián Ramírez",
        year=2024,
        url="https://typer.tiangolo.com",
        insight="Type-hinted CLI framework; auto-generated help; rapid development; Click foundation",
    )
)

CitationRegistry.register(
    Citation(
        key="rich",
        title="Rich — Python library for rich text and beautiful formatting in the terminal",
        authors="Will McGugan",
        year=2024,
        url="https://github.com/Textualize/rich",
        insight="Tables, progress bars, markdown rendering, syntax highlighting, tracebacks; 16.7M colors",
    )
)

CitationRegistry.register(
    Citation(
        key="textual",
        title="Textual — Python framework for building terminal user interfaces",
        authors="Will McGugan",
        year=2025,
        url="https://github.com/Textualize/textual",
        insight="DOM-based widget system; reactive updates; CSS-like TCSS styling; async-native; ideal for fleet dashboards",
    )
)
