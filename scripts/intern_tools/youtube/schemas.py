"""
Pydantic Schemas for YouTube Import Tools.

Data models for YouTube channel and video tracking.
"""

from pydantic import BaseModel, Field


class ChannelInfo(BaseModel):
    """Dynamically registered YouTube channel."""

    id: str  # channel slug (e.g., "huberman_lab")
    name: str  # Display name (e.g., "Huberman Lab")
    youtube_channel_id: str  # YouTube's channel ID (UC...)
    pillars: list[str] = Field(default_factory=list)
    max_videos: int = 100


class VideoInfo(BaseModel):
    """Tracked video entry."""

    video_id: str  # YouTube video ID
    title: str  # Video title
    channel_slug: str  # Reference to channel ID in tracker
    channel_name: str  # Denormalized channel name
    transcript_words: int  # Word count of pasted transcript
    chunks_created: int  # Number of ContentReservoir chunks
    date_added: str  # ISO timestamp


class YouTubeStats(BaseModel):
    """Aggregate statistics for YouTube imports."""

    total_videos: int = 0
    total_words: int = 0
    total_chunks: int = 0
    by_channel: dict[str, int] = Field(default_factory=dict)


class YouTubeTrackerData(BaseModel):
    """
    Full youtube_tracker.json structure.

    Unlike authors.json which is pre-defined, channels are
    dynamically registered when first encountered.
    """

    videos: dict[str, VideoInfo] = Field(default_factory=dict)  # keyed by url_hash
    channels: dict[str, ChannelInfo] = Field(default_factory=dict)  # dynamic registry
    stats: YouTubeStats = Field(default_factory=YouTubeStats)


class YouTubeVideoMetadata(BaseModel):
    """Metadata extracted from YouTube Data API."""

    video_id: str
    title: str
    channel_id: str
    channel_name: str
