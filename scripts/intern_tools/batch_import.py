#!/usr/bin/env python3
"""
Batch import from simple text file.

FILE FORMAT (data/inbox/batch.txt):
---
URL: https://jamesclear.com/habits

Paste article content here.
Multiple paragraphs fine.
No special formatting needed.

---
URL: https://markmanson.net/values

Another article content...

---

Just URLs and content. That's it.
Title auto-extracted from URL.
Author auto-detected from domain.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# i have moved on bitch
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.db.db_session import get_session

# Import utilities from add_article
from scripts.intern_tools.add_article import (
    load_authors,
    load_tracker,
    save_tracker,
    url_hash,
    is_duplicate,
    detect_author,
    extract_title_from_url,
    clean_content,
    get_or_create_source,
    save_to_database,
    archive_article,
    AUTHORS_FILE,
    MIN_WORDS,
    DATA_DIR,
)


BATCH_FILE = DATA_DIR / "inbox" / "batch.txt"


def parse_batch_file() -> list[dict]:
    """Parse batch file into articles."""
    if not BATCH_FILE.exists():
        return []

    content = BATCH_FILE.read_text(encoding="utf-8")

    # Split by separator
    blocks = re.split(r"\n-{3,}\n", content)

    articles = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Extract URL - handle "URL:", "url:", "url :", etc.
        url_match = re.search(r"^URL\s*:\s*(.+)$", block, re.MULTILINE | re.IGNORECASE)
        if not url_match:
            continue

        url = url_match.group(1).strip()
        if not url.startswith("http"):
            url = "https://" + url

        # Extract content (everything after URL line)
        article_content = re.sub(
            r"^URL\s*:\s*.+$", "", block, flags=re.MULTILINE | re.IGNORECASE
        )
        article_content = clean_content(article_content)

        if len(article_content.split()) >= MIN_WORDS:
            articles.append(
                {
                    "url": url,
                    "content": article_content,
                }
            )

    return articles


def create_template() -> None:
    """Create batch file template."""
    BATCH_FILE.parent.mkdir(parents=True, exist_ok=True)

    template = """---
URL: https://example.com/first-article

Paste the first article content here.
Multiple paragraphs are fine.
Just keep pasting until the article is done.

---
URL: https://example.com/second-article

Second article goes here.
Copy-paste from the browser.
Reader mode helps get clean text.

---
"""

    BATCH_FILE.write_text(template, encoding="utf-8")
    print(f"📝 Created template: {BATCH_FILE}")


def main() -> None:
    """Process batch file."""
    print("\n" + "=" * 60)
    print("📦 BATCH IMPORT")
    print("=" * 60)

    # Check/create batch file
    if not BATCH_FILE.exists():
        create_template()
        print("   Fill it with articles and run again.")
        return

    # Parse articles
    articles = parse_batch_file()

    if not articles:
        print("❌ No valid articles found in batch file.")
        print(f"   Check {BATCH_FILE}")
        return

    print(f"\n📄 Found {len(articles)} articles")

    # Load data
    authors_data = load_authors()
    tracker = load_tracker()

    # Process
    imported = 0
    skipped = 0
    errors: list[str] = []

    for i, article in enumerate(articles, 1):
        url = article["url"]
        content = article["content"]

        short_url = url[:50] + "..." if len(url) > 50 else url
        print(f"\n[{i}/{len(articles)}] {short_url}")

        # Check duplicate
        if is_duplicate(url, tracker):
            print("   ⚠️ Duplicate")
            skipped += 1
            continue

        # Detect author
        author = detect_author(url, authors_data)
        if not author:
            print("   ❌ Unknown author")
            errors.append(f"Unknown author: {url}")
            continue

        # Get title
        title = extract_title_from_url(url)

        # Use fresh session for each article to isolate errors
        session_gen = get_session()
        session = next(session_gen)

        try:
            # Archive first - always backup regardless of DB status
            archive_article(author["id"], title, url, content)

            # Save to database
            source = get_or_create_source(session, author)
            chunks, chunk_ids = save_to_database(session, source, title, content, url)

            # Check if this was a duplicate (0 chunks returned)
            if chunks == 0:
                # Still update tracker to sync with DB state
                # (article exists in DB but may not be in tracker)
                if url_hash(url) not in tracker["urls"]:
                    tracker["urls"][url_hash(url)] = {
                        "title": title,
                        "author": author["name"],
                        "date": datetime.now(timezone.utc).isoformat(),
                    }
                    # Also update stats since article IS in DB
                    tracker["stats"]["total"] += 1
                    tracker["stats"]["by_author"][author["id"]] = (
                        tracker["stats"]["by_author"].get(author["id"], 0) + 1
                    )
                    print(f"   📊 Synced to tracker (was DB duplicate)")

                skipped += 1
                # Close session cleanly
                try:
                    next(session_gen)
                except StopIteration:
                    pass
                continue

            # Update tracker for new imports
            tracker["urls"][url_hash(url)] = {
                "title": title,
                "author": author["name"],
                "date": datetime.now(timezone.utc).isoformat(),
            }
            tracker["stats"]["total"] += 1
            tracker["stats"]["by_author"][author["id"]] = (
                tracker["stats"]["by_author"].get(author["id"], 0) + 1
            )

            imported += 1
            word_count = len(content.split())
            print(
                f"   ✅ {author['name']}: {title[:35]}... "
                f"({word_count} words, {chunks} chunks)"
            )
            print(f"   📦 IDs: {', '.join(chunk_ids)}")

            # Close session cleanly
            try:
                next(session_gen)
            except StopIteration:
                pass

        except Exception as e:
            # Rollback and close session on error
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
    BATCH_FILE.write_text("---\nURL: \n\n")

    # Summary
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print(f"   ✅ Imported: {imported}")
    print(f"   ⚠️  Skipped: {skipped}")
    print(f"   ❌ Errors: {len(errors)}")
    print(f"\n   Total in DB: {tracker['stats']['total']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
