"""
AI Architect v2 - GLM Client Wrapper

Alternative client for ZhipuAI GLM models.
Supports GLM-4, GLM-4-Plus, GLM-4-Flash, etc.
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..utils.config import get_settings
from ..utils.logger import get_logger

log = get_logger("processor.glm_client")


class GLMModel(str, Enum):
    """Available GLM models."""
    GLM_4 = "glm-4"
    GLM_4_PLUS = "glm-4-plus"
    GLM_4_FLASH = "glm-4-flash"      # Faster, cheaper
    GLM_4_LONG = "glm-4-long"        # Long context


@dataclass
class GLMResponse:
    """Response from GLM API."""
    content: str
    model: str
    usage: dict[str, int] | None = None
    raw_output: str | None = None
    json_data: dict[str, Any] | None = None


class GLMClientError(Exception):
    """Base error for GLM client."""
    pass


class GLMTimeoutError(GLMClientError):
    """GLM request timed out."""
    pass


class GLMAPIError(GLMClientError):
    """GLM API returned an error."""
    pass


class GLMClient:
    """
    Client for ZhipuAI GLM models.

    API Documentation: https://open.bigmodel.cn/dev/api
    """

    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(
        self,
        model: GLMModel = GLMModel.GLM_4_FLASH,
        api_key: str | None = None,
        timeout: int = 120,
        max_retries: int = 3,
    ):
        """
        Initialize GLM client.

        Args:
            model: GLM model to use
            api_key: ZhipuAI API key (from env ZHIPUAI_API_KEY)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.model = model
        settings = get_settings()
        self.api_key = api_key or settings.glm_api_key or ""
        self.timeout = timeout
        self.max_retries = max_retries

        if not self.api_key:
            log.warning("glm_api_key_not_set")

    def _build_request(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Build API request body."""
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        return {
            "model": self.model.value,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

    @retry(
        retry=retry_if_exception_type(GLMAPIError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def _execute(self, request_body: dict[str, Any]) -> dict[str, Any]:
        """
        Execute API request with retry logic.

        Args:
            request_body: Request payload

        Returns:
            API response JSON

        Raises:
            GLMTimeoutError: Request timed out
            GLMAPIError: API error
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        log.debug("executing_glm", model=self.model.value)

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.API_URL,
                    headers=headers,
                    json=request_body,
                )

            if response.status_code != 200:
                error_msg = response.text[:500]
                log.error(
                    "glm_api_error",
                    status_code=response.status_code,
                    error=error_msg,
                )

                if response.status_code in [429, 503]:
                    raise GLMAPIError(f"Rate limited: {error_msg}")

                raise GLMAPIError(f"GLM API error: {error_msg}")

            return response.json()

        except httpx.TimeoutException as e:
            log.error("glm_timeout", timeout=self.timeout)
            raise GLMTimeoutError(f"GLM request timed out after {self.timeout}s") from e

        except httpx.HTTPError as e:
            log.error("glm_http_error", error=str(e)[:200])
            raise GLMAPIError(f"HTTP error: {str(e)[:200]}") from e

    def _parse_response(self, response_json: dict[str, Any]) -> GLMResponse:
        """Parse API response."""
        choices = response_json.get("choices", [])
        if not choices:
            raise GLMAPIError("No choices in response")

        content = choices[0].get("message", {}).get("content", "")
        usage = response_json.get("usage", {})

        return GLMResponse(
            content=content,
            model=response_json.get("model", self.model.value),
            usage=usage,
            raw_output=json.dumps(response_json),
        )

    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
        expect_json: bool = False,
    ) -> GLMResponse:
        """
        Send a completion request to GLM.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            max_tokens: Maximum tokens in response
            expect_json: Whether to parse response as JSON

        Returns:
            GLMResponse with content and metadata
        """
        request_body = self._build_request(prompt, system, max_tokens)
        response_json = self._execute(request_body)
        response = self._parse_response(response_json)

        # Parse JSON if expected
        if expect_json and response.content:
            try:
                content = response.content
                # Extract JSON from markdown code blocks
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
                log.warning("glm_json_parse_failed", content=response.content[:200])

        log.info(
            "glm_complete",
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
            prompt: User prompt
            system: System prompt
            max_tokens: Maximum tokens

        Returns:
            Parsed JSON dict
        """
        response = self.complete(prompt, system, max_tokens, expect_json=True)

        if response.json_data is None:
            raise GLMClientError("Expected JSON but got: " + response.content[:200])

        return response.json_data


# Convenience functions
def get_glm_analysis_client() -> GLMClient:
    """Get GLM client for analysis (GLM-4-Flash for speed)."""
    return GLMClient(model=GLMModel.GLM_4_FLASH)


def get_glm_synthesis_client() -> GLMClient:
    """Get GLM client for synthesis (GLM-4-Plus for quality)."""
    return GLMClient(model=GLMModel.GLM_4_PLUS, timeout=300)
