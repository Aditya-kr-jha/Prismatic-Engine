"""
Restore ONLY Untracked Archive Files to Database.

This script identifies archive files that are NOT tracked in tracker.json
and restores ONLY those to the ContentReservoir database WITHOUT modifying
the tracker.json or authors.json files.

USE CASE:
  If articles were archived but not saved to DB during a run, this script
  restores them without touching your existing tracking data.

USAGE:
  python scripts/intern_tools/restore_untracked.py           # Restore untracked
  python scripts/intern_tools/restore_untracked.py --dry-run # Preview only
  python scripts/intern_tools/restore_untracked.py --verbose # Show all details

WORKFLOW:
  1. Reads archive files from data/archive/
  2. Compares against tracker.json URLs (by hash)
  3. Finds files NOT in tracker
  4. Restores ONLY those to ContentReservoir
  5. Does NOT modify tracker.json or authors.json
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import argparse

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from sqlmodel import Session, select
import json

from app.db.db_session import get_session
from app.db.db_models.pre_ingestion import EvergreenSource, ContentReservoir
from app.db.enums import (
    EvergreenSourceType,
    EvergreenSourceStatus,
    ReservoirStatus,
)

# Import tracker utilities from add_article
from scripts.intern_tools.add_article import (
    load_tracker,
    url_hash,
)


# ---------- PATHS ----------
DATA_DIR = project_root / "data"
AUTHORS_FILE = DATA_DIR / "authors.json"
ARCHIVE_DIR = DATA_DIR / "archive"

# ---------- CONFIG ----------
CHUNK_SIZE = 2000  # words per chunk
CHUNK_OVERLAP = 100  # overlap between chunks


# ============================================================================
# AUTHOR RESOLUTION
# ============================================================================


def load_authors_json() -> dict:
    """Load authors from data/authors.json.
    
    This file contains the authoritative ID mapping used in archive files.
    """
    if not AUTHORS_FILE.exists():
        print(f"❌ Authors file not found: {AUTHORS_FILE}")
        return {}
    return json.loads(AUTHORS_FILE.read_text())


def get_author_by_id(author_id: str, authors_data: dict) -> Optional[dict]:
    """Get author info by ID from authors.json data."""
    authors = authors_data.get("authors", {})
    if author_id in authors:
        return authors[author_id]
    return None


# ============================================================================
# ARCHIVE PARSING
# ============================================================================


def parse_archive_file(filepath: Path) -> Optional[dict]:
    """Parse an archive file and extract metadata + content.
    
    Archive format:
        URL: <url>
        TITLE: <title>
        AUTHOR_ID: <id>
        ARCHIVED: <timestamp>
        
        ---
        
        <content>
    """
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ❌ Error reading {filepath.name}: {e}")
        return None
    
    # Split header and content
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        print(f"  ⚠️  Invalid format in {filepath.name}: missing --- separator")
        return None
    
    header, content = parts
    content = content.strip()
    
    # Parse header fields
    metadata = {}
    for line in header.strip().split("\n"):
        if ": " in line:
            key, value = line.split(": ", 1)
            metadata[key.strip()] = value.strip()
    
    # Validate required fields
    required = ["URL", "TITLE", "AUTHOR_ID"]
    for field in required:
        if field not in metadata:
            print(f"  ⚠️  Missing {field} in {filepath.name}")
            return None
    
    return {
        "url": metadata["URL"],
        "title": metadata["TITLE"],
        "author_id": metadata["AUTHOR_ID"],
        "archived_at": metadata.get("ARCHIVED", ""),
        "content": content,
        "filename": filepath.name,
    }


# ============================================================================
# TEXT PROCESSING
# ============================================================================


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
# DATABASE OPERATIONS
# ============================================================================


def get_or_create_source(session: Session, author: dict) -> EvergreenSource:
    """Get or create EvergreenSource for author."""
    statement = select(EvergreenSource).where(
        EvergreenSource.author == author["name"],
        EvergreenSource.source_type == EvergreenSourceType.BLOG,
    )
    existing = session.exec(statement).first()

    if existing:
        return existing

    source = EvergreenSource(
        source_type=EvergreenSourceType.BLOG,
        title=f"{author['name']}'s Blog",
        author=author["name"],
        file_path=author.get("blog_url", ""),
        status=EvergreenSourceStatus.PROCESSING,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    return source


def get_max_chunk_index(session: Session, source_id) -> int:
    """Get the maximum chunk index for a source."""
    statement = (
        select(ContentReservoir.chunk_index)
        .where(ContentReservoir.source_id == source_id)
        .order_by(ContentReservoir.chunk_index.desc())
    )
    result = session.exec(statement).first()
    return result if result is not None else -1


def check_duplicate_content(session: Session, source_id, raw_title: str) -> bool:
    """Check if content with same title already exists for this source.
    
    Uses title matching to detect duplicates even if chunk indices differ.
    """
    # Extract base title (remove " (Part X/Y)" suffix)
    base_title = re.sub(r"\s*\(Part \d+/\d+\)$", "", raw_title)
    
    statement = select(ContentReservoir).where(
        ContentReservoir.source_id == source_id,
        ContentReservoir.raw_title.like(f"{base_title}%")
    )
    existing = session.exec(statement).first()
    return existing is not None


def restore_article(
    session: Session,
    source: EvergreenSource,
    title: str,
    content: str,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Restore article chunks to ContentReservoir.
    
    Returns (inserted_count, skipped_count).
    """
    # Check for duplicate by title
    if check_duplicate_content(session, source.id, title):
        return 0, 1  # Skip - already exists
    
    # Get next chunk index
    start_idx = get_max_chunk_index(session, source.id) + 1
    
    # Chunk the content
    chunks = chunk_text(content)
    
    inserted = 0
    
    if dry_run:
        return len(chunks), 0
    
    for i, chunk in enumerate(chunks):
        chunk_title = title
        if len(chunks) > 1:
            chunk_title = f"{title} (Part {i + 1}/{len(chunks)})"

        entry = ContentReservoir(
            source_id=source.id,
            raw_text=chunk,
            raw_title=chunk_title,
            chunk_index=start_idx + i,
            source_type=EvergreenSourceType.BLOG.value,
            source_name=f"{source.author}'s Blog",
            source_author=source.author,
            status=ReservoirStatus.AVAILABLE,
        )
        session.add(entry)
        inserted += 1

    # Update source stats
    source.chunks_extracted += inserted
    session.add(source)
    session.commit()

    return inserted, 0


