"""
Generic HTTP Client.

Used for harvesters and scrapers that don't require authentication:
- Reddit API (public JSON endpoints)
- PubMed API
- Pexels API (free tier)
- Misc web scraping
"""

import logging
from typing import Optional

from app.services.clients.base import BaseHTTPClient

logger = logging.getLogger(__name__)


class GenericHTTPClient(BaseHTTPClient):
    """
    Generic HTTP client for public API access.
    
    Features:
    - No authentication required
    - Standard 30s timeout
    - Full URLs (no base_url) for flexibility across domains
    - Configurable User-Agent
    """
    
    DEFAULT_USER_AGENT = "PrismaticEngine/1.0 (content research)"
    
    def __init__(
        self,
        timeout: float = 30.0,
        user_agent: Optional[str] = None,
    ):
        headers = {"User-Agent": user_agent or self.DEFAULT_USER_AGENT}
        super().__init__(
            base_url=None,  # Full URLs provided per request
            timeout=timeout,
            headers=headers,
            follow_redirects=True,
        )
    
    async def get_json(
        self,
        url: str,
        params: Optional[dict] = None,
    ) -> tuple[int, dict | list | None]:
        """
        Make a GET request and parse JSON response.
        
        Returns:
            Tuple of (status_code, json_data or None on parse failure)
        """
        response = await self.get(url, params=params)
        try:
            return response.status_code, response.json()
        except Exception:
            return response.status_code, None
