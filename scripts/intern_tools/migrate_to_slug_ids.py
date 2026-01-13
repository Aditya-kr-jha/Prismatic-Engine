#!/usr/bin/env python3
"""
One-time migration script to convert from numeric IDs to slug-based IDs.

This script:
1. Creates a mapping from old numeric IDs to new slug IDs
2. Updates authors.json with new IDs
3. Updates tracker.json stats keys
4. Creates backups before modifying

Usage:
    python scripts/intern_tools/migrate_to_slug_ids.py          # Preview
    python scripts/intern_tools/migrate_to_slug_ids.py --apply  # Apply changes
"""

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


# ---------- PATHS ----------
DATA_DIR = project_root / "data"
AUTHORS_FILE = DATA_DIR / "authors.json"
TRACKER_FILE = DATA_DIR / "tracker.json"


def slugify(name: str) -> str:
    """Convert author name to stable slug ID."""
    slug = name.lower()
    slug = re.sub(r"[''`]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug


def create_backup(file_path: Path) -> Path:
    """Create timestamped backup of a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f".backup_{timestamp}.json")
    shutil.copy(file_path, backup_path)
    return backup_path


def main() -> None:
    apply_mode = "--apply" in sys.argv

    print("\n" + "=" * 60)
    print("🔄 MIGRATING TO SLUG-BASED AUTHOR IDs")
    if not apply_mode:
        print("   (Preview mode - use --apply to make changes)")
    print("=" * 60)

    if not AUTHORS_FILE.exists():
        print("❌ authors.json not found. Nothing to migrate.")
        return

    # Load current data
    authors_data = json.loads(AUTHORS_FILE.read_text())
    tracker_data = json.loads(TRACKER_FILE.read_text()) if TRACKER_FILE.exists() else None

    # Build ID mapping (old numeric -> new slug)
    id_mapping: dict[str, str] = {}
    new_authors: dict = {}

    print("\n📋 ID Mapping:")
    for old_id, author_info in authors_data["authors"].items():
        name = author_info["name"]
        new_id = slugify(name)
        id_mapping[old_id] = new_id
        new_authors[new_id] = author_info
        print(f"   {old_id:>3} -> {new_id}")

    # Update URL patterns
    new_url_patterns: dict = {}
    for pattern, old_id in authors_data.get("url_patterns", {}).items():
        new_id = id_mapping.get(old_id, old_id)  # Fallback to original if not found
        new_url_patterns[pattern] = new_id

    # Build new authors.json
    new_authors_data = {
        "authors": new_authors,
        "url_patterns": new_url_patterns,
    }

    print(f"\n📊 URL patterns: {len(new_url_patterns)} migrated")

    # Update tracker if exists
    new_tracker_data = None
    if tracker_data:
        new_by_author: dict = {}
        old_by_author = tracker_data.get("stats", {}).get("by_author", {})
        
        print(f"\n📈 Tracker stats migration:")
        for old_id, count in old_by_author.items():
            new_id = id_mapping.get(old_id, old_id)
            new_by_author[new_id] = count
            if old_id != new_id:
                print(f"   {old_id} ({count} articles) -> {new_id}")

        new_tracker_data = {
            "urls": tracker_data.get("urls", {}),
            "stats": {
                "total": tracker_data.get("stats", {}).get("total", 0),
                "by_author": new_by_author,
            },
        }

    if apply_mode:
        # Create backups
        print("\n💾 Creating backups...")
        backup1 = create_backup(AUTHORS_FILE)
        print(f"   {backup1.name}")
        
        if TRACKER_FILE.exists():
            backup2 = create_backup(TRACKER_FILE)
            print(f"   {backup2.name}")

        # Save new files
        AUTHORS_FILE.write_text(json.dumps(new_authors_data, indent=2))
        print(f"\n✅ Updated {AUTHORS_FILE.name}")

        if new_tracker_data:
            TRACKER_FILE.write_text(json.dumps(new_tracker_data, indent=2))
            print(f"✅ Updated {TRACKER_FILE.name}")

        print("\n🎉 Migration complete!")
    else:
        print("\n" + "-" * 60)
        print("Preview complete. Run with --apply to make changes.")
        print("-" * 60)

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
