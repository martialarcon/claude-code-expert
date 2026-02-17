"""
AI Architect v2 - Claude Client Wrapper

Wraps the Claude CLI with retry logic, timeout handling, and JSON parsing.
"""

import json
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..utils.config import get_config, get_settings
from ..utils.logger import get_logger

log = get_logger("processor.claude_client")


class ClaudeModel(str, Enum):
    """Available Claude models."""
    SONNET = "claude-sonnet-4-20250514"
    OPUS = "claude-opus-4-6"


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
    Wrapper for Claude CLI with retry logic and JSON parsing.

    Uses the Claude CLI subprocess for API calls.
    """

    def __init__(
        self,
        model: ClaudeModel | None = None,
        timeout: int = 120,
        max_retries: int = 3,
    ):
        """
        Initialize Claude client.

        Args:
            model: Claude model to use (defaults to analysis model from config)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        config = get_config()
        self.model = model or ClaudeModel.SONNET
        self.timeout = timeout
        self.max_retries = max_retries
        self._settings = get_settings()

    def _build_command(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> list[str]:
        """Build Claude CLI command."""
        cmd = [
            "claude",
            "--model", self.model.value,
            "--max-tokens", str(max_tokens),
            "--output-format", "json",
            "--print",  # Output to stdout
        ]

        if system:
            cmd.extend(["--system", system])

        cmd.append(prompt)
        return cmd

    @retry(
        retry=retry_if_exception_type(ClaudeAPIError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def _execute(self, cmd: list[str]) -> str:
        """
        Execute Claude CLI command with retry logic.

        Args:
            cmd: Command and arguments

        Returns:
            Raw stdout output

        Raises:
            ClaudeTimeoutError: Command timed out
            ClaudeAPIError: API error (retryable)
        """
        log.debug("executing_claude", model=self.model.value, cmd=" ".join(cmd[:5]))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                log.error(
                    "claude_error",
                    returncode=result.returncode,
                    error=error_msg[:500],
                )

                # Check for rate limit or temporary errors (retryable)
                if "rate" in error_msg.lower() or "overloaded" in error_msg.lower():
                    raise ClaudeAPIError(f"Rate limited: {error_msg[:200]}")

                raise ClaudeAPIError(f"Claude error: {error_msg[:200]}")

            return result.stdout

        except subprocess.TimeoutExpired as e:
            log.error("claude_timeout", timeout=self.timeout)
            raise ClaudeTimeoutError(f"Claude request timed out after {self.timeout}s") from e

    def _parse_response(self, raw_output: str) -> ClaudeResponse:
        """
        Parse Claude CLI JSON output.

        Args:
            raw_output: Raw stdout from Claude CLI

        Returns:
            Parsed ClaudeResponse

        Raises:
            ClaudeParseError: Failed to parse output
        """
        try:
            # Claude CLI outputs JSON
            data = json.loads(raw_output.strip())

            content = data.get("content", "")
            if isinstance(content, list) and len(content) > 0:
                # Handle structured content blocks
                content = content[0].get("text", str(content[0]))

            return ClaudeResponse(
                content=content,
                model=data.get("model", self.model.value),
                usage=data.get("usage"),
                raw_output=raw_output,
                json_data=data if isinstance(data, dict) else None,
            )

        except json.JSONDecodeError as e:
            # Maybe it's plain text output
            if raw_output.strip():
                log.warning("claude_non_json_output", output=raw_output[:200])
                return ClaudeResponse(
                    content=raw_output.strip(),
                    model=self.model.value,
                    raw_output=raw_output,
                )
            raise ClaudeParseError(f"Failed to parse Claude output: {e}") from e

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
            ClaudeParseError: Failed to parse response
        """
        cmd = self._build_command(prompt, system, max_tokens)
        raw_output = self._execute(cmd)
        response = self._parse_response(raw_output)

        # Parse inner JSON if expecting JSON response
        if expect_json and response.content:
            try:
                # Try to extract JSON from markdown code blocks
                content = response.content
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    content = content[start:end].strip()
                elif "```" in content:
                    start = content.find("```") + 3
                    end = content.find("```", start)
                    content = content[start:end].strip()

                response.json_data = json.loads(content)
            except json.JSONDecodeError:
                log.warning("claude_json_parse_failed", content=response.content[:200])

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
    """Get Claude client configured for analysis (Sonnet)."""
    return ClaudeClient(model=ClaudeModel.SONNET)


def get_synthesis_client() -> ClaudeClient:
    """Get Claude client configured for synthesis (Opus)."""
    return ClaudeClient(model=ClaudeModel.OPUS, timeout=300)  # Longer timeout for synthesis
