"""
ElevenLabs API Client.

Used for Text-to-Speech generation in Phase 7.
"""

import logging
from typing import AsyncIterator, Optional

import httpx

from app.services.clients.base import BaseHTTPClient

logger = logging.getLogger(__name__)


class ElevenLabsClient(BaseHTTPClient):
    """
    HTTP client for ElevenLabs TTS API.
    
    Features:
    - API key authentication via xi-api-key header
    - Streaming support for audio generation
    - Binary response handling
    """
    
    BASE_URL = "https://api.elevenlabs.io"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }
        
        if api_key:
            headers["xi-api-key"] = api_key
        
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
    
    async def text_to_speech(
        self,
        voice_id: str,
        text: str,
        model_id: str = "eleven_monolingual_v1",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> tuple[int, bytes | None]:
        """
        Convert text to speech audio.
        
        Args:
            voice_id: ElevenLabs voice ID
            text: Text to convert to speech
            model_id: TTS model to use
            stability: Voice stability (0.0-1.0)
            similarity_boost: Voice similarity boost (0.0-1.0)
            
        Returns:
            Tuple of (status_code, audio_bytes or None)
        """
        if not self.is_configured:
            logger.error("ElevenLabsClient: API key not configured")
            return 401, None
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        }
        
        response = await self.post(f"/v1/text-to-speech/{voice_id}", json=payload)
        
        if response.status_code == 200:
            return response.status_code, response.content
        return response.status_code, None
    
    async def text_to_speech_stream(
        self,
        voice_id: str,
        text: str,
        model_id: str = "eleven_monolingual_v1",
    ) -> AsyncIterator[bytes]:
        """
        Stream text-to-speech audio chunks.
        
        Yields audio chunks as they are generated.
        """
        if not self.is_configured:
            logger.error("ElevenLabsClient: API key not configured")
            return
        
        client = self._ensure_client()
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        
        async with client.stream(
            "POST",
            f"/v1/text-to-speech/{voice_id}/stream",
            json=payload,
        ) as response:
            if response.status_code == 200:
                async for chunk in response.aiter_bytes():
                    yield chunk
            else:
                logger.error(f"ElevenLabs streaming failed: {response.status_code}")
