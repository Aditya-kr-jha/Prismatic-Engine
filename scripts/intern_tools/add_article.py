"""


USAGE:
  python scripts/intern_tools/add_article.py           # Add one article
  python scripts/intern_tools/add_article.py --loop    # Continuous mode
  python scripts/intern_tools/add_article.py --stats   # Show progress

WORKFLOW:
  1. Copy article URL from browser
  2. Run this script
  3. Paste URL → Press Enter
  4. Paste content → Type END → Press Enter
  5. Done! Script auto-detects author and handles everything.
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from sqlmodel import Session, select

from app.db.db_session import get_session
from app.db.db_models.pre_ingestion import EvergreenSource, ContentReservoir
from app.db.enums import (
    EvergreenSourceType,
    EvergreenSourceStatus,
    ReservoirStatus,
)


# ---------- PATHS ----------
DATA_DIR = project_root / "data"
AUTHORS_FILE = DATA_DIR / "authors.json"
TRACKER_FILE = DATA_DIR / "tracker.json"
ARCHIVE_DIR = DATA_DIR / "archive"

# ---------- CONFIG ----------
CHUNK_SIZE = 2000  # words per chunk
CHUNK_OVERLAP = 100  # overlap between chunks
MIN_WORDS = 50  # minimum article length


# ============================================================================
# DATA LOADING
# ============================================================================


def load_authors() -> dict:
    """Load authors config."""
    if not AUTHORS_FILE.exists():
        print(
            "❌ Authors not initialized. Run: "
            "python scripts/intern_tools/init_from_config.py"
        )
        sys.exit(1)
    return json.loads(AUTHORS_FILE.read_text())


def load_tracker() -> dict:
    """Load URL tracker."""
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text())
    return {"urls": {}, "stats": {"total": 0, "by_author": {}}}


def save_tracker(tracker: dict) -> None:
    """Save tracker."""
    TRACKER_FILE.write_text(json.dumps(tracker, indent=2))


# ============================================================================
# URL UTILITIES
# ============================================================================


def url_hash(url: str) -> str:
    """Generate hash for URL deduplication."""
    normalized = url.lower().strip().rstrip("/")
    # Remove query params and fragments
    normalized = normalized.split("?")[0].split("#")[0]
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def is_duplicate(url: str, tracker: dict) -> bool:
    """Check if URL already processed."""
    return url_hash(url) in tracker["urls"]


def detect_author(url: str, authors_data: dict) -> Optional[dict]:
    """Auto-detect author from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")

    # Try full domain first
    for pattern, author_id in authors_data.get("url_patterns", {}).items():
        if pattern in domain or pattern in url.lower():
            author_info = authors_data["authors"].get(author_id)
            if author_info:
                return {"id": author_id, **author_info}

    return None


def extract_title_from_url(url: str) -> str:
    """Extract readable title from URL slug."""
    parsed = urlparse(url)
    path = parsed.path.strip("/").split("/")[-1]

    # Remove extensions and clean up
    path = re.sub(r"\.(html?|php|aspx?)$", "", path)
    path = re.sub(r"[-_]", " ", path)
    path = re.sub(r"\d{4}[-/]\d{2}[-/]\d{2}[-/]?", "", path)  # Remove dates

    # Title case
    title = " ".join(word.capitalize() for word in path.split() if word)

    return title if title else "Untitled"


# ============================================================================
# TEXT PROCESSING
# ============================================================================


