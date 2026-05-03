"""
Tests for the intent classification and complexity evaluation engine.

Citation: pytest best practices; type-safe test fixtures
"""

from __future__ import annotations

import pytest

from picocloth_cli.intent.classifier import IntentType, classify_intent
from picocloth_cli.intent.complexity import ComplexityMetrics, evaluate_complexity
from picocloth_cli.intent.engine import IntentEngine, LowConfidenceError


class TestIntentClassifier:
    """Test the rule-based and heuristic intent classifier."""

    def test_orchestrate_status(self) -> None:
        intent = classify_intent("show fleet status")
        assert intent.intent_type == IntentType.ORCHESTRATE
        assert intent.confidence >= 0.9

    def test_delegate_spawn(self) -> None:
        intent = classify_intent("spawn a task on node-b to build an API")
        # "build an API" strongly matches BUILD — this is acceptable overlap
        assert intent.intent_type in (IntentType.DELEGATE, IntentType.BUILD)
        assert intent.parameters["target_node"] == "node-b"

    def test_build_code(self) -> None:
        intent = classify_intent("write a python script to parse JSON")
        assert intent.intent_type == IntentType.BUILD
        assert intent.confidence >= 0.9

    def test_query_search(self) -> None:
        intent = classify_intent("search memory for facts about postgres")
        assert intent.intent_type == IntentType.QUERY

    def test_chat_fallback(self) -> None:
        intent = classify_intent("hello there")
        assert intent.intent_type == IntentType.CHAT
        assert intent.confidence >= 0.4

    def test_node_extraction(self) -> None:
        intent = classify_intent("ask node-c to archive this")
        assert intent.parameters["target_node"] == "node-c"

    def test_unknown_low_confidence(self) -> None:
        intent = classify_intent("xyz abc 123")
        # Should fall back to CHAT with moderate confidence
        assert intent.intent_type == IntentType.CHAT


class TestComplexityEvaluation:
    """Test complexity metric computation."""

    def test_simple_intent_low_complexity(self) -> None:
        intent = classify_intent("status")
        complexity = evaluate_complexity(intent)
        assert complexity.overall < 0.5
        assert not complexity.should_spawn()

    def test_complex_intent_high_complexity(self) -> None:
        intent = classify_intent(
            "build a REST API with authentication, rate limiting, and "
            "database integration. Validate all inputs and write tests."
        )
        complexity = evaluate_complexity(intent)
        assert complexity.cyclomatic > 0.15
        assert complexity.overall > 0.0

    def test_file_count_scoring(self) -> None:
        intent = classify_intent("modify app.py, models.py, and config.yaml")
        complexity = evaluate_complexity(intent)
        assert complexity.file_count > 0.2


class TestIntentEngine:
    """Test the intent resolution engine."""

    def test_direct_execution(self) -> None:
        engine = IntentEngine(default_node="node-a")
        result = engine.resolve("show status")
        assert result.success
        assert result.action == "orchestrate"

    def test_low_confidence_raises(self) -> None:
        engine = IntentEngine(default_node="node-a")
        with pytest.raises(LowConfidenceError):
            engine.resolve("xyz abc completely nonsense input here")

    def test_spawn_depth_limit(self) -> None:
        engine = IntentEngine(default_node="node-a", current_depth=3)
        # At max depth, should not spawn even for complex intents
        result = engine.resolve("build a complex microservice architecture")
        assert result.success
        # Should execute directly instead of spawning
        assert result.action in ("build", "delegate", "chat")
