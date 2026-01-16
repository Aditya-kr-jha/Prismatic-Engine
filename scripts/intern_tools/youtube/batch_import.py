#!/usr/bin/env python3
"""
Batch import YouTube transcripts from text file.

FILE FORMAT (data/inbox/youtube_batch.txt):
---
URL: https://youtube.com/watch?v=xyz123

Paste transcript content here.
Multiple paragraphs fine.
No special formatting needed.

---
URL: https://youtu.be/abc456

Another video transcript...

---

Just URLs and transcripts. That's it.
Channel name and video title are auto-extracted via YouTube API.
"""

import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select

from app.db.db_session import get_session
from app.db.db_models.pre_ingestion import EvergreenSource, ContentReservoir
from app.db.enums import (
    EvergreenSourceType,
    EvergreenSourceStatus,
    ReservoirStatus,
)

from scripts.intern_tools.youtube.youtube_api import (
    extract_video_id,
    get_video_metadata,
)
from scripts.intern_tools.youtube.tracker import (
    load_tracker,
    save_tracker,
    url_hash,
    is_duplicate,
    register_channel,
    record_video,
)


# ---------- PATHS ----------
DATA_DIR = project_root / "data"
BATCH_FILE = DATA_DIR / "inbox" / "youtube_batch.txt"
ARCHIVE_DIR = DATA_DIR / "archive" / "youtube"

# ---------- CONFIG ----------
CHUNK_SIZE = 2000  # words per chunk
CHUNK_OVERLAP = 100  # overlap between chunks
MIN_WORDS = 50  # minimum transcript length


# ============================================================================
# TEXT PROCESSING (reused from blog pipeline)
# ============================================================================


def clean_content(text: str) -> str:
    """Clean up pasted transcript content."""
    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    # Remove common YouTube transcript junk
    junk_patterns = [
        r"\[Music\]",
        r"\[Applause\]",
        r"\[Laughter\]",
        r"^\d+:\d+:\d+$",  # Standalone timestamps
        r"^\d+:\d+$",  # Short timestamps
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, "", text, flags=re.MULTILINE | re.IGNORECASE)

    return text.strip()


def chunk_text(text: str) -> list[str]:
    """Split text into chunks by word count."""
    words = text.split()

    if len(words) <= CHUNK_SIZE:
        return [text]

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        start = end - CHUNK_OVERLAP
        if start >= len(words) - CHUNK_OVERLAP:
            break

    return chunks


# ============================================================================
# BATCH FILE PARSING
# ============================================================================


def parse_batch_file() -> list[dict]:
    """Parse batch file into video entries."""
    if not BATCH_FILE.exists():
        return []

    content = BATCH_FILE.read_text(encoding="utf-8")

    # Split by separator
    blocks = re.split(r"\n-{3,}\n", content)

    videos = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Extract URL - handle "URL:", "url:", etc.
        url_match = re.search(r"^URL\s*:\s*(.+)$", block, re.MULTILINE | re.IGNORECASE)
        if not url_match:
            continue

        url = url_match.group(1).strip()
        if not url.startswith("http"):
            url = "https://" + url

        # Extract transcript (everything after URL line)
        transcript = re.sub(
            r"^URL\s*:\s*.+$", "", block, flags=re.MULTILINE | re.IGNORECASE
        )
        transcript = clean_content(transcript)

        if len(transcript.split()) >= MIN_WORDS:
            videos.append(
                {
                    "url": url,
                    "transcript": transcript,
                }
            )

    return videos


def create_template() -> None:
    """Create batch file template."""
    BATCH_FILE.parent.mkdir(parents=True, exist_ok=True)

    template = """---
URL: https://youtube.com/watch?v=EXAMPLE_VIDEO_ID

Paste the video transcript here.
Multiple paragraphs are fine.
Channel and title will be auto-detected via YouTube API.

---
URL: https://youtu.be/ANOTHER_VIDEO_ID

Second video transcript goes here.
Copy from YouTube's transcript feature or
any transcription service you prefer.

---
"""

    BATCH_FILE.write_text(template, encoding="utf-8")
    print(f"📝 Created template: {BATCH_FILE}")


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================


