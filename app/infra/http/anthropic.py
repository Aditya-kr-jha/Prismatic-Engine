"""
Anthropic API Client.

Used for all Claude LLM calls across phases:
- Phase 3: Content processing
- Phase 5: Content generation
- Phase 6: Quality review
"""

import logging
from typing import Any, Optional

from app.infra.http.base import BaseHTTPClient

logger = logging.getLogger(__name__)


class AnthropicClient(BaseHTTPClient):
    """
    HTTP client for Anthropic Claude API.

    Features:
    - API key authentication via x-api-key header
    - Longer timeout (120s) for LLM inference
    - Anthropic-specific headers

    Note: This is a low-level HTTP client. For production LLM usage,
    consider using langchain-anthropic which provides higher-level
    abstractions. This client exists for direct API access when needed.
    """

    BASE_URL = "https://api.anthropic.com"
    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.api_key = api_key

        headers = {
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        # Only add API key header if provided
        if api_key:
            headers["x-api-key"] = api_key

        super().__init__(
            base_url=self.BASE_URL,
            timeout=timeout,
            headers=headers,
            follow_redirects=False,
        )

    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    async def create_message(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 4096,
        system: Optional[str] = None,
    ) -> tuple[int, dict | None]:
        """
        Create a message using the Claude API.

        Args:
            model: Model identifier (e.g., "claude-sonnet-4-20250514")
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            system: Optional system prompt

        Returns:
            Tuple of (status_code, response_json or None)
        """
        if not self.is_configured:
            logger.error("AnthropicClient: API key not configured")
            return 401, None

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        if system:
            payload["system"] = system

        response = await self.post("/v1/messages", json=payload)

        try:
            return response.status_code, response.json()
        except Exception:
            return response.status_code, None
