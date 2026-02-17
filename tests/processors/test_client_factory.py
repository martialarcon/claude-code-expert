"""Tests for client factory."""

import os
from unittest.mock import patch, MagicMock


class TestClientFactory:
    """Test client factory functions."""

    @patch("src.processors.client_factory.ClaudeClient")
    def test_get_analysis_client_returns_claude_client(self, mock_client):
        """Should return ClaudeClient instance."""
        from src.processors.client_factory import get_analysis_client

        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        result = get_analysis_client()
        assert result is not None
        mock_client.assert_called()

    @patch("src.processors.client_factory.ClaudeClient")
    def test_get_synthesis_client_returns_claude_client(self, mock_client):
        """Should return ClaudeClient instance with longer timeout."""
        from src.processors.client_factory import get_synthesis_client

        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        result = get_synthesis_client()
        assert result is not None
        mock_client.assert_called()
