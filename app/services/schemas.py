"""
Pydantic models for the Reddit harvester service.

These models provide validation and structure for harvest operations.
"""

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.db.enums import ContentPillar


class RedditMetadata(BaseModel):
    """Nested model for raw_metadata JSONB storage."""

    title: str
    author: Optional[str] = None
    subreddit: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: float
    permalink: str
    post_type: str = Field(description="'self' for text posts, 'link' for links")
    domain: Optional[str] = None
    url: Optional[str] = None
    is_video: bool = False


class RawRedditPost(BaseModel):
    """Pydantic model for parsed and validated Reddit post data."""

    source_id: str = Field(description="Format: {subreddit}:{post_fullname}")
    title: str
    selftext: Optional[str] = None
    score: int = Field(ge=0)
    upvote_ratio: float = Field(ge=0.0, le=1.0)
    num_comments: int = Field(ge=0)
    created_utc: float
    permalink: str
    subreddit: str
    pillar: ContentPillar
    metadata: RedditMetadata

    @field_validator("source_id")
    @classmethod
    def validate_source_id_format(cls, v: str) -> str:
        """Ensure source_id follows {subreddit}:{post_fullname} format."""
        if ":" not in v:
            raise ValueError("source_id must be in format {subreddit}:{post_fullname}")
        return v

    @property
    def raw_content(self) -> str:
        """Combined content for storage."""
        if self.selftext:
            return f"{self.title}\n\n{self.selftext}"
        return self.title

    @property
    def source_url(self) -> str:
        """Full Reddit URL for the post."""
        return f"https://reddit.com{self.permalink}"


@dataclass
class HarvestResult:
    """Return type for harvest operations with summary statistics."""

    posts_fetched: int = 0
    posts_stored: int = 0
    posts_skipped: int = 0
    errors: list[str] = None
    duration_seconds: float = 0.0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def __str__(self) -> str:
        return (
            f"HarvestResult(fetched={self.posts_fetched}, "
            f"stored={self.posts_stored}, skipped={self.posts_skipped}, "
            f"errors={len(self.errors)}, duration={self.duration_seconds:.2f}s)"
        )


@dataclass(frozen=True)
class HarvesterConfig:
    """Configuration for the Reddit harvester."""

    posts_per_subreddit: int = 25
    lookback_days: int = 7
    request_delay_seconds: float = 2.0
    min_score: int = 10
    min_content_length: int = 300
    timeout_seconds: float = 30.0
    retry_delay_seconds: float = 60.0
    user_agent: str = "PrismaticEngine/1.0 (content research)"