def clean_content(text: str) -> str:
    """Clean up pasted content."""
    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    # Remove common junk patterns
    junk_patterns = [
        r"Share this:.*?(?=\n|$)",
        r"Follow us on.*?(?=\n|$)",
        r"Subscribe to.*?(?=\n|$)",
        r"Sign up for.*?(?=\n|$)",
        r"Related posts?:?.*?(?=\n\n|$)",
        r"Tags:.*?(?=\n|$)",
        r"Categories:.*?(?=\n|$)",
        r"Posted in.*?(?=\n|$)",
        r"Leave a comment.*?(?=\n|$)",
        r"Comments \(\d+\)",
        r"Share on (Facebook|Twitter|LinkedIn).*?(?=\n|$)",
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

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


def save_to_database(
    session: Session,
    source: EvergreenSource,
    title: str,
    content: str,
    url: str,
) -> tuple[int, list[str]]:
    """Save article chunks to ContentReservoir. Returns (chunk count, list of IDs).
    
    Handles duplicates by checking if title already exists for this source.
    """
    import uuid
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy import text
    
    # Check for duplicate by title (remove Part X/Y suffix for comparison)
    base_title = re.sub(r"\s*\(Part \d+/\d+\)$", "", title)
    existing_check = session.exec(
        select(ContentReservoir).where(
            ContentReservoir.source_id == source.id,
            ContentReservoir.raw_title.like(f"{base_title}%")
        )
    ).first()
    
    if existing_check:
        # Content with this title already exists - skip
        print(f"   ⚠️ Article '{title}' already exists, skipping.")
        return 0, []
    
    # Get max chunk index for this source using raw SQL to ensure fresh read
    result = session.exec(
        text("""
            SELECT COALESCE(MAX(chunk_index), -1) + 1 as next_idx
            FROM content_reservoir 
            WHERE source_id = :source_id
        """),
        params={"source_id": str(source.id)}
    )
    row = result.first()
    start_idx = row[0] if row else 0

    # Chunk the content
    chunks = chunk_text(content)
    
    created_ids: list[str] = []
    inserted_count = 0

    for i, chunk in enumerate(chunks):
        chunk_title = title
        if len(chunks) > 1:
            chunk_title = f"{title} (Part {i + 1}/{len(chunks)})"

        chunk_id = uuid.uuid4()
        chunk_idx = start_idx + i
        
        # Use INSERT ... ON CONFLICT DO NOTHING to gracefully handle duplicates
        stmt = insert(ContentReservoir).values(
            id=chunk_id,
            source_id=source.id,
            raw_text=chunk,
            raw_title=chunk_title,
            chunk_index=chunk_idx,
            source_type=EvergreenSourceType.BLOG.value,
            source_name=f"{source.author}'s Blog",
            source_author=source.author,
            status=ReservoirStatus.AVAILABLE,
            times_used=0,
            last_used_at=None,
            cooldown_until=None,
        ).on_conflict_do_nothing(
            index_elements=['source_id', 'chunk_index']
        )
        
        result = session.execute(stmt)
        if result.rowcount > 0:
            created_ids.append(str(chunk_id))
            inserted_count += 1
        else:
            print(f"   ⚠️ Chunk {chunk_idx} already exists, skipping")

    # Update source stats only for actually inserted chunks
    if inserted_count > 0:
        source.chunks_extracted += inserted_count
        session.add(source)
    session.commit()

    return inserted_count, created_ids


# ============================================================================
# ARCHIVE
# ============================================================================


def archive_article(author_id: str, title: str, url: str, content: str) -> None:
    """Save article to archive as backup."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^\w\s-]", "", title)[:40].strip()
    filename = f"{author_id}_{safe_title}_{timestamp}.txt"

    archive_content = f"""URL: {url}
TITLE: {title}
AUTHOR_ID: {author_id}
ARCHIVED: {datetime.now(timezone.utc).isoformat()}

---

{content}
"""

    (ARCHIVE_DIR / filename).write_text(archive_content, encoding="utf-8")


# ============================================================================
# MAIN FUNCTIONS
# ============================================================================


def add_article() -> bool:
    """Interactive article intake."""
    authors_data = load_authors()
    tracker = load_tracker()

    print("\n" + "─" * 50)

    # Step 1: Get URL
    url = input("🔗 URL: ").strip()

    if not url:
        print("❌ No URL")
        return False

    if not url.startswith("http"):
        url = "https://" + url

    # Step 2: Check duplicate
    if is_duplicate(url, tracker):
        print("⚠️  Already added. Skipping.")
        return False

    # Step 3: Detect author
    author = detect_author(url, authors_data)

    if not author:
        # Show author list
        print("\n📋 Select author:")
        for aid, info in sorted(authors_data["authors"].items()):
            count = tracker["stats"]["by_author"].get(aid, 0)
            max_a = info.get("max_articles", 50)
            print(f"   {aid}: {info['name']} ({count}/{max_a})")

        author_id = input("\nAuthor ID: ").strip()

        if author_id not in authors_data["authors"]:
            print("❌ Invalid ID")
            return False

        author = {"id": author_id, **authors_data["authors"][author_id]}

        # Learn this domain
        domain = urlparse(url).netloc.replace("www.", "").lower()
        authors_data["url_patterns"][domain] = author_id
        AUTHORS_FILE.write_text(json.dumps(authors_data, indent=2))
        print(f"   📝 Learned: {domain} → {author['name']}")
    else:
        print(f"✅ Author: {author['name']}")

    # Step 4: Title
    auto_title = extract_title_from_url(url)
    print(f"📄 Title: {auto_title}")

    new_title = input("   (Enter to keep, or type new): ").strip()
    title = new_title if new_title else auto_title

    # Step 5: Content
    print("\n📝 Paste content, then type END on a new line:\n")

    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        except EOFError:
            break

    content = "\n".join(lines)
    content = clean_content(content)

    # Validate
    word_count = len(content.split())
    if word_count < MIN_WORDS:
        print(f"❌ Too short ({word_count} words, need {MIN_WORDS}+)")
        return False

    # Step 6: Save
    session_gen = get_session()
    session = next(session_gen)
    chunk_ids: list[str] = []
    try:
        source = get_or_create_source(session, author)
        chunks, chunk_ids = save_to_database(session, source, title, content, url)
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass

    # Archive
    archive_article(author["id"], title, url, content)

    # Update tracker
    tracker["urls"][url_hash(url)] = {
        "title": title,
        "author": author["name"],
        "date": datetime.now(timezone.utc).isoformat(),
    }
    tracker["stats"]["total"] += 1
    tracker["stats"]["by_author"][author["id"]] = (
        tracker["stats"]["by_author"].get(author["id"], 0) + 1
    )
    save_tracker(tracker)

    # Success output
    total = tracker["stats"]["total"]
    author_count = tracker["stats"]["by_author"].get(author["id"], 0)
    author_max = author.get("max_articles", 50)

    print(f"\n✅ Saved! {word_count:,} words → {chunks} chunk(s)")
    print(f"   {author['name']}: {author_count}/{author_max}")
    print(f"   Total: {total}/1000")
    
    # Display ContentReservoir IDs for verification
    print(f"\n   📦 ContentReservoir IDs:")
    for cid in chunk_ids:
        print(f"      {cid}")

    # Progress bar
    pct = min(total / 1000 * 100, 100)
    bar_len = 30
    filled = int(bar_len * pct / 100)
    print(f"\n   [{'█' * filled}{'░' * (bar_len - filled)}] {pct:.1f}%")

    return True


def show_stats() -> None:
    """Display progress statistics."""
    authors_data = load_authors()
    tracker = load_tracker()

    print("\n" + "=" * 60)
    print("📊 PROGRESS")
    print("=" * 60)

    total = tracker["stats"]["total"]
    target = sum(a.get("max_articles", 50) for a in authors_data["authors"].values())

    # Overall progress
    pct = total / target * 100 if target > 0 else 0
    bar_len = 40
    filled = int(bar_len * pct / 100)

    print(f"\n🎯 Overall: {total}/{target} ({pct:.1f}%)")
    print(f"[{'█' * filled}{'░' * (bar_len - filled)}]")

    # By author
    print(f"\n{'Author':<25} {'Done':<8} {'Target':<8} {'Status':<10}")
    print("─" * 55)

    completed = 0
    in_progress = 0
    not_started = 0

    for aid, info in sorted(authors_data["authors"].items()):
        name = info["name"][:24]
        done = tracker["stats"]["by_author"].get(aid, 0)
        max_a = info.get("max_articles", 50)

        if done >= max_a:
            status = "✅ Done"
            completed += 1
        elif done > 0:
            status = "🟡 Active"
            in_progress += 1
        else:
            status = "⬜ —"
            not_started += 1

        print(f"{name:<25} {done:<8} {max_a:<8} {status}")

    print("─" * 55)
    print(
        f"\n📈 Authors: {completed} done, {in_progress} active, "
        f"{not_started} remaining"
    )

    # Estimate
    if total > 0:
        remaining = target - total
        print(f"📝 Remaining: {remaining} articles")

    print("=" * 60 + "\n")


def continuous_mode() -> None:
    """Keep adding articles in a loop."""
    print("\n" + "=" * 60)
    print("🔄 CONTINUOUS MODE (Ctrl+C to stop)")
    print("=" * 60)

    count = 0

    try:
        while True:
            success = add_article()
            if success:
                count += 1

            print()
            cont = input("➡️  Next article? [Y/n]: ").strip().lower()
            if cont == "n":
                break
    except KeyboardInterrupt:
        print("\n")

    print(f"✅ Added {count} articles this session.\n")


# ============================================================================
# CLI
# ============================================================================


def main() -> None:
    args = sys.argv[1:]

    if "--stats" in args or "-s" in args:
        show_stats()
    elif "--loop" in args or "-l" in args:
        continuous_mode()
    elif "--help" in args or "-h" in args:
        print(__doc__)
    else:
        add_article()


if __name__ == "__main__":
    main()