# ============================================================================
# FIND UNTRACKED FILES
# ============================================================================


def find_untracked_files(verbose: bool = False) -> list[Path]:
    """Find archive files that are NOT tracked in tracker.json.
    
    Compares archive file URLs against tracker.json hashes.
    """
    if not ARCHIVE_DIR.exists():
        print(f"❌ Archive directory not found: {ARCHIVE_DIR}")
        return []
    
    # Get all archive files
    archive_files = sorted(ARCHIVE_DIR.glob("*.txt"))
    if not archive_files:
        print("❌ No archive files found")
        return []
    
    # Load tracker
    tracker = load_tracker()
    tracked_hashes = set(tracker.get("urls", {}).keys())
    
    print(f"📂 Archive: {len(archive_files)} files")
    print(f"📊 Tracker: {len(tracked_hashes)} URLs tracked")
    print()
    
    untracked = []
    parse_errors = []
    
    for filepath in archive_files:
        article = parse_archive_file(filepath)
        
        if not article:
            parse_errors.append(filepath.name)
            continue
        
        # Generate URL hash and check if tracked
        article_hash = url_hash(article["url"])
        
        if article_hash not in tracked_hashes:
            untracked.append(filepath)
            if verbose:
                print(f"  📄 Untracked: {filepath.name}")
                print(f"      URL: {article['url'][:60]}...")
                print(f"      Hash: {article_hash}")
        else:
            if verbose:
                print(f"  ✓ Tracked: {filepath.name}")
    
    print(f"\n🔍 Found {len(untracked)} untracked files")
    if parse_errors:
        print(f"⚠️  Parse errors: {len(parse_errors)} files")
    
    return untracked


# ============================================================================
# MAIN RESTORE FUNCTION
# ============================================================================


