"""Tests for SubagentInvoker module."""

import json
import pytest
from pathlib import Path
# Note: patch and MagicMock available for future mocking needs

from src.processors.subagent_invoker import (
    SubagentError,
    SubagentInvoker,
    invoke_ranker,
    invoke_analyzer,
    invoke_synthesizer,
    invoke_competitive,
)


class TestSubagentError:
    """Test SubagentError exception class."""

    def test_subagent_error_is_exception(self):
        """Should be an exception type."""
        assert issubclass(SubagentError, Exception)

    def test_subagent_error_with_message(self):
        """Should accept message argument."""
        error = SubagentError("Test error message")
        assert str(error) == "Test error message"

    def test_subagent_error_with_agent_name(self):
        """Should store agent name for context."""
        error = SubagentError("Test error", agent_name="test-agent")
        assert error.agent_name == "test-agent"


class TestSubagentInvokerInit:
    """Test SubagentInvoker initialization."""

    def test_init_with_agent_name(self):
        """Should initialize with agent name."""
        invoker = SubagentInvoker("test-agent")
        assert invoker.agent_name == "test-agent"

    def test_init_with_default_agents_dir(self):
        """Should use default agents directory if not specified."""
        invoker = SubagentInvoker("test-agent")
        # Default should be .claude/agents relative to project root
        assert invoker.agents_dir is not None

    def test_init_with_custom_agents_dir(self):
        """Should accept custom agents directory."""
        custom_path = Path("/custom/agents")
        invoker = SubagentInvoker("test-agent", agents_dir=custom_path)
        assert invoker.agents_dir == custom_path


class TestSubagentInvokerPrepareInput:
    """Test _prepare_input method."""

    def test_prepare_input_for_list(self):
        """Should serialize list to JSON string."""
        invoker = SubagentInvoker("test-agent")
        data = [{"title": "Item 1"}, {"title": "Item 2"}]
        result = invoker._prepare_input(data)
        assert json.loads(result) == data

    def test_prepare_input_for_list_adds_index(self):
        """Should add index field to list items for ranker."""
        invoker = SubagentInvoker("agent-ranker")
        data = [{"title": "Item 1"}, {"title": "Item 2"}]
        result = invoker._prepare_input(data)
        parsed = json.loads(result)
        assert parsed[0].get("index") == 0
        assert parsed[1].get("index") == 1

    def test_prepare_input_for_dict(self):
        """Should serialize dict to JSON string."""
        invoker = SubagentInvoker("test-agent")
        data = {"key": "value", "number": 42}
        result = invoker._prepare_input(data)
        assert json.loads(result) == data

    def test_prepare_input_preserves_original_list(self):
        """Should not modify original list when adding index."""
        invoker = SubagentInvoker("agent-ranker")
        data = [{"title": "Item 1"}]
        original_len = len(data)
        original_has_index = "index" in data[0]
        _ = invoker._prepare_input(data)
        # Original should be unchanged
        assert len(data) == original_len
        assert ("index" in data[0]) == original_has_index


class TestSubagentInvokerParseOutput:
    """Test _parse_output method."""

    def test_parse_output_plain_json(self):
        """Should parse plain JSON string."""
        invoker = SubagentInvoker("test-agent")
        output = '{"key": "value", "number": 42}'
        result = invoker._parse_output(output)
        assert result == {"key": "value", "number": 42}

    def test_parse_output_json_array(self):
        """Should parse JSON array."""
        invoker = SubagentInvoker("test-agent")
        output = '[{"id": 1}, {"id": 2}]'
        result = invoker._parse_output(output)
        assert result == [{"id": 1}, {"id": 2}]

    def test_parse_output_markdown_code_block_json(self):
        """Should extract JSON from markdown code blocks."""
        invoker = SubagentInvoker("test-agent")
        output = '''```json
{"key": "value"}
```'''
        result = invoker._parse_output(output)
        assert result == {"key": "value"}

    def test_parse_output_markdown_code_block_no_language(self):
        """Should extract JSON from markdown code blocks without language."""
        invoker = SubagentInvoker("test-agent")
        output = '''```
{"key": "value"}
```'''
        result = invoker._parse_output(output)
        assert result == {"key": "value"}

    def test_parse_output_embedded_json(self):
        """Should extract JSON embedded in text."""
        invoker = SubagentInvoker("test-agent")
        output = 'Here is the result: {"key": "value"} and that is it.'
        result = invoker._parse_output(output)
        assert result == {"key": "value"}

    def test_parse_output_embedded_json_array(self):
        """Should extract JSON array embedded in text."""
        invoker = SubagentInvoker("test-agent")
        output = 'Results:\n[{"score": 5}, {"score": 7}]\nEnd.'
        result = invoker._parse_output(output)
        assert result == [{"score": 5}, {"score": 7}]

    def test_parse_output_invalid_raises_error(self):
        """Should raise SubagentError on invalid output."""
        invoker = SubagentInvoker("test-agent")
        output = "This is not JSON at all"
        with pytest.raises(SubagentError):
            invoker._parse_output(output)


