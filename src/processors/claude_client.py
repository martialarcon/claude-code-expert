"""
AI Architect v2 - Claude Client Wrapper

Wraps the Anthropic SDK with retry logic, timeout handling, and JSON parsing.
Configurable base_url for GLM proxy support.
"""

import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

from anthropic import Anthropic, APIError, APITimeoutError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger("processor.claude_client")


class ClaudeModel(str, Enum):
    """Available Claude models (or GLM equivalents)."""
    SONNET = "claude-sonnet-4-20250514"
    OPUS = "claude-opus-4-6"
    GLM_5 = "glm-5"
    GLM_4_FLASH = "glm-4-flash"


@dataclass
class ClaudeResponse:
    """Response from Claude API."""
    content: str
    model: str
    usage: dict[str, int] | None = None
    raw_output: str | None = None
    json_data: dict[str, Any] | None = None


class ClaudeClientError(Exception):
    """Base error for Claude client."""
    pass


class ClaudeTimeoutError(ClaudeClientError):
    """Claude request timed out."""
    pass


class ClaudeAPIError(ClaudeClientError):
    """Claude API returned an error."""
    pass


class ClaudeParseError(ClaudeClientError):
    """Failed to parse Claude response."""
    pass


class ClaudeClient:
    """
    Wrapper for Anthropic SDK with retry logic and JSON parsing.

    Supports custom base_url for GLM proxy compatibility.
    """

    def __init__(
        self,
        model: ClaudeModel | None = None,
        timeout: int = 120,
        max_retries: int = 3,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """
        Initialize Claude client.

        Args:
            model: Claude model to use (defaults to analysis model from config)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            api_key: API key (defaults to ANTHROPIC_API_KEY env var)
            base_url: API base URL (defaults to ANTHROPIC_BASE_URL env var)
        """
        config = get_config()
        self.model = model or ClaudeModel.SONNET
        self.timeout = timeout
        self.max_retries = max_retries

        # Get API credentials
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")

        if not self._api_key:
            log.warning("anthropic_api_key_not_set")

        # Initialize Anthropic client
        client_kwargs = {"api_key": self._api_key, "timeout": self.timeout}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url

        self._client = Anthropic(**client_kwargs)
        log.debug("claude_client_initialized", model=self.model.value, base_url=self._base_url)

    @retry(
        retry=retry_if_exception_type(ClaudeAPIError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def _execute(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """
        Execute API request with retry logic.

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Maximum tokens in response

        Returns:
            Raw text response

        Raises:
            ClaudeTimeoutError: Request timed out
            ClaudeAPIError: API error (retryable)
        """
        log.debug("executing_anthropic", model=self.model.value)

        try:
            kwargs = {
                "model": self.model.value,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }

            if system:
                kwargs["system"] = system

            response = self._client.messages.create(**kwargs)

            # Extract text from content blocks
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            return content

        except APITimeoutError as e:
            log.error("anthropic_timeout", timeout=self.timeout)
            raise ClaudeTimeoutError(f"Request timed out after {self.timeout}s") from e

        except APIError as e:
            error_msg = str(e)[:500]
            log.error("anthropic_api_error", error=error_msg)

            # Check for rate limit or temporary errors (retryable)
            if "rate" in error_msg.lower() or "overload" in error_msg.lower():
                raise ClaudeAPIError(f"Rate limited: {error_msg}")

            raise ClaudeAPIError(f"API error: {error_msg}") from e

    def _parse_json_from_content(self, content: str) -> dict[str, Any] | None:
        """Extract and parse JSON from content."""
        try:
            # Try direct parse
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            try:
                return json.loads(content[start:end].strip())
            except json.JSONDecodeError:
                pass

        if "```" in content:
            start = content.find("```") + 3
            # Skip language identifier if present
            newline_pos = content.find("\n", start)
            if newline_pos > start:
                start = newline_pos + 1
            end = content.find("```", start)
            try:
                return json.loads(content[start:end].strip())
            except json.JSONDecodeError:
                pass

        return None

    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
        expect_json: bool = False,
    ) -> ClaudeResponse:
        """
        Send a completion request to Claude.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            max_tokens: Maximum tokens in response
            expect_json: Whether to parse response as JSON

        Returns:
            ClaudeResponse with content and metadata

        Raises:
            ClaudeTimeoutError: Request timed out
            ClaudeAPIError: API error
            ClaudeParseError: Failed to parse response as JSON (when expect_json=True)
        """
        content = self._execute(prompt, system, max_tokens)

        response = ClaudeResponse(
            content=content,
            model=self.model.value,
        )

        # Parse JSON if expected
        if expect_json and content:
            json_data = self._parse_json_from_content(content)
            if json_data:
                response.json_data = json_data
            else:
                log.warning("claude_json_parse_failed", content=content[:200])

        log.info(
            "claude_complete",
            model=self.model.value,
            content_length=len(response.content),
            has_json=response.json_data is not None,
        )

        return response

    def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """
        Send a completion request and return parsed JSON.

        Args:
            prompt: User prompt (should request JSON output)
            system: System prompt (optional)
            max_tokens: Maximum tokens in response

        Returns:
            Parsed JSON dict

        Raises:
            ClaudeTimeoutError: Request timed out
            ClaudeAPIError: API error
            ClaudeParseError: Failed to parse response as JSON
        """
        response = self.complete(prompt, system, max_tokens, expect_json=True)

        if response.json_data is None:
            raise ClaudeParseError("Expected JSON response but got: " + response.content[:200])

        return response.json_data

    def analyze(
        self,
        content: str,
        prompt_template: str,
    ) -> ClaudeResponse:
        """
        Analyze content using a prompt template.

        Convenience method for common analysis pattern.

        Args:
            content: Content to analyze
            prompt_template: Template with {content} placeholder

        Returns:
            ClaudeResponse
        """
        prompt = prompt_template.format(content=content)
        return self.complete(prompt)


# Convenience functions for common use cases
def get_analysis_client() -> ClaudeClient:
    """Get Claude client configured for analysis (Sonnet/GLM-5)."""
    config = get_config()
    model_str = config.models.analysis or "glm-5"
    try:
        model = ClaudeModel(model_str)
    except ValueError:
        # Map GLM model names
        if "glm" in model_str.lower():
            model = ClaudeModel.GLM_5
        else:
            model = ClaudeModel.SONNET
    return ClaudeClient(model=model)


def get_synthesis_client() -> ClaudeClient:
    """Get Claude client configured for synthesis (Opus/GLM-5)."""
    config = get_config()
    model_str = config.models.synthesis or "glm-5"
    try:
        model = ClaudeModel(model_str)
    except ValueError:
        if "glm" in model_str.lower():
            model = ClaudeModel.GLM_5
        else:
            model = ClaudeModel.OPUS
    return ClaudeClient(model=model, timeout=300)  # Longer timeout for synthesis