def restore_untracked(dry_run: bool = False, verbose: bool = False) -> dict:
    """Restore ONLY untracked archive files to ContentReservoir.
    
    Args:
        dry_run: If True, only preview what would be done
        verbose: If True, show detailed output
    
    Returns:
        Statistics dict with totals
    """
    print(f"\n{'='*60}")
    print(f"{'🔍 DRY RUN - ' if dry_run else ''}📦 RESTORE UNTRACKED FILES")
    print(f"{'='*60}")
    print(f"⚠️  This script does NOT modify tracker.json or authors.json")
    print()
    
    # Find untracked files
    untracked_files = find_untracked_files(verbose=verbose)
    
    if not untracked_files:
        print("\n✅ No untracked files to restore!")
        return {"skipped": True}
    
    print(f"\n{'─'*60}")
    print("Starting restore...")
    print(f"{'─'*60}\n")
    
    # Load authors from JSON file
    authors_data = load_authors_json()
    if not authors_data:
        return {"error": "Failed to load authors.json"}
    
    # Stats
    stats = {
        "files_processed": 0,
        "files_skipped": 0,
        "chunks_inserted": 0,
        "chunks_skipped": 0,
        "db_duplicates": 0,
        "errors": [],
    }
    
    # Get database session
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        for filepath in untracked_files:
            print(f"📄 {filepath.name}")
            
            # Parse archive file
            article = parse_archive_file(filepath)
            if not article:
                stats["files_skipped"] += 1
                stats["errors"].append(f"Parse error: {filepath.name}")
                continue
            
            # Get author info
            author = get_author_by_id(article["author_id"], authors_data)
            if not author:
                print(f"  ⚠️  Unknown author ID: {article['author_id']}")
                stats["files_skipped"] += 1
                stats["errors"].append(f"Unknown author: {filepath.name}")
                continue
            
            print(f"  👤 Author: {author['name']}")
            print(f"  📝 Title: {article['title']}")
            
            # Get or create source
            source = get_or_create_source(session, author)
            
            # Restore article
            inserted, skipped = restore_article(
                session,
                source,
                article["title"],
                article["content"],
                dry_run=dry_run,
            )
            
            if skipped > 0:
                print(f"  ⏭️  Skipped (already in DB)")
                stats["db_duplicates"] += 1
            else:
                word_count = len(article["content"].split())
                print(f"  ✅ {'Would insert' if dry_run else 'Inserted'} {inserted} chunk(s) ({word_count:,} words)")
                stats["chunks_inserted"] += inserted
            
            stats["files_processed"] += 1
            print()
    
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass
    
    # Summary
    print("─" * 60)
    print(f"{'🔍 DRY RUN SUMMARY' if dry_run else '✅ RESTORE COMPLETE'}")
    print("─" * 60)
    print(f"📄 Files processed: {stats['files_processed']}")
    print(f"⏭️  Files skipped: {stats['files_skipped']}")
    print(f"📦 Chunks {'would be' if dry_run else ''} inserted: {stats['chunks_inserted']}")
    print(f"🔄 DB duplicates: {stats['db_duplicates']}")
    
    if stats["errors"]:
        print(f"\n⚠️  Errors ({len(stats['errors'])}):") 
        for err in stats["errors"][:10]:  # Show first 10
            print(f"   • {err}")
        if len(stats["errors"]) > 10:
            print(f"   ... and {len(stats['errors']) - 10} more")
    
    print()
    print("💡 Note: tracker.json was NOT modified.")
    print("   If you want to update the tracker, run:")
    print("   python scripts/intern_tools/restore_from_archive.py")
    print("=" * 60 + "\n")
    
    return stats


# ============================================================================
# CLI
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore ONLY untracked archive files to database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Preview what would be restored without making changes",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="Show detailed output for each file",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Only list untracked files, don't restore",
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("\n" + "="*60)
        print("📋 LISTING UNTRACKED FILES ONLY")
        print("="*60 + "\n")
        untracked = find_untracked_files(verbose=True)
        print(f"\n📊 Total untracked: {len(untracked)} files")
        print("="*60 + "\n")
    else:
        restore_untracked(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
