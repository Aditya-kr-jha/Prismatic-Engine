"""
YouTube Data API v3 Integration.

Extracts video metadata (title, channel) from YouTube URLs.
Uses the official YouTube Data API v3 — NOT for transcript extraction.
"""

import re
import sys
from pathlib import Path
from typing import Optional

import requests

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from app.config import settings
from scripts.intern_tools.youtube.schemas import YouTubeVideoMetadata


# YouTube URL patterns
YOUTUBE_URL_PATTERNS = [
    # Standard watch URLs
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
    # Short URLs
    r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})",
    # Embed URLs
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    # Shorts URLs
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
]


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.

    Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/shorts/VIDEO_ID

    Args:
        url: YouTube URL in any supported format

    Returns:
        11-character video ID or None if not found
    """
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_metadata(video_id: str) -> Optional[YouTubeVideoMetadata]:
    """
    Fetch video metadata from YouTube Data API v3.

    Retrieves title and channel info for a video.
    Requires YOUTUBE_API_KEY in environment.

    Args:
        video_id: YouTube video ID (11 characters)

    Returns:
        YouTubeVideoMetadata with video_id, title, channel_id, channel_name
        or None if API call fails
    """
    api_key = settings.YOUTUBE_API_KEY

    if not api_key:
        print("❌ YOUTUBE_API_KEY not set in environment")
        return None

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet",
        "id": video_id,
        "key": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("items"):
            print(f"❌ No video found for ID: {video_id}")
            return None

        snippet = data["items"][0]["snippet"]

        return YouTubeVideoMetadata(
            video_id=video_id,
            title=snippet["title"],
            channel_id=snippet["channelId"],
            channel_name=snippet["channelTitle"],
        )

    except requests.RequestException as e:
        print(f"❌ YouTube API request failed: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"❌ Failed to parse YouTube API response: {e}")
        return None


def get_metadata_from_url(url: str) -> Optional[YouTubeVideoMetadata]:
    """
    Convenience function: extract video ID and fetch metadata in one call.

    Args:
        url: YouTube URL in any supported format

    Returns:
        YouTubeVideoMetadata or None
    """
    video_id = extract_video_id(url)

    if not video_id:
        print(f"❌ Could not extract video ID from URL: {url}")
        return None

    return get_video_metadata(video_id)


# ============================================================================
# CLI Test
# ============================================================================

if __name__ == "__main__":
    # Quick test with a sample URL
    test_url = input("Enter YouTube URL to test: ").strip()

    if not test_url:
        print("No URL provided")
        sys.exit(1)

    video_id = extract_video_id(test_url)
    print(f"\n📺 Video ID: {video_id}")

    if video_id:
        metadata = get_video_metadata(video_id)
        if metadata:
            print(f"📄 Title: {metadata.title}")
            print(f"📺 Channel: {metadata.channel_name}")
            print(f"🆔 Channel ID: {metadata.channel_id}")
        else:
            print("Failed to fetch metadata")