class TestSubagentInvokerMockInvoke:
    """Test _mock_invoke method for testing without real agent."""

    def test_mock_invoke_ranker(self):
        """Should return mock ranking response."""
        invoker = SubagentInvoker("agent-ranker")
        data = [{"title": "Test item"}]
        result = invoker._mock_invoke(data)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["signal_score"] == 5
        assert result[0]["impact"] == "ecosystem"
        assert result[0]["maturity"] == "growing"

    def test_mock_invoke_analyzer(self):
        """Should return mock analysis response."""
        invoker = SubagentInvoker("agent-analyzer")
        data = {"title": "Test item", "content": "Test content"}
        result = invoker._mock_invoke(data)

        assert isinstance(result, dict)
        assert "summary" in result
        assert "key_insights" in result
        assert result["actionability"] == "medium"
        assert result["confidence"] == 0.7

    def test_mock_invoke_synthesizer(self):
        """Should return mock synthesis response."""
        invoker = SubagentInvoker("agent-synthesizer")
        data = {"mode": "daily", "items": []}
        result = invoker._mock_invoke(data)

        assert isinstance(result, dict)
        assert "relevance_score" in result
        assert "highlights" in result
        assert "patterns" in result
        assert "recommendations" in result
        assert result["relevance_score"] == 5

    def test_mock_invoke_competitive(self):
        """Should return mock competitive analysis response."""
        invoker = SubagentInvoker("agent-competitive")
        data = {"week": "2026-W07", "items": []}
        result = invoker._mock_invoke(data)

        assert isinstance(result, dict)
        assert "week" in result
        assert "tools" in result
        assert "feature_gaps" in result
        assert "adoption_trends" in result
        assert "strategic_insights" in result


class TestSubagentInvokerInvoke:
    """Test invoke method."""

    def test_invoke_uses_mock_by_default(self):
        """Should use mock invoke in test mode."""
        invoker = SubagentInvoker("agent-ranker")
        data = [{"title": "Test"}]
        result = invoker.invoke(data)

        # Should return mock response
        assert isinstance(result, list)
        assert result[0]["signal_score"] == 5

    def test_invoke_with_timeout(self):
        """Should accept timeout parameter."""
        invoker = SubagentInvoker("agent-ranker")
        data = [{"title": "Test"}]
        # Should not raise
        result = invoker.invoke(data, timeout=60)
        assert result is not None

    def test_invoke_propagates_mock_response(self):
        """Should return parsed mock response."""
        invoker = SubagentInvoker("agent-analyzer")
        data = {"title": "Test"}
        result = invoker.invoke(data)

        assert "summary" in result
        assert "key_insights" in result


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_invoke_ranker_exists(self):
        """invoke_ranker should be callable."""
        assert callable(invoke_ranker)

    def test_invoke_ranker_returns_list(self):
        """invoke_ranker should return list of ranked items."""
        items = [{"title": "Item 1"}]
        result = invoke_ranker(items)

        assert isinstance(result, list)
        assert len(result) == 1
        assert "signal_score" in result[0]
        assert "impact" in result[0]
        assert "maturity" in result[0]

    def test_invoke_analyzer_exists(self):
        """invoke_analyzer should be callable."""
        assert callable(invoke_analyzer)

    def test_invoke_analyzer_returns_dict(self):
        """invoke_analyzer should return analysis dict."""
        item = {"title": "Test", "content": "Content"}
        result = invoke_analyzer(item)

        assert isinstance(result, dict)
        assert "summary" in result
        assert "key_insights" in result
        assert "actionability" in result
        assert "confidence" in result

    def test_invoke_synthesizer_exists(self):
        """invoke_synthesizer should be callable."""
        assert callable(invoke_synthesizer)

    def test_invoke_synthesizer_returns_dict(self):
        """invoke_synthesizer should return synthesis dict."""
        data = {"mode": "daily", "items": []}
        result = invoke_synthesizer(data)

        assert isinstance(result, dict)
        assert "relevance_score" in result
        assert "highlights" in result
        assert "patterns" in result
        assert "recommendations" in result

    def test_invoke_competitive_exists(self):
        """invoke_competitive should be callable."""
        assert callable(invoke_competitive)

    def test_invoke_competitive_returns_dict(self):
        """invoke_competitive should return competitive analysis dict."""
        data = {"week": "2026-W07", "items": []}
        result = invoke_competitive(data)

        assert isinstance(result, dict)
        assert "week" in result
        assert "tools" in result
        assert "feature_gaps" in result
        assert "adoption_trends" in result
        assert "strategic_insights" in result
