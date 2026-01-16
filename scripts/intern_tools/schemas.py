"""
Pydantic Schemas for Intern Tools.

Shared data models for the human-in-the-loop blog intake pipeline.
"""

from pydantic import BaseModel, Field


class AuthorInfo(BaseModel):
    """Author information from config."""

    id: str
    name: str
    blog_url: str
    platform: str
    pillars: list[str]
    max_articles: int


class TrackedURL(BaseModel):
    """A single tracked URL entry."""

    title: str
    author: str
    date: str


class TrackerStats(BaseModel):
    """Progress tracking statistics."""

    total: int = 0
    by_author: dict[str, int] = Field(default_factory=dict)


class TrackerData(BaseModel):
    """Full tracker.json structure."""

    urls: dict[str, TrackedURL] = Field(default_factory=dict)
    stats: TrackerStats = Field(default_factory=TrackerStats)


class AuthorsData(BaseModel):
    """Full authors.json structure."""

    authors: dict[str, dict] = Field(default_factory=dict)
    url_patterns: dict[str, str] = Field(default_factory=dict)


class ChunkConfig(BaseModel):
    """Configuration for text chunking."""

    chunk_size: int = 1800  # words per chunk
    chunk_overlap: int = 100  # overlap between chunks
    min_words: int = 50  # minimum article length
