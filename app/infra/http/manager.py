"""
HTTP Client Manager.

Centralized lifecycle management for all HTTP clients.
Wired into FastAPI lifespan for proper startup/shutdown.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.config import settings
from app.infra.http.anthropic import AnthropicClient
from app.infra.http.elevenlabs import ElevenLabsClient
from app.infra.http.generic import GenericHTTPClient

logger = logging.getLogger(__name__)


@dataclass
class HTTPClientManager:
    """
    Manages all HTTP clients with centralized lifecycle control.

    Usage:
        # In FastAPI lifespan
        manager = HTTPClientManager()
        await manager.startup()
        app.state.clients = manager
        # ... app runs ...
        await manager.shutdown()

    Attributes:
        generic: Client for public APIs (Reddit, PubMed, Pexels)
        anthropic: Client for Claude LLM API
        elevenlabs: Client for TTS API
    """

    generic: Optional[GenericHTTPClient] = None
    anthropic: Optional[AnthropicClient] = None
    elevenlabs: Optional[ElevenLabsClient] = None

    async def startup(self) -> None:
        """Initialize all HTTP clients."""
        logger.info("🔌 HTTPClientManager: Starting clients...")

        # Generic client for harvesters
        self.generic = GenericHTTPClient(
            timeout=getattr(settings, "HTTP_TIMEOUT_DEFAULT", 30.0),
            user_agent="PrismaticEngine/1.0 (content research)",
        )
        await self.generic.startup()

        # Anthropic client for LLM calls
        anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", None)
        self.anthropic = AnthropicClient(
            api_key=anthropic_key,
            timeout=getattr(settings, "HTTP_TIMEOUT_LLM", 120.0),
        )
        await self.anthropic.startup()

        if not anthropic_key:
            logger.warning("⚠️  ANTHROPIC_API_KEY not configured - LLM calls will fail")

        # ElevenLabs client for TTS
        elevenlabs_key = getattr(settings, "ELEVENLABS_API_KEY", None)
        self.elevenlabs = ElevenLabsClient(
            api_key=elevenlabs_key,
            timeout=60.0,
        )
        await self.elevenlabs.startup()

        if not elevenlabs_key:
            logger.warning("⚠️  ELEVENLABS_API_KEY not configured - TTS calls will fail")

        logger.info("🔌 HTTPClientManager: All clients ready")

    async def shutdown(self) -> None:
        """Close all HTTP clients gracefully."""
        logger.info("🔌 HTTPClientManager: Shutting down clients...")

        if self.generic:
            await self.generic.shutdown()

        if self.anthropic:
            await self.anthropic.shutdown()

        if self.elevenlabs:
            await self.elevenlabs.shutdown()

        logger.info("🔌 HTTPClientManager: All clients closed")

    async def __aenter__(self) -> "HTTPClientManager":
        """Async context manager entry."""
        await self.startup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.shutdown()
