"""
Harvesters Package.

Content harvesters for fetching and parsing external data sources.
Harvesters only fetch and parse - they do NOT write to the database.
"""

from app.ingestion.harvesters.reddit import (
    RedditHarvester,
    HarvesterConfig,
    RawRedditPost,
    HarvestFetchResult,
)
from app.ingestion.harvesters.base import BaseHarvester

__all__ = [
    "BaseHarvester",
    "RedditHarvester",
    "HarvesterConfig",
    "RawRedditPost",
    "HarvestFetchResult",
]
