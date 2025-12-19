"""
Base HTTP Client Protocol.

Defines the interface for all HTTP clients in the Prismatic Engine.
All domain-specific clients should implement this protocol.
"""

import logging
from abc import ABC
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class BaseHTTPClient(ABC):
    """
    Abstract base class for HTTP clients.

    All clients must implement startup/shutdown lifecycle methods
    and provide standard HTTP operations.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        headers: Optional[dict[str, str]] = None,
        follow_redirects: bool = True,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.default_headers = headers or {}
        self.follow_redirects = follow_redirects
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client_name(self) -> str:
        """Human-readable name for logging."""
        return self.__class__.__name__

    async def startup(self) -> None:
        """Initialize the httpx.AsyncClient."""
        client_kwargs = {
            "timeout": self.timeout,
            "headers": self.default_headers,
            "follow_redirects": self.follow_redirects,
        }

        # Only add base_url if it's not None
        if self.base_url is not None:
            client_kwargs["base_url"] = self.base_url

        self._client = httpx.AsyncClient(**client_kwargs)

    async def shutdown(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info(f"🛑 {self.client_name} closed")

    def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure client is initialized before use."""
        if self._client is None:
            raise RuntimeError(
                f"{self.client_name}: Client not initialized. "
                "Call startup() before making requests."
            )
        return self._client

    async def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a GET request."""
        client = self._ensure_client()
        return await client.get(url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        json: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a POST request."""
        client = self._ensure_client()
        return await client.post(url, json=json, data=data, headers=headers)

    async def __aenter__(self) -> "BaseHTTPClient":
        """Async context manager entry."""
        await self.startup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.shutdown()