def get_or_create_source(session: Session, channel_name: str) -> EvergreenSource:
    """
    Get or create EvergreenSource for a YouTube channel.

    Maps channel_name to author field in EvergreenSource.
    """
    statement = select(EvergreenSource).where(
        EvergreenSource.author == channel_name,
        EvergreenSource.source_type == EvergreenSourceType.YOUTUBE,
    )
    existing = session.exec(statement).first()

    if existing:
        return existing

    source = EvergreenSource(
        source_type=EvergreenSourceType.YOUTUBE,
        title=f"{channel_name}'s YouTube Channel",
        author=channel_name,
        file_path=None,  # No file path for YouTube
        status=EvergreenSourceStatus.PROCESSING,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    print(f"   🆕 Created EvergreenSource for: {channel_name}")

    return source


def save_to_database(
    session: Session,
    source: EvergreenSource,
    video_title: str,
    transcript: str,
    video_url: str,
) -> tuple[int, list[str]]:
    """
    Save transcript chunks to ContentReservoir.

    Returns (chunk count, list of ContentReservoir IDs).

    Field mapping:
        - raw_text: transcript chunk
        - raw_title: video title (with Part X/Y for multi-chunk)
        - source_type: "YOUTUBE"
        - source_name: video title
        - source_author: channel name
    """
    from sqlalchemy import text as sql_text

    # Check for duplicate by video title
    base_title = re.sub(r"\s*\(Part \d+/\d+\)$", "", video_title)
    existing_check = session.exec(
        select(ContentReservoir).where(
            ContentReservoir.source_id == source.id,
            ContentReservoir.raw_title.like(f"{base_title}%"),
        )
    ).first()

    if existing_check:
        print(f"   ⚠️ Video '{video_title}' already exists in DB")
        # Return -1 to signal "exists in DB but not new" so caller can sync tracker
        return -1, []

    # Get max chunk index for this source
    result = session.exec(
        sql_text(
            """
            SELECT COALESCE(MAX(chunk_index), -1) + 1 as next_idx
            FROM content_reservoir 
            WHERE source_id = :source_id
        """
        ),
        params={"source_id": str(source.id)},
    )
    row = result.first()
    start_idx = row[0] if row else 0

    # Chunk the transcript
    chunks = chunk_text(transcript)

    created_ids: list[str] = []
    inserted_count = 0

    for i, chunk in enumerate(chunks):
        chunk_title = video_title
        if len(chunks) > 1:
            chunk_title = f"{video_title} (Part {i + 1}/{len(chunks)})"

        chunk_id = uuid.uuid4()
        chunk_idx = start_idx + i

        # Use INSERT ... ON CONFLICT DO NOTHING for safety
        stmt = (
            insert(ContentReservoir)
            .values(
                id=chunk_id,
                source_id=source.id,
                raw_text=chunk,
                raw_title=chunk_title,
                chunk_index=chunk_idx,
                source_type=EvergreenSourceType.YOUTUBE.value,
                source_name=video_title,  # Video title
                source_author=source.author,  # Channel name
                status=ReservoirStatus.AVAILABLE,
                times_used=0,
                last_used_at=None,
                cooldown_until=None,
            )
            .on_conflict_do_nothing(index_elements=["source_id", "chunk_index"])
        )

        result = session.execute(stmt)
        if result.rowcount > 0:
            created_ids.append(str(chunk_id))
            inserted_count += 1
        else:
            print(f"   ⚠️ Chunk {chunk_idx} already exists, skipping")

    # Update source stats
    if inserted_count > 0:
        source.chunks_extracted += inserted_count
        session.add(source)
    session.commit()

    return inserted_count, created_ids


# ============================================================================
# ARCHIVE
# ============================================================================


def archive_video(
    channel_slug: str,
    video_title: str,
    url: str,
    transcript: str,
) -> None:
    """Save video transcript to archive as backup."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^\w\s-]", "", video_title)[:40].strip()
    filename = f"{channel_slug}_{safe_title}_{timestamp}.txt"

    archive_content = f"""URL: {url}
TITLE: {video_title}
CHANNEL: {channel_slug}
ARCHIVED: {datetime.now(timezone.utc).isoformat()}

---

{transcript}
"""

    (ARCHIVE_DIR / filename).write_text(archive_content, encoding="utf-8")


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    """Process batch file."""
    print("\n" + "=" * 60)
    print("📺 YOUTUBE BATCH IMPORT")
    print("=" * 60)

    # Check/create batch file
    if not BATCH_FILE.exists():
        create_template()
        print("   Fill it with video URLs and transcripts, then run again.")
        return

    # Parse videos
    videos = parse_batch_file()

    if not videos:
        print("❌ No valid videos found in batch file.")
        print(f"   Check {BATCH_FILE}")
        return

    print(f"\n🎬 Found {len(videos)} videos")

    # Load tracker
    tracker = load_tracker()

    # Process
    imported = 0
    skipped = 0
    errors: list[str] = []

    for i, video in enumerate(videos, 1):
        url = video["url"]
        transcript = video["transcript"]

        short_url = url[:50] + "..." if len(url) > 50 else url
        print(f"\n[{i}/{len(videos)}] {short_url}")

        # Check duplicate
        if is_duplicate(url, tracker):
            print("   ⚠️ Duplicate - already imported")
            skipped += 1
            continue

        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            print("   ❌ Could not extract video ID")
            errors.append(f"Invalid URL: {url}")
            continue

        # Fetch metadata from YouTube API
        print("   📡 Fetching metadata from YouTube API...")
        metadata = get_video_metadata(video_id)

        if not metadata:
            print("   ❌ Could not fetch video metadata")
            errors.append(f"API failed: {url}")
            continue

        print(f"   📄 Title: {metadata.title}")
        print(f"   📺 Channel: {metadata.channel_name}")

        # Register channel (dynamic)
        channel_slug = register_channel(
            tracker,
            metadata.channel_id,
            metadata.channel_name,
        )

        # Database operations
        session_gen = get_session()
        session = next(session_gen)

        try:
            # Archive first
            archive_video(channel_slug, metadata.title, url, transcript)

            # Get or create source
            source = get_or_create_source(session, metadata.channel_name)

            # Save to database
            chunks, chunk_ids = save_to_database(
                session,
                source,
                metadata.title,
                transcript,
                url,
            )

            # Handle existing content (sync to tracker)
            if chunks == -1:
                # Video exists in DB but not in tracker - sync it
                word_count = len(transcript.split())
                record_video(
                    tracker,
                    url=url,
                    video_id=video_id,
                    title=metadata.title,
                    channel_slug=channel_slug,
                    channel_name=metadata.channel_name,
                    transcript_words=word_count,
                    chunks_created=0,  # Unknown, already in DB
                )
                print(f"   📊 Synced to tracker (was DB duplicate)")
                skipped += 1
                try:
                    next(session_gen)
                except StopIteration:
                    pass
                continue

            if chunks == 0:
                # ON CONFLICT happened for all chunks - unusual case
                skipped += 1
                try:
                    next(session_gen)
                except StopIteration:
                    pass
                continue

            # Record in tracker
            word_count = len(transcript.split())
            record_video(
                tracker,
                url=url,
                video_id=video_id,
                title=metadata.title,
                channel_slug=channel_slug,
                channel_name=metadata.channel_name,
                transcript_words=word_count,
                chunks_created=chunks,
            )

            imported += 1
            print(f"   ✅ Saved: {word_count:,} words → {chunks} chunk(s)")
            print(f"   📦 IDs: {', '.join(chunk_ids[:3])}" + ("..." if len(chunk_ids) > 3 else ""))

            try:
                next(session_gen)
            except StopIteration:
                pass

        except Exception as e:
            session.rollback()
            try:
                session.close()
            except Exception:
                pass
            errors.append(f"{url}: {e}")
            print(f"   ❌ Error: {e}")

    # Save tracker
    save_tracker(tracker)

    # Clear batch file
    BATCH_FILE.write_text("---\nURL: \n\n", encoding="utf-8")

    # Summary
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print(f"   ✅ Imported: {imported}")
    print(f"   ⚠️  Skipped: {skipped}")
    print(f"   ❌ Errors: {len(errors)}")
    print(f"\n   📺 Total videos: {tracker.stats.total_videos}")
    print(f"   📺 Channels: {len(tracker.channels)}")

    if errors:
        print("\n   Errors:")
        for err in errors[:5]:
            print(f"      - {err[:60]}...")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
