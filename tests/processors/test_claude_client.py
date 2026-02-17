"""Tests for ClaudeClient with Anthropic SDK."""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestClaudeClientInit:
    """Test ClaudeClient initialization."""

    def test_init_with_defaults(self):
        """Should initialize with default model."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient, ClaudeModel

            client = ClaudeClient()
            assert client.model == ClaudeModel.SONNET

    def test_init_with_custom_base_url(self):
        """Should use ANTHROPIC_BASE_URL from environment."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-key",
                "ANTHROPIC_BASE_URL": "https://custom.api.com"
            }
        ):
            from src.processors.claude_client import ClaudeClient

            client = ClaudeClient()
            assert client._base_url == "https://custom.api.com"

    def test_init_with_custom_model(self):
        """Should accept custom model parameter."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient, ClaudeModel

            client = ClaudeClient(model=ClaudeModel.OPUS)
            assert client.model == ClaudeModel.OPUS

    def test_init_with_explicit_base_url(self):
        """Should use explicitly passed base_url over environment."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-key",
                "ANTHROPIC_BASE_URL": "https://env.api.com"
            }
        ):
            from src.processors.claude_client import ClaudeClient

            client = ClaudeClient(base_url="https://explicit.api.com")
            assert client._base_url == "https://explicit.api.com"


class TestClaudeClientModels:
    """Test ClaudeModel enum."""

    def test_sonnet_model_value(self):
        """Should have correct Sonnet model value."""
        from src.processors.claude_client import ClaudeModel

        assert ClaudeModel.SONNET.value == "claude-sonnet-4-20250514"

    def test_opus_model_value(self):
        """Should have correct Opus model value."""
        from src.processors.claude_client import ClaudeModel

        assert ClaudeModel.OPUS.value == "claude-opus-4-6"

    def test_glm_models_available(self):
        """Should include GLM model variants."""
        from src.processors.claude_client import ClaudeModel

        assert ClaudeModel.GLM_5.value == "glm-5"
        assert ClaudeModel.GLM_4_FLASH.value == "glm-4-flash"


class TestClaudeClientComplete:
    """Test ClaudeClient complete method."""

    def test_complete_returns_response(self):
        """Should return ClaudeResponse with content."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient, ClaudeResponse

            client = ClaudeClient()

            # Mock the Anthropic client
            mock_response = MagicMock()
            mock_block = MagicMock()
            mock_block.text = "Test response content"
            mock_response.content = [mock_block]

            client._client.messages.create = MagicMock(return_value=mock_response)

            response = client.complete("Test prompt")

            assert isinstance(response, ClaudeResponse)
            assert response.content == "Test response content"

    def test_complete_with_system_prompt(self):
        """Should pass system prompt to API."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient

            client = ClaudeClient()

            mock_response = MagicMock()
            mock_block = MagicMock()
            mock_block.text = "Response"
            mock_response.content = [mock_block]

            client._client.messages.create = MagicMock(return_value=mock_response)

            client.complete("User prompt", system="System instructions")

            call_kwargs = client._client.messages.create.call_args[1]
            assert call_kwargs["system"] == "System instructions"

    def test_complete_with_expect_json(self):
        """Should parse JSON from response when expect_json=True."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient

            client = ClaudeClient()

            mock_response = MagicMock()
            mock_block = MagicMock()
            mock_block.text = '{"key": "value"}'
            mock_response.content = [mock_block]

            client._client.messages.create = MagicMock(return_value=mock_response)

            response = client.complete("Prompt", expect_json=True)

            assert response.json_data == {"key": "value"}

    def test_complete_json_from_markdown_block(self):
        """Should extract JSON from markdown code blocks."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient

            client = ClaudeClient()

            mock_response = MagicMock()
            mock_block = MagicMock()
            mock_block.text = '```json\n{"key": "value"}\n```'
            mock_response.content = [mock_block]

            client._client.messages.create = MagicMock(return_value=mock_response)

            response = client.complete("Prompt", expect_json=True)

            assert response.json_data == {"key": "value"}


class TestClaudeClientCompleteJson:
    """Test ClaudeClient complete_json method."""

    def test_complete_json_returns_dict(self):
        """Should return parsed JSON dict."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient

            client = ClaudeClient()

            mock_response = MagicMock()
            mock_block = MagicMock()
            mock_block.text = '{"result": "success"}'
            mock_response.content = [mock_block]

            client._client.messages.create = MagicMock(return_value=mock_response)

            result = client.complete_json("Prompt")

            assert result == {"result": "success"}

    def test_complete_json_raises_on_invalid_json(self):
        """Should raise ClaudeParseError on invalid JSON."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient, ClaudeParseError

            client = ClaudeClient()

            mock_response = MagicMock()
            mock_block = MagicMock()
            mock_block.text = "Not valid JSON"
            mock_response.content = [mock_block]

            client._client.messages.create = MagicMock(return_value=mock_response)

            with pytest.raises(ClaudeParseError):
                client.complete_json("Prompt")


class TestClaudeClientAnalyze:
    """Test ClaudeClient analyze method."""

    def test_analyze_formats_prompt(self):
        """Should format content into prompt template."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient

            client = ClaudeClient()

            mock_response = MagicMock()
            mock_block = MagicMock()
            mock_block.text = "Analysis result"
            mock_response.content = [mock_block]

            client._client.messages.create = MagicMock(return_value=mock_response)

            response = client.analyze("Sample content", "Analyze this: {content}")

            assert response.content == "Analysis result"

            call_kwargs = client._client.messages.create.call_args[1]
            assert call_kwargs["messages"][0]["content"] == "Analyze this: Sample content"


class TestClaudeClientErrors:
    """Test error handling."""

    def test_timeout_error(self):
        """Should raise ClaudeTimeoutError on timeout."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient, ClaudeTimeoutError
            from anthropic import APITimeoutError

            client = ClaudeClient()

            client._client.messages.create = MagicMock(
                side_effect=APITimeoutError("Timeout")
            )

            with pytest.raises(ClaudeTimeoutError):
                client.complete("Prompt")

    def test_api_error_retryable(self):
        """Should raise ClaudeAPIError for rate limit errors."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient, ClaudeAPIError
            from anthropic import APIError

            client = ClaudeClient()

            # Create a mock request object for APIError
            mock_request = MagicMock()
            client._client.messages.create = MagicMock(
                side_effect=APIError("rate limited", request=mock_request, body=None)
            )

            with pytest.raises(ClaudeAPIError):
                client.complete("Prompt")
