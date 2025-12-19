"""
Base Harvester Protocol.

Defines the interface for all content harvesters in the Prismatic Engine.
"""

from abc import ABC, abstractmethod
from typing import List


class BaseHarvester(ABC):
    """
    Abstract base class for content harvesters.

    Harvesters are responsible for:
    - Calling external APIs
    - Parsing responses
    - Returning plain Python data

    Harvesters must NOT:
    - Write to database
    - Perform status transitions
    - Contain business logic beyond parsing
    """

    @abstractmethod
    async def fetch(self, **kwargs) -> List[dict]:
        """
        Fetch raw data from external source.

        Returns:
            List of raw data dicts from the source
        """
        pass

    @abstractmethod
    def parse(self, raw_data: List[dict], **kwargs) -> List[dict]:
        """
        Parse raw data into structured format.

        Args:
            raw_data: List of raw dicts from fetch

        Returns:
            List of parsed, structured dicts ready for storage
        """
        pass
