"""
HTTP Client Infrastructure.

Domain-grouped clients for external API communication with centralized lifecycle management.

Clients:
- GenericHTTPClient: For harvesters (Reddit, PubMed, Pexels) - no auth, standard timeouts
- AnthropicClient: For LLM calls (Phases 3, 5, 6) - API key auth, longer timeouts
- ElevenLabsClient: For TTS (Phase 7) - API key auth, streaming support
"""

from app.services.clients.base import BaseHTTPClient
from app.services.clients.generic import GenericHTTPClient
from app.services.clients.anthropic import AnthropicClient
from app.services.clients.elevenlabs import ElevenLabsClient
from app.services.clients.manager import HTTPClientManager

__all__ = [
    "BaseHTTPClient",
    "GenericHTTPClient",
    "AnthropicClient",
    "ElevenLabsClient",
    "HTTPClientManager",
]
