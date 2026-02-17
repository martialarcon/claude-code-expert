# Anthropic SDK Client Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Claude CLI subprocess client with Anthropic Python SDK configured for GLM proxy.

**Architecture:** Single ClaudeClient using Anthropic SDK with configurable base_url. Simplified client_factory returns ClaudeClient. GLM client deleted.

**Tech Stack:** Python 3.11, anthropic SDK >= 0.40.0, httpx (existing), tenacity (existing)

---

## Prerequisites

- Docker environment working
- `.env` configured with `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL`

---

### Task 1: Add Anthropic SDK Dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add anthropic to requirements**

```diff
# requirements.txt

# HTTP & Parsing
httpx>=0.25.0
+ anthropic>=0.40.0
feedparser>=6.0
```

**Step 2: Verify syntax**

Run: `cat requirements.txt | grep anthropic`
Expected: `anthropic>=0.40.0`

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add anthropic SDK dependency"
```

---

### Task 2: Rewrite ClaudeClient with Anthropic SDK

**Files:**
- Modify: `src/processors/claude_client.py`
- Create: `tests/processors/test_claude_client.py`

**Step 1: Write failing test for ClaudeClient initialization**

```python
# tests/processors/test_claude_client.py
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
```

**Step 2: Run test to verify it fails**

Run: `cd /home/jetson/developer/projects/claude-code-expert && python -m pytest tests/processors/test_claude_client.py -v`
Expected: FAIL (test file exists but ClaudeClient doesn't have _base_url)

**Step 3: Rewrite ClaudeClient implementation**

```python
# src/processors/claude_client.py
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
```

**Step 4: Run test to verify it passes**

Run: `cd /home/jetson/developer/projects/claude-code-expert && python -m pytest tests/processors/test_claude_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/processors/claude_client.py tests/processors/test_claude_client.py
git commit -m "feat: rewrite ClaudeClient with Anthropic SDK

- Replace subprocess CLI calls with anthropic SDK
- Add ANTHROPIC_BASE_URL support for GLM proxy
- Maintain backward-compatible interface"
```

---

### Task 3: Write Integration Test for ClaudeClient

**Files:**
- Modify: `tests/processors/test_claude_client.py`

**Step 1: Add integration test with mocked Anthropic SDK**

```python
# Add to tests/processors/test_claude_client.py

class TestClaudeClientComplete:
    """Test ClaudeClient complete method."""

    @patch("src.processors.claude_client.Anthropic")
    def test_complete_returns_response(self, mock_anthropic):
        """Should return ClaudeResponse with content."""
        # Setup mock
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_block = MagicMock()
        mock_block.text = "Test response"
        mock_message.content = [mock_block]
        mock_client.messages.create.return_value = mock_message

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient

            client = ClaudeClient()
            response = client.complete("Hello")

            assert response.content == "Test response"
            mock_client.messages.create.assert_called_once()

    @patch("src.processors.claude_client.Anthropic")
    def test_complete_json_parses_json(self, mock_anthropic):
        """Should parse JSON from response."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_block = MagicMock()
        mock_block.text = '{"key": "value"}'
        mock_message.content = [mock_block]
        mock_client.messages.create.return_value = mock_message

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from src.processors.claude_client import ClaudeClient

            client = ClaudeClient()
            result = client.complete_json("Return JSON")

            assert result == {"key": "value"}
```

**Step 2: Run tests**

Run: `cd /home/jetson/developer/projects/claude-code-expert && python -m pytest tests/processors/test_claude_client.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/processors/test_claude_client.py
git commit -m "test: add ClaudeClient integration tests with mocked SDK"
```

---

### Task 4: Simplify client_factory.py

**Files:**
- Modify: `src/processors/client_factory.py`
- Create: `tests/processors/test_client_factory.py`

**Step 1: Write test for simplified factory**

```python
# tests/processors/test_client_factory.py
"""Tests for client factory."""

import os
from unittest.mock import patch, MagicMock

class TestClientFactory:
    """Test client factory functions."""

    @patch("src.processors.client_factory.ClaudeClient")
    def test_get_analysis_client_returns_claude_client(self, mock_client):
        """Should return ClaudeClient instance."""
        from src.processors.client_factory import get_analysis_client

        result = get_analysis_client()
        assert result is not None

    @patch("src.processors.client_factory.ClaudeClient")
    def test_get_synthesis_client_returns_claude_client(self, mock_client):
        """Should return ClaudeClient instance with longer timeout."""
        from src.processors.client_factory import get_synthesis_client

        result = get_synthesis_client()
        assert result is not None
```

**Step 2: Run test to verify current behavior**

Run: `cd /home/jetson/developer/projects/claude-code-expert && python -m pytest tests/processors/test_client_factory.py -v`
Expected: Tests should work with current factory

**Step 3: Simplify client_factory.py**

```python
# src/processors/client_factory.py
"""
AI Architect v2 - Client Factory

