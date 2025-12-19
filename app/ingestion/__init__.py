"""
Ingestion Package for Prismatic Engine.

Contains harvesters, validators, services, and DB operations for Phase 1 ingestion.
"""

from app.ingestion.harvesters.reddit import (
    RedditHarvester,
    HarvesterConfig,
    RawRedditPost,
    HarvestFetchResult,
)
from app.ingestion.service import IngestionService, IngestionResult

__all__ = [
    # Harvesters
    "RedditHarvester",
    "HarvesterConfig",
    "RawRedditPost",
    "HarvestFetchResult",
    # Service
    "IngestionService",
    "IngestionResult",
]
