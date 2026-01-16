"""
Dynamic YouTube Channel and Video Tracker.

Unlike the blog pipeline's pre-defined authors.json, channels
are dynamically registered when first encountered.
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from scripts.intern_tools.youtube.schemas import (
    YouTubeTrackerData,
    YouTubeStats,
    ChannelInfo,
    VideoInfo,
)


# ---------- PATHS ----------
DATA_DIR = project_root / "data"
TRACKER_FILE = DATA_DIR / "youtube_tracker.json"


# ============================================================================
# TRACKER I/O
# ============================================================================


def load_tracker() -> YouTubeTrackerData:
    """Load YouTube tracker from JSON file."""
    if TRACKER_FILE.exists():
        try:
            data = json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
            return YouTubeTrackerData.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️ Error loading tracker, creating new: {e}")

    return YouTubeTrackerData(stats=YouTubeStats())


def save_tracker(tracker: YouTubeTrackerData) -> None:
    """Save tracker to JSON file."""
    TRACKER_FILE.write_text(
        tracker.model_dump_json(indent=2),
        encoding="utf-8",
    )


# ============================================================================
# URL HANDLING
# ============================================================================


def url_hash(url: str) -> str:
    """
    Generate hash for URL deduplication.

    Normalizes URL before hashing for consistent dedup.
    """
    normalized = url.lower().strip().rstrip("/")
    # Remove query params except v= for YouTube
    # Keep only the video ID for consistency
    if "youtube.com" in normalized or "youtu.be" in normalized:
        # Extract video ID and use that for hashing
        from scripts.intern_tools.youtube.youtube_api import extract_video_id

        video_id = extract_video_id(url)
        if video_id:
            normalized = f"youtube:{video_id}"

    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def is_duplicate(url: str, tracker: YouTubeTrackerData) -> bool:
    """Check if video URL already processed."""
    return url_hash(url) in tracker.videos


# ============================================================================
# CHANNEL MANAGEMENT (Dynamic Registration)
# ============================================================================


def generate_channel_slug(channel_name: str) -> str:
    """
    Generate a slug from channel name.

    Example: "Huberman Lab" -> "huberman_lab"
    """
    # Lowercase and replace spaces/special chars with underscores
    slug = re.sub(r"[^a-z0-9]+", "_", channel_name.lower())
    # Remove leading/trailing underscores
    slug = slug.strip("_")
    # Limit length
    return slug[:50] if slug else "unknown_channel"


def get_channel_by_youtube_id(
    tracker: YouTubeTrackerData,
    youtube_channel_id: str,
) -> Optional[ChannelInfo]:
    """Find channel by YouTube's channel ID."""
    for channel in tracker.channels.values():
        if channel.youtube_channel_id == youtube_channel_id:
            return channel
    return None


def register_channel(
    tracker: YouTubeTrackerData,
    youtube_channel_id: str,
    channel_name: str,
) -> str:
    """
    Register a new channel or return existing slug.

    Channels are dynamically added when first encountered,
    unlike the pre-defined authors in the blog pipeline.

    Args:
        tracker: Current tracker data
        youtube_channel_id: YouTube's channel ID (UC...)
        channel_name: Channel display name

    Returns:
        Channel slug (e.g., "huberman_lab")
    """
    # Check if channel already registered
    existing = get_channel_by_youtube_id(tracker, youtube_channel_id)
    if existing:
        return existing.id

    # Generate slug
    base_slug = generate_channel_slug(channel_name)
    slug = base_slug

    # Handle collisions
    counter = 1
    while slug in tracker.channels:
        slug = f"{base_slug}_{counter}"
        counter += 1

    # Register new channel
    channel = ChannelInfo(
        id=slug,
        name=channel_name,
        youtube_channel_id=youtube_channel_id,
        pillars=[],  # User can add later
        max_videos=100,
    )
    tracker.channels[slug] = channel

    print(f"   🆕 Registered new channel: {channel_name} ({slug})")

    return slug


# ============================================================================
# VIDEO RECORDING
# ============================================================================


def record_video(
    tracker: YouTubeTrackerData,
    url: str,
    video_id: str,
    title: str,
    channel_slug: str,
    channel_name: str,
    transcript_words: int,
    chunks_created: int,
) -> None:
    """
    Record a video import and update statistics.

    Args:
        tracker: Current tracker data
        url: Original YouTube URL
        video_id: YouTube video ID
        title: Video title
        channel_slug: Registered channel slug
        channel_name: Channel display name
        transcript_words: Word count of transcript
        chunks_created: Number of ContentReservoir chunks
    """
    hash_key = url_hash(url)

    video_info = VideoInfo(
        video_id=video_id,
        title=title,
        channel_slug=channel_slug,
        channel_name=channel_name,
        transcript_words=transcript_words,
        chunks_created=chunks_created,
        date_added=datetime.now(timezone.utc).isoformat(),
    )

    tracker.videos[hash_key] = video_info

    # Update statistics
    tracker.stats.total_videos += 1
    tracker.stats.total_words += transcript_words
    tracker.stats.total_chunks += chunks_created

    tracker.stats.by_channel[channel_slug] = (
        tracker.stats.by_channel.get(channel_slug, 0) + 1
    )


# ============================================================================
# STATISTICS
# ============================================================================


def show_stats(tracker: YouTubeTrackerData) -> None:
    """Display YouTube import statistics."""
    stats = tracker.stats

    print("\n" + "=" * 60)
    print("📊 YOUTUBE IMPORT STATISTICS")
    print("=" * 60)

    print(f"\n🎬 Total Videos: {stats.total_videos}")
    print(f"📝 Total Words: {stats.total_words:,}")
    print(f"📦 Total Chunks: {stats.total_chunks}")
    print(f"📺 Channels: {len(tracker.channels)}")

    if tracker.channels:
        print("\n📺 By Channel:")
        print("-" * 40)
        for slug, channel in sorted(tracker.channels.items()):
            count = stats.by_channel.get(slug, 0)
            print(f"   {channel.name}: {count} videos")

    print("=" * 60 + "\n")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    tracker = load_tracker()
    show_stats(tracker)