Factory that creates LLM clients.
Currently uses ClaudeClient with Anthropic SDK (supports GLM proxy via ANTHROPIC_BASE_URL).
"""

from .claude_client import ClaudeClient, ClaudeModel
from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger("processor.client_factory")


def get_analysis_client() -> ClaudeClient:
    """
    Get LLM client configured for analysis tasks.

    Returns ClaudeClient configured with analysis model.
    """
    config = get_config()
    model_str = config.models.analysis or "glm-5"

    try:
        model = ClaudeModel(model_str)
    except ValueError:
        # Default to GLM-5 for proxy setups
        model = ClaudeModel.GLM_5

    log.debug("creating_analysis_client", model=model.value)
    return ClaudeClient(model=model)


def get_synthesis_client() -> ClaudeClient:
    """
    Get LLM client configured for synthesis tasks.

    Returns ClaudeClient with longer timeout for synthesis operations.
    """
    config = get_config()
    model_str = config.models.synthesis or "glm-5"

    try:
        model = ClaudeModel(model_str)
    except ValueError:
        model = ClaudeModel.GLM_5

    log.debug("creating_synthesis_client", model=model.value)
    return ClaudeClient(model=model, timeout=300)
```

**Step 4: Run tests**

Run: `cd /home/jetson/developer/projects/claude-code-expert && python -m pytest tests/processors/test_client_factory.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/processors/client_factory.py tests/processors/test_client_factory.py
git commit -m "refactor: simplify client_factory to use ClaudeClient only"
```

---

### Task 5: Delete GLM Client

**Files:**
- Delete: `src/processors/glm_client.py`

**Step 1: Remove glm_client.py**

Run: `rm src/processors/glm_client.py`

**Step 2: Verify no imports reference glm_client**

Run: `grep -r "glm_client" src/`
Expected: No matches

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: remove glm_client.py (using Anthropic SDK with proxy)"
```

---

### Task 6: Update Docker Configuration

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Add environment variables to docker-compose.yml**

```yaml
# docker-compose.yml - update environment section
environment:
  - PYTHONUNBUFFERED=1
  - LOG_LEVEL=${LOG_LEVEL:-INFO}
  - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
  - ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-https://api.z.ai/api/anthropic}
  - API_TIMEOUT_MS=${API_TIMEOUT_MS:-3000000}
```

**Step 2: Verify yaml syntax**

Run: `docker compose config --quiet && echo "Valid"`
Expected: `Valid`

**Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add ANTHROPIC_BASE_URL env var to docker-compose"
```

---

### Task 7: Update config.yaml

**Files:**
- Modify: `config.yaml`

**Step 1: Update provider setting**

```yaml
# config.yaml - update models section
models:
  provider: "anthropic"           # Using Anthropic SDK with GLM proxy
  analysis: "glm-5"               # GLM-5 for analysis
  synthesis: "glm-5"              # GLM-5 for synthesis
```

**Step 2: Commit**

```bash
git add config.yaml
git commit -m "chore: update config.yaml provider to anthropic"
```

---

### Task 8: Update .env.example

**Files:**
- Modify: `.env.example`

**Step 1: Document new environment variables**

```bash
# .env.example - add these lines
# Anthropic API Configuration (works with GLM proxy)
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
API_TIMEOUT_MS=3000000
```

**Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: update .env.example with Anthropic proxy vars"
```

---

### Task 9: Rebuild and Test

**Files:**
- None (testing only)

**Step 1: Rebuild Docker image**

Run: `docker compose down && docker compose build --no-cache`
Expected: Build succeeds

**Step 2: Start container**

Run: `docker compose up -d`
Expected: Container starts healthy

**Step 3: Check logs for successful API calls**

Run: `sleep 30 && docker logs ai-architect --tail 50`
Expected: Logs show `executing_anthropic` and successful responses (not API errors)

**Step 4: Verify output generated**

Run: `ls -la output/daily/`
Expected: Daily digest file created

---

### Task 10: Final Commit and Cleanup

**Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

**Step 2: Final commit with all changes**

```bash
git add -A
git status
git commit -m "feat: migrate to Anthropic SDK with GLM proxy support

- Replace CLI subprocess with anthropic Python SDK
- Add ANTHROPIC_BASE_URL support for GLM proxy
- Remove native GLM client (using proxy instead)
- Update Docker configuration
- Update config.yaml and .env.example"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add anthropic SDK | requirements.txt |
| 2 | Rewrite ClaudeClient | src/processors/claude_client.py |
| 3 | Add integration tests | tests/processors/test_claude_client.py |
| 4 | Simplify factory | src/processors/client_factory.py |
| 5 | Delete GLM client | src/processors/glm_client.py |
| 6 | Update Docker | docker-compose.yml |
| 7 | Update config | config.yaml |
| 8 | Update env example | .env.example |
| 9 | Rebuild and test | - |
| 10 | Final commit | - |
